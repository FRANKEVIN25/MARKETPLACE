/**
 * API Client para Vendors
 * 
 * Este archivo contiene todas las funciones para interactuar con el backend
 * relacionadas con el registro de vendors (proveedores)
 * 
 * CÓMO FUNCIONA:
 * 1. Importamos axios (librería para hacer peticiones HTTP)
 * 2. Definimos funciones que llaman al backend de Django
 * 3. TypeScript nos ayuda a asegurar que los datos sean correctos
 */

import axios, { type AxiosInstance } from 'axios';
import type {
  VendorRegistrationData,
  VendorRegistrationResponse,
  RegistrationStatusResponse,
  TierInfo
} from './types';

// ============================================
// CONFIGURACIÓN BASE
// ============================================
// URL del backend Django (cambia en producción)
const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

// Crear instancia de axios para hacer peticiones
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 30000,  // 30 segundos (registro puede tardar)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================
// FUNCIONES DE LA API
// ============================================

/**
 * Registrar un nuevo vendor
 * 
 * Esta función envía los datos del formulario al backend
 * El backend creará:
 * 1. Usuario Django
 * 2. Provider en la base de datos
 * 3. Company en Odoo (en segundo plano con Celery)
 * 4. Usuario en Odoo (en segundo plano)
 * 
 * @param data - Datos del formulario de registro
 * @returns Respuesta del backend con info del registro
 * 
 * EJEMPLO DE USO:
 * const response = await registerVendor({
 *   username: "juan_autopartes",
 *   email: "juan@example.com",
 *   password: "mipassword123",
 *   password_confirm: "mipassword123",
 *   business_name: "AutoPartes Juan SAC",
 *   business_email: "ventas@autopartesjuan.com",
 *   phone: "+51 999 888 777",
 *   ruc: "20123456789",
 *   odoo_password: "odoopass123",
 *   odoo_password_confirm: "odoopass123",
 *   tier: "starter",
 *   accept_terms: true
 * });
 */
export async function registerVendor(
  data: VendorRegistrationData
): Promise<VendorRegistrationResponse> {
  try {
    // POST = enviar datos al servidor
    // El backend está en: /api/v1/marketplace/register-vendor/
    const response = await apiClient.post<VendorRegistrationResponse>(
      '/api/v1/marketplace/register-vendor/',
      data
    );
    
    // Si llegamos aquí, el registro fue exitoso
    return response.data;
    
  } catch (error: any) {
    // Si algo sale mal, manejamos el error
    console.error('❌ Error al registrar vendor:', error);
    
    // Si el backend nos envió un mensaje de error, lo usamos
    if (error.response?.data) {
      throw new Error(
        error.response.data.message || 
        'Error al registrar. Verifica los datos.'
      );
    }
    
    // Si es un error de red u otro
    throw new Error('No se pudo conectar con el servidor. Intenta de nuevo.');
  }
}

/**
 * Consultar el estado de una tarea de registro
 * 
 * Después de registrarse, Celery crea la Company y Usuario en Odoo
 * en segundo plano. Esta función nos permite consultar si ya terminó.
 * 
 * @param taskId - ID de la tarea que nos dio el backend al registrarnos
 * @returns Estado de la tarea (PENDING, SUCCESS, FAILURE)
 * 
 * EJEMPLO DE USO:
 * // Después de registrarse, obtenemos un task_id
 * const status = await getRegistrationStatus(response.task_id);
 * if (status.state === 'SUCCESS') {
 *   console.log('¡Ya está listo! Puedes iniciar sesión en Odoo');
 * }
 */
export async function getRegistrationStatus(
  taskId: string
): Promise<RegistrationStatusResponse> {
  try {
    // GET = pedir información al servidor
    const response = await apiClient.get<RegistrationStatusResponse>(
      `/api/v1/marketplace/registration-status/${taskId}/`
    );
    
    return response.data;
    
  } catch (error: any) {
    console.error('❌ Error al consultar estado:', error);
    
    throw new Error('No se pudo consultar el estado del registro.');
  }
}

/**
 * Obtener información de los planes disponibles
 * 
 * Esta función retorna la información de los 3 planes:
 * - Starter (Gratis)
 * - Pro (S/ 99/mes)
 * - Premium (S/ 299/mes)
 * 
 * NOTA: Por ahora está hardcodeado aquí, pero en producción
 * deberías traerlo del backend para poder actualizar precios
 * sin cambiar el código del frontend
 * 
 * @returns Array con información de cada plan
 */
export function getTiers(): TierInfo[] {
  return [
    {
      id: 'starter',
      name: 'Plan Starter',
      price: 0,  // Gratis
      features: [
        'Hasta 100 productos',
        'Hasta 50 órdenes/mes',
        'Panel de gestión básico',
        'Soporte por email',
        'Comisión del 8% por venta'
      ],
      max_products: 100,
      commission: 0.08,
      recommended: false
    },
    {
      id: 'pro',
      name: 'Plan Pro',
      price: 99,  // S/ 99/mes
      features: [
        'Hasta 1,000 productos',
        'Hasta 500 órdenes/mes',
        'Panel de gestión avanzado',
        'Reportes y estadísticas',
        'Soporte prioritario',
        'Comisión del 5% por venta'
      ],
      max_products: 1000,
      commission: 0.05,
      recommended: true  // Este es el recomendado
    },
    {
      id: 'premium',
      name: 'Plan Premium',
      price: 299,  // S/ 299/mes
      features: [
        'Productos ilimitados',
        'Órdenes ilimitadas',
        'Instancia dedicada de Odoo',
        'Subdominio propio',
        'Soporte 24/7',
        'Comisión del 3% por venta',
        'API personalizada'
      ],
      max_products: null,  // Ilimitado
      commission: 0.03,
      recommended: false
    }
  ];
}

/**
 * Validar RUC peruano
 * 
 * El RUC debe tener 11 dígitos y empezar con 10 o 20
 * 
 * @param ruc - RUC a validar
 * @returns true si es válido, false si no
 * 
 * EJEMPLO:
 * validateRUC("20123456789")  // true
 * validateRUC("123456789")    // false (muy corto)
 * validateRUC("30123456789")  // false (no empieza con 10 o 20)
 */
export function validateRUC(ruc: string): boolean {
  // Debe tener exactamente 11 dígitos
  if (ruc.length !== 11) return false;
  
  // Debe contener solo números
  if (!/^\d+$/.test(ruc)) return false;
  
  // Debe empezar con 10 o 20
  if (!ruc.startsWith('10') && !ruc.startsWith('20')) return false;
  
  return true;
}

// ============================================
// EXPORTAR TODO COMO UN OBJETO (opcional)
// ============================================
// Esto permite usar: import { vendorsApi } from './vendors'
// Y luego: vendorsApi.register(data)
export const vendorsApi = {
  register: registerVendor,
  getStatus: getRegistrationStatus,
  getTiers,
  validateRUC
};

// También exportamos las funciones individuales para flexibilidad
// Esto permite: import { registerVendor } from './vendors'
export default vendorsApi;