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
// STOCK ITEM
// ============================================
// Representa la cantidad de un producto en un almacén específico
export interface StockItem {
  id: number;                   // ID único
  warehouse: number;            // ID del almacén
  warehouse_name: string;       // Nombre del almacén
  warehouse_city: string;       // Ciudad del almacén
  quantity: number;             // Cantidad disponible
  is_low_stock: boolean;        // ¿Stock bajo (< 5)?
  is_out_of_stock: boolean;     // ¿Sin stock?
  updated_at: string;           // Última actualización
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
  tax_percent: string; 
  category?: number | string; // ID o nombre de la categoría (según endpoint)
  category_name?: string;   // Nombre de la categoría
  es_universal: boolean;    // ¿Compatible con todos los vehículos?
  total_stock: number;      // Stock total sumado de todos los almacenes
  stock_items?: StockItem[]; // Detalle de stock por almacén (opcional en listados)
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
// CUSTOMER
// ============================================
export type BusinessActivity =
  | 'workshop'
  | 'parts_supplier'
  | 'retail_store'
  | 'distributor'
  | 'fleet'
  | 'dealer'
  | 'manufacturer'
  | 'insurance'
  | 'other';

export interface Customer {
  id: number;
  customer_id: string;
  user: number;
  username: string;
  email: string;
  full_name: string;
  customer_type: 'individual' | 'company';
  phone: string;
  document_type: 'DNI' | 'RUC' | 'CE' | 'PASSPORT';
  document_number: string;
  full_document: string;
  company_name?: string;
  business_activity?: BusinessActivity | '';
  business_activity_display?: string;
  receive_newsletter: boolean;
  receive_promotions: boolean;
  is_active: boolean;
  is_verified: boolean;
  is_workshop?: boolean;
  created_at: string;
  updated_at: string;
  last_order_date?: string;
}

export interface Address {
  id: number;
  address_id: string;
  customer: number;
  customer_name: string;
  address_type: 'shipping' | 'agency' | 'business';
  contact_name: string;
  contact_phone: string;
  street: string;
  street_number?: string;
  apartment?: string;
  district: string;
  city: string;
  state: string;
  postal_code?: string;
  country: string;
  agency_name?: string;
  is_default: boolean;
  reference?: string;
  full_address: string;
  is_agency: boolean;
  created_at: string;
  updated_at: string;
}

export interface CustomerStats {
  id: number;
  customer: number;
  customer_name: string;
  total_orders: number;
  total_spent: string;
  average_order_value: string;
  preferred_brands?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

// ============================================
// ÓRDENES
// ============================================

export type OrderStatus =
  | 'pendiente_pago'
  | 'pagado'
  | 'procesando'
  | 'enviado'
  | 'completado'
  | 'cancelado';

export type DeliveryMethod = 'domicilio' | 'agencia' | 'tienda';

export type SubOrderStatus =
  | 'pendiente_pago'   // timer activo, cliente no ha subido comprobante
  | 'pago_en_revision' // comprobante subido, esperando aprobación del proveedor
  | 'pago_rechazado'   // v5: proveedor rechazó el comprobante, cliente debe corregir
  | 'confirmado'       // pago aprobado, orden confirmada en Odoo
  | 'enviado'          // despacho registrado en Odoo
  | 'entregado'        // cliente confirmó recepción
  | 'cancelado';       // expirado o cancelado manualmente

export type PaymentMethod =
  | 'transferencia'
  | 'yape'
  | 'plin'
  | 'efectivo_contraentrega'
  | 'efectivo_tienda';

/** Item individual dentro de una orden */
export interface OrderItem {
  id: number;
  product: number;
  product_name: string;
  product_sku: string;
  provider: number;
  provider_name: string;
  quantity: number;
  unit_price: string;
  igv_rate: string;
  igv_amount: string;
  discount: string;
  subtotal: string;
}

/** Datos de pago del proveedor (cuentas bancarias, Yape, Plin) */
export interface ProviderPaymentInfo {
  banco_nombre: string | null;
  banco_cuenta: string | null;
  banco_cci: string | null;
  yape_numero: string | null;
  plin_numero: string | null;
}

/** Sub-orden agrupada por proveedor */
export interface SubOrder {
  id: number;
  sub_order_number: string;
  order: number;
  provider: number;
  provider_name: string;
  provider_tax_regime: string;
  status: SubOrderStatus;
  subtotal: string;
  discount_percent: string;
  discount: string;
  igv_rate: string;
  igv_amount: string;
  total: string;
  tracking_number: string;
  created_at: string;
  updated_at: string;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  // Flags (sustituyen estados extra)
  payment_rejected: boolean;   // proveedor rechazó el último comprobante
  rejection_reason: string;    // motivo de rechazo del proveedor (v5)
  expired: boolean;            // superó payment_deadline sin pagar
  refunded: boolean;           // reembolso realizado
  odoo_sync_error: boolean;    // error al sincronizar con Odoo
  items: OrderItem[];
  payments: PaymentProof[];    // historial de intentos de pago
  provider_payment_info: ProviderPaymentInfo;
}

/** Orden principal del cliente */
export interface Order {
  id: number;
  order_number: string;
  customer: number;
  customer_name: string;
  customer_email: string;
  status: OrderStatus;
  payment_deadline: string | null;   // ISO datetime; null = sin límite
  delivery_method: DeliveryMethod;
  shipping_address: number | null;
  shipping_address_detail: {
    contact_name: string;
    contact_phone: string;
    full_address: string;
    reference: string;
  } | null;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  customer_notes: string;
  created_at: string;
  updated_at: string;
  provider_count: number;
  sub_orders: SubOrder[];
  items: OrderItem[];
}

/** Comprobante de pago subido por el cliente */
export interface PaymentProof {
  id: number;
  sub_order: number;
  payment_method: PaymentMethod;
  file: string;                      // URL (puede estar vacío para pagos futuros por API)
  operation_number: string;
  amount: string;
  status: 'uploaded' | 'approved' | 'rejected';
  status_display: string;
  rejection_reason: string;          // completado por el proveedor al rechazar
  external_transaction_id: string;   // para integraciones futuras (Culqi, Niubiz, etc.)
  uploaded_by: number;
  uploaded_by_name: string;
  uploaded_at: string;
  verified_by: number | null;
  verified_by_name: string | null;
  verified_at: string | null;
}

/** Payload para crear una orden */
export interface CreateOrderPayload {
  customer_id: number;
  shipping_address_id?: number | null;
  delivery_method: DeliveryMethod;
  customer_notes?: string;
  items: { product_id: number; quantity: number }[];
}

/** Payload para subir un comprobante de pago */
export interface UploadPaymentProofPayload {
  sub_order_id: number;
  payment_method: PaymentMethod;
  file: File;
  operation_number?: string;
  amount: number;
}

// ============================================
// FILTROS DE PRODUCTOS
// ============================================
// Parámetros que podemos usar para filtrar productos
export interface ProductFilters {
  category?: number;        // ID de la categoría seleccionada
  search?: string;          // Buscar por texto (q)
  ordering?: string;        // Ordenar por campo
  page?: number;            // Número de página
  page_size?: number;       // Cuántos resultados por página

