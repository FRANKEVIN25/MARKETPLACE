/**
 * TypeScript types para la API de Django
 * 
 * Este archivo define todos los "tipos" de datos que usamos.
 * Es como decirle a TypeScript "estos son los formatos de datos que esperamos"
 */

// ============================================
// PROVEEDOR (Provider)
// ============================================
// Un proveedor es una empresa que vende en el marketplace
export interface ProviderGroup {
  id: number;               // ID único del proveedor
  name: string;             // Nombre de la empresa
  slug: string;             // URL amigable (ej: "autopartes-abc")
  ruc?: string;             // RUC (opcional)
  email?: string;           // Email de contacto
  phone?: string;           // Teléfono
  is_active: boolean;       // ¿Está activo?
  is_approved: boolean;     // ¿Está aprobado por admin?
}

// ============================================
// CATEGORÍA
// ============================================
// Las categorías organizan los productos (ej: "Frenos", "Motores")
export interface Category {
  id: number;               // ID único
  name: string;             // Nombre de la categoría
  slug: string;             // URL amigable
  parent?: number;          // ID de categoría padre (si es subcategoría)
  description?: string;     // Descripción
  image?: string;           // URL de la imagen
  is_active: boolean;       // ¿Está activa?
  children_count: number;   // Cantidad de subcategorías
}

// ============================================
// PRODUCTO
// ============================================
// Un producto es lo que se vende en el marketplace
export interface Product {
  id: number;               // ID único
  name: string;             // Nombre del producto
  reference: string;        // Código de referencia
  slug: string;             // URL amigable
  provider_group: number;   // ID del proveedor que lo vende
  provider_name: string;    // Nombre del proveedor
  product_type: 'consu' | 'service' | 'product'; // Tipo de producto
  manufacturer_code?: string; // Código del fabricante
  description?: string;     // Descripción del producto
  image?: string;           // URL de la imagen
  price: string;            // Precio (como texto: "150.00")
  category?: number;        // ID de la categoría
  category_name?: string;   // Nombre de la categoría
  active: boolean;          // ¿Está activo?
  is_synced: boolean;       // ¿Está sincronizado con Odoo?
  created_at: string;       // Fecha de creación
  updated_at: string;       // Fecha de actualización
}

// ============================================
// RESPUESTA PAGINADA
// ============================================
// Cuando pedimos una lista de productos, Django nos responde con este formato
// Incluye la lista Y información de paginación
export interface PaginatedResponse<T> {
  count: number;            // Total de resultados
  next: string | null;      // URL de la página siguiente (o null si es la última)
  previous: string | null;  // URL de la página anterior (o null si es la primera)
  results: T[];             // Array con los resultados
}

// ============================================
// FILTROS DE PRODUCTOS
// ============================================
// Parámetros que podemos usar para filtrar productos
export interface ProductFilters {
  category?: number;        // Filtrar por categoría
  search?: string;          // Buscar por texto
  ordering?: string;        // Ordenar por campo
  page?: number;            // Número de página
  page_size?: number;       // Cuántos resultados por página
}

// ============================================
// REGISTRO DE VENDORS (NUEVO)
// ============================================

/**
 * Datos que el usuario llena en el formulario de registro
 * Esto es lo que enviamos al backend cuando alguien quiere registrarse como vendor
 */
export interface VendorRegistrationData {
  // ---- Datos del usuario Django ----
  // Estos datos son para que el vendor pueda iniciar sesión en el marketplace
  username: string;           // Nombre de usuario único (ej: "juan_autopartes")
  email: string;              // Email del usuario
  password: string;           // Contraseña para login
  password_confirm: string;   // Repetir contraseña (validación)
  
  // ---- Datos del negocio ----
  // Información sobre la empresa del vendor
  business_name: string;      // Nombre de la empresa (ej: "AutoPartes ABC SAC")
  business_email: string;     // Email del negocio (puede ser diferente al personal)
  phone: string;              // Teléfono de contacto
  ruc: string;                // RUC de 11 dígitos (obligatorio en Perú)
  
  // ---- Contraseña para Odoo ----
  // El vendor tendrá acceso a Odoo (ERP) para gestionar sus productos
  // Esta es una contraseña SEPARADA del login del marketplace
  odoo_password: string;      // Password para acceder a Odoo
  odoo_password_confirm: string; // Repetir password
  
  // ---- Plan seleccionado ----
  // El vendor elige qué plan quiere (gratis, pro, premium)
  tier: 'starter' | 'pro' | 'premium';
  
  // ---- Términos y condiciones ----
  // Debe aceptar los términos para registrarse
  accept_terms: boolean;      // Debe ser true
}

/**
 * Respuesta que nos da el backend después de enviar el formulario
 */
export interface VendorRegistrationResponse {
  success: boolean;           // ¿Se registró correctamente? true/false
  message: string;            // Mensaje descriptivo (ej: "Registro exitoso")
  user_id: number;            // ID del usuario Django que se creó
  username: string;           // Username del usuario creado
  task_id: string;            // ID de la tarea Celery (para seguimiento en segundo plano)
  business_name: string;      // Nombre del negocio registrado
}

/**
 * Estado de la tarea de registro en segundo plano
 * Después de registrarse, Celery crea la Company y Usuario en Odoo
 * Podemos consultar el estado de esa tarea
 */
export interface RegistrationStatusResponse {
  state: 'PENDING' | 'SUCCESS' | 'FAILURE'; // Estado actual
  result?: any;               // Resultado si terminó exitosamente
  error?: string;             // Mensaje de error si falló
}

/**
 * Información de los planes disponibles
 * Usaremos esto para mostrar las tarjetas de precios
 */
export interface TierInfo {
  id: 'starter' | 'pro' | 'premium';  // Identificador del plan
  name: string;               // Nombre mostrado (ej: "Plan Starter")
  price: number;              // Precio mensual en soles (0 = gratis)
  features: string[];         // Lista de características del plan
  max_products: number | null; // Máximo de productos (null = ilimitado)
  commission: number;         // Comisión que cobra el marketplace (0.08 = 8%)
  recommended?: boolean;      // ¿Es el plan recomendado?
}