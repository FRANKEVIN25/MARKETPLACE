/**
 * TypeScript types para la API de Django
 */

// Proveedor
export interface ProviderGroup {
  id: number;
  name: string;
  slug: string;
  ruc?: string;
  email?: string;
  phone?: string;
  is_active: boolean;
  is_approved: boolean;
}

// Categoría
export interface Category {
  id: number;
  name: string;
  slug: string;
  parent?: number;
  description?: string;
  image?: string;
  is_active: boolean;
  children_count: number;
}

// Producto
export interface Product {
  id: number;
  name: string;
  reference: string;
  slug: string;
  provider_group: number;
  provider_name: string;
  product_type: 'consu' | 'service' | 'product';
  manufacturer_code?: string;
  description?: string;
  image?: string;
  price: string;
  category?: number;
  category_name?: string;
  active: boolean;
  is_synced: boolean;
  created_at: string;
  updated_at: string;
}

// Respuesta paginada
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Filtros de productos
export interface ProductFilters {
  category?: number;
  search?: string;
  ordering?: string;
  page?: number;
  page_size?: number;
}