  // Filtros adicionales de marketplace
  provider_id?: number;     // Filtrar por proveedor (Provider.id)
  es_universal?: boolean | null; // Filtrar por productos universales
  category_slug?: string;   // Alternativa textual a category

  // Filtros por vehículo (para tiparlos correctamente)
  marca_id?: number;
  modelo_id?: number;
  variante_id?: number;
}

// ============================================
// SERVICIOS DE TALLER
// ============================================

export type ServiceType = 'maintenance' | 'repair' | 'diagnostic';
export type ServiceLevel = 'BASIC' | 'MANAGED' | 'ADVANCED';
export type CommerceLevel = 'NONE' | 'BUYER' | 'B2B_BUYER' | 'SELLER';

export interface ServiceCategoryItem {
  id: number;
  name: string;
  description?: string;
  icon?: string;
  order: number;
  services_count: number;
  workshops_count: number;
}

export interface WorkshopLocationOptions {
  departments: string[];
  provinces: string[];
  districts: string[];
}

export interface ServiceMainLocation {
  id: number;
  name: string;
  address: string;
  district: string;
  province: string;
  department: string;
  latitude: string;
  longitude: string;
  is_main: boolean;
}

export interface ServiceListing {
  id: number;
  serviceSlug: string;
  serviceName: string;
  category: string;
  serviceType: ServiceType;
  workshopId: number;
  workshopSlug: string;
  workshopName: string;
  workshopHeadline: string;
  mainLocation?: ServiceMainLocation | null;
  district: string;
  province: string;
  department: string;
  priceMin: number | null;
  priceMax: number | null;
  durationMin: number;
  verified: boolean;
  specialized: boolean;
  erpIntegrated: boolean;
  certified: boolean;
  totalJobs: number;
  avgRating: number;
  successRate: number;
  repeatFailureRate: number;
  yearsExperience: number;
  serviceLevel: ServiceLevel;
  commerceLevel: CommerceLevel;
  vehicleExpertise: string[];
  trustNotes: string[];
}

export interface ServiceFilters {
  q?: string;
  category_id?: number;
  category?: string;
  service_type?: ServiceType;
  district?: string;
  province?: string;
  department?: string;
  verified_only?: boolean;
  specialized_only?: boolean;
  erp_only?: boolean;
  marca_id?: number;
  modelo_id?: number;
  page?: number;
  page_size?: number;
  ordering?: string;
}

// ============================================
// VEHÍCULOS PARA FILTROS DE PRODUCTO
// ============================================

export interface VehicleMarca {
  id: number;
  nombre: string;
  slug: string;
  activo: boolean;
}

export interface VehicleModelo {
  id: number;
  nombre: string;
  marca: number;
  marca_nombre: string;
  slug: string;
  activo: boolean;
}

export interface VehicleVariantFilter {
  id: number;
  nombre: string;
  modelo: number;
  modelo_nombre: string;
  anio_inicio?: number;
  anio_fin?: number;
  activo: boolean;
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
  task_id: string;
  status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'RETRY';
  ready: boolean;
  result?: {
    success: boolean;
    provider_id: number;
    provider_name: string;
    odoo_company_id: number;
    odoo_user_id: number;
    odoo_username: string;
    message: string;
  };
  error?: string;
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
// ====== VENDOR REGISTRATION ======

