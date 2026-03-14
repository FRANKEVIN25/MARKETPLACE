/**
 * API de Vendors/Proveedores
 * Conecta con: POST /api/v1/marketplace/register-vendor/
 *              GET  /api/v1/marketplace/registration-status/<task_id>/
 */
import axios from 'axios';
import type { VendorRegistrationData, VendorRegistrationResponse, RegistrationStatusResponse } from './types';

const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

/**
 * Registra un nuevo vendor en el marketplace
 * Crea el usuario Django + dispara Celery task que crea Company+User en Odoo
 */
export async function registerVendor(data: VendorRegistrationData): Promise<VendorRegistrationResponse> {
  try {
    const response = await apiClient.post<VendorRegistrationResponse>(
      '/api/v1/marketplace/register-vendor/',
      data
    );
    return response.data;
  } catch (error: any) {
    // Extraer errores de validación del backend (campo por campo)
    const backendErrors = error?.response?.data?.errors;
    if (backendErrors) {
      // Convertir {field: ["msg"]} → mensaje legible
      const messages = Object.entries(backendErrors)
        .map(([field, msgs]) => `${field}: ${(msgs as string[]).join(', ')}`)
        .join(' | ');
      throw new Error(messages);
    }
    // Error general del servidor
    const msg = error?.response?.data?.error || error?.message || 'Error al registrar';
    throw new Error(msg);
  }
}

/**
 * Consulta el estado de la task Celery de setup de Odoo
 * Úsala en la página de éxito para mostrar progreso
 */
export async function getRegistrationStatus(taskId: string): Promise<RegistrationStatusResponse> {
  const response = await apiClient.get<RegistrationStatusResponse>(
    `/api/v1/marketplace/registration-status/${taskId}/`
  );
  return response.data;
}

/**
 * Valida el formato de RUC peruano
 * 11 dígitos, empieza con 10 (persona natural) o 20 (empresa)
 */
export function validateRUC(ruc: string): boolean {
  if (!ruc || ruc.length !== 11) return false;
  if (!/^\d{11}$/.test(ruc)) return false;
  return ruc.startsWith('10') || ruc.startsWith('20');
}

/**
 * Retorna los 3 planes disponibles con sus detalles para mostrar en la UI
 */
export function getTiers() {
  return [
    {
      id: 'starter' as const,
      name: 'Starter',
      price: 'Gratis',
      priceNumber: 0,
      commission: '8%',
      features: [
        'Hasta 100 productos',
        'Hasta 50 órdenes/mes',
        'Soporte por email',
        'Panel de control básico',
      ],
      highlighted: false,
    },
    {
      id: 'pro' as const,
      name: 'Pro',
      price: 'S/ 99/mes',
      priceNumber: 99,
      commission: '5%',
      features: [
        'Hasta 1,000 productos',
        'Hasta 500 órdenes/mes',
        'Soporte prioritario',
        'Analytics avanzados',
        'Descuentos y cupones',
      ],
      highlighted: true,
    },
    {
      id: 'premium' as const,
      name: 'Premium',
      price: 'S/ 299/mes',
      priceNumber: 299,
      commission: '3%',
      features: [
        'Productos ilimitados',
        'Órdenes ilimitadas',
        'Instancia Odoo dedicada',
        'Soporte 24/7',
        'Integración personalizada',
      ],
      highlighted: false,
    },
  ];
}
