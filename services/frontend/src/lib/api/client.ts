/**
 * Cliente HTTP para la API de Django
 */
import axios, { type AxiosInstance } from 'axios';
import type {
  Product,
  Category,
  PaginatedResponse,
  ProductFilters,
  ServiceCategoryItem,
  ServiceFilters,
  ServiceListing,
  WorkshopLocationOptions,
  Customer,
  Address,
  AuthTokens,
  AuthUser,
  BusinessActivity,
  Order,
  SubOrder,
  CreateOrderPayload,
  UploadPaymentProofPayload,
  VehicleMarca,
  VehicleModelo,
  VehicleVariantFilter,
} from './types';

type RawServiceListing = Omit<ServiceListing, 'district' | 'province' | 'department' | 'totalJobs' | 'successRate' | 'repeatFailureRate' | 'avgRating'> & {
  mainLocation?: {
    id: number;
    name: string;
    address: string;
    district: string;
    province: string;
    department: string;
    latitude: string;
    longitude: string;
    is_main: boolean;
  } | null;
  totalDemand?: number;
  avgRating?: number;
};

function normalizeServiceListing(listing: RawServiceListing): ServiceListing {
  const location = listing.mainLocation ?? null;
  const avgRating = Number(listing.avgRating ?? 0);

  return {
    ...listing,
    mainLocation: location,
    district: location?.district ?? '',
    province: location?.province ?? '',
    department: location?.department ?? '',
    totalJobs: Number(listing.totalDemand ?? 0),
    avgRating,
    // Se mantienen para no romper el resto del frontend mientras migramos la UI
    // a labels más precisos basados en rating/demanda reales del backend.
    successRate: avgRating * 20,
    repeatFailureRate: 0,
  };
}

function normalizeServiceListingResponse(
  response: PaginatedResponse<RawServiceListing>,
): PaginatedResponse<ServiceListing> {
  return {
    ...response,
    results: (response.results ?? []).map(normalizeServiceListing),
  };
}

// Configuración base
const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
const API_TIMEOUT = parseInt(import.meta.env.PUBLIC_API_TIMEOUT || '10000');

// Instancia de Axios
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper para headers con JWT
function authHeaders(token: string) {
  return { Authorization: `Bearer ${token}` };
}

// Interceptor para logging (solo desarrollo)
if (import.meta.env.DEV) {
  apiClient.interceptors.request.use((config) => {
    console.log('🚀 API Request:', config.method?.toUpperCase(), config.url);
    return config;
  });

  apiClient.interceptors.response.use(
    (response) => {
      console.log('✅ API Response:', response.status, response.config.url);
      return response;
    },
    (error) => {
      console.error('❌ API Error:', error.response?.status, error.config?.url);
      return Promise.reject(error);
    }
  );
}

/**
 * API Client
 */
export const api = {
  /**
   * Health Check
   */
  async healthCheck() {
    const response = await apiClient.get('/api/v1/health/');
    return response.data;
  },
  
/**
   * PRODUCTOS
   */
  products: {
    /**
     * Obtener lista de productos del marketplace (público)
     */
    async list(filters?: ProductFilters): Promise<PaginatedResponse<Product>> {
      const params: Record<string, string> = {};

      // Categoría (ID o slug)
      if (filters?.category) {
        // Usamos category_id como parámetro principal, pero el backend también
        // acepta "category"; mantenerlo simple y explícito.
        params['category_id'] = filters.category.toString();
      }
      if (filters?.category_slug) {
        params['category_slug'] = filters.category_slug;
      }

      if (filters?.search) params['q'] = filters.search; // alias amigable de search
      if (filters?.ordering) params['ordering'] = filters.ordering;
      if (filters?.page) params['page'] = filters.page.toString();
      if (filters?.page_size) params['page_size'] = filters.page_size.toString();

      // Filtros por vehículo
      if (filters?.marca_id) params['marca_id'] = String(filters.marca_id);
      if (filters?.modelo_id) params['modelo_id'] = String(filters.modelo_id);
      if (filters?.variante_id) params['variante_id'] = String(filters.variante_id);

      // Filtro por proveedor
      if (filters?.provider_id) {
        params['provider_id'] = String(filters.provider_id);
      }

      // Filtro por productos universales
      if (filters?.es_universal !== undefined && filters.es_universal !== null) {
        params['es_universal'] = filters.es_universal ? 'true' : 'false';
      }

      const response = await apiClient.get<PaginatedResponse<Product>>(
        '/api/v1/products/marketplace/',
        { params }
      );
      return response.data;
    },

    /**
     * Obtener detalle de un producto por ID
     */
    async getById(id: number | string): Promise<Product> {
      const response = await apiClient.get<Product>(
        `/api/v1/products/marketplace/${id}/`
      );
      return response.data;
    },

    /**
     * Obtener detalle de un producto por slug
     */
    async getBySlug(slug: string): Promise<Product> {
      const response = await apiClient.get<PaginatedResponse<Product>>(
        '/api/v1/products/marketplace/',
        { params: { search: slug } }
      );
      
      const product = response.data.results.find(p => p.slug === slug);
      
      if (!product) {
        throw new Error('Producto no encontrado');
      }
      
      return product;
    },

    /**
     * Buscar productos
     */
    async search(query: string): Promise<Product[]> {
      const response = await apiClient.get<PaginatedResponse<Product>>(
        '/api/v1/products/marketplace/',
        { params: { search: query, page_size: 20 } }
      );
      return response.data.results;
    },
  },

  /**
   * VEHÍCULOS PÚBLICOS (para filtros de catálogo)
   */
  publicVehicles: {
    /**
     * Marcas con productos compatibles en el marketplace
     */
    async marcas(): Promise<VehicleMarca[]> {
      const response = await apiClient.get<VehicleMarca[] | { results: VehicleMarca[] }>(
        '/api/v1/vehicles/public/marcas/'
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },

    /**
     * Modelos para una marca con productos compatibles
     */
    async modelos(marca_id: number): Promise<VehicleModelo[]> {
      const response = await apiClient.get<VehicleModelo[] | { results: VehicleModelo[] }>(
        '/api/v1/vehicles/public/modelos/',
        { params: { marca_id } }
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },

    /**
     * Variantes para un modelo con productos compatibles
     */
    async variantes(modelo_id: number): Promise<VehicleVariantFilter[]> {
      const response = await apiClient.get<VehicleVariantFilter[] | { results: VehicleVariantFilter[] }>(
        '/api/v1/vehicles/public/variantes/',
        { params: { modelo_id } }
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },
  },

  /**
   * CATEGORÍAS
   */
  categories: {
    /**
     * Obtener lista de categorías
     */
    async list(): Promise<Category[]> {
      const response = await apiClient.get<Category[] | { results: Category[] }>(
        '/api/v1/products/public/categories/'
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },

    /**
     * Obtener detalle de una categoría
     */
    async getBySlug(slug: string): Promise<Category> {
      const response = await apiClient.get<Category[]>(
        '/api/v1/products/categories/',
        { params: { search: slug } }
      );
      
      const category = response.data.find(c => c.slug === slug);
      
      if (!category) {
        throw new Error('Categoría no encontrada');
      }
      
      return category;
    },
  },

  /**
   * SERVICIOS DE TALLER
   */
  services: {
    async categories(): Promise<ServiceCategoryItem[]> {
      const response = await apiClient.get<PaginatedResponse<ServiceCategoryItem> | ServiceCategoryItem[]>(
        '/api/v1/services/categories/'
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },

    async list(filters?: ServiceFilters): Promise<PaginatedResponse<ServiceListing>> {
      const params: Record<string, string> = {};

      if (filters?.q) params['q'] = filters.q;
      if (filters?.category_id) params['category_id'] = String(filters.category_id);
      if (filters?.category) params['category'] = filters.category;
      if (filters?.service_type) params['service_type'] = filters.service_type;
      if (filters?.district) params['district'] = filters.district;
      if (filters?.province) params['province'] = filters.province;
      if (filters?.department) params['department'] = filters.department;
      if (filters?.verified_only !== undefined) params['verified_only'] = String(filters.verified_only);
      if (filters?.specialized_only !== undefined) params['specialized_only'] = String(filters.specialized_only);
      if (filters?.erp_only !== undefined) params['erp_only'] = String(filters.erp_only);
      if (filters?.marca_id) params['marca_id'] = String(filters.marca_id);
      if (filters?.modelo_id) params['modelo_id'] = String(filters.modelo_id);
      if (filters?.page) params['page'] = String(filters.page);
      if (filters?.page_size) params['page_size'] = String(filters.page_size);
      if (filters?.ordering) params['ordering'] = filters.ordering;

      const response = await apiClient.get<PaginatedResponse<RawServiceListing>>(
        '/api/v1/services/listings/',
        { params }
      );
      return normalizeServiceListingResponse(response.data);
    },

    async locationOptions(
      department?: string,
      province?: string,
    ): Promise<WorkshopLocationOptions> {
      const params: Record<string, string> = {};
      if (department) params['department'] = department;
      if (province) params['province'] = province;
      const response = await apiClient.get<WorkshopLocationOptions>(
        '/api/v1/services/locations/',
        { params },
      );
      return response.data;
    },
  },

  /**
   * AUTH
   */
  auth: {
    async login(username: string, password: string): Promise<AuthTokens> {
      const response = await apiClient.post<AuthTokens>('/api/v1/auth/token/', { username, password });
      return response.data;
    },
    async refreshToken(refresh: string): Promise<{ access: string }> {
      const response = await apiClient.post<{ access: string }>('/api/v1/auth/token/refresh/', { refresh });
      return response.data;
    },
    async getMe(token: string): Promise<AuthUser> {
      const response = await apiClient.get<AuthUser>('/api/v1/auth/me/', { headers: authHeaders(token) });
      return response.data;
    },
  },

  /**
   * CUSTOMER
   */
  customer: {
    async getProfile(token: string): Promise<Customer> {
      const response = await apiClient.get<Customer>('/api/v1/customer/customers/me/', { headers: authHeaders(token) });
      return response.data;
    },
    async updateProfile(token: string, data: Partial<Customer>): Promise<Customer> {
      const response = await apiClient.patch<Customer>('/api/v1/customer/customers/me/', data, { headers: authHeaders(token) });
      return response.data;
    },
    async getAddresses(token: string): Promise<Address[]> {
      const response = await apiClient.get<{ results: Address[] } | Address[]>('/api/v1/customer/addresses/', { headers: authHeaders(token) });
      // El endpoint puede devolver respuesta paginada {results:[]} o array directo
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },
    async createAddress(token: string, data: Partial<Address>): Promise<Address> {
      const response = await apiClient.post<Address>('/api/v1/customer/addresses/', data, { headers: authHeaders(token) });
      return response.data;
    },
    async updateAddress(token: string, id: number, data: Partial<Address>): Promise<Address> {
      const response = await apiClient.patch<Address>(`/api/v1/customer/addresses/${id}/`, data, { headers: authHeaders(token) });
      return response.data;
    },
    async deleteAddress(token: string, id: number): Promise<void> {
      await apiClient.delete(`/api/v1/customer/addresses/${id}/`, { headers: authHeaders(token) });
    },
    async register(data: {
      customer_type: 'individual' | 'company';
      document_type: 'DNI' | 'RUC';
      document_number: string;
      business_activity?: BusinessActivity | '';
      email: string;
      password: string;
    }): Promise<{ customer: Customer; tokens: AuthTokens }> {
      const response = await apiClient.post<{ customer: Customer; tokens: AuthTokens }>(
        '/api/v1/customer/customers/register/', data
      );
      return response.data;
    },
  },

  /**
   * ÓRDENES
   */
  orders: {
    /** Crear una nueva orden */
    async createOrder(token: string, payload: CreateOrderPayload): Promise<Order> {
      const response = await apiClient.post<Order>(
        '/api/v1/orders/orders/create_order/',
        payload,
        { headers: authHeaders(token) }
      );
      return response.data;
    },

    /** Listar órdenes del cliente autenticado */
    async getOrders(token: string): Promise<Order[]> {
      const response = await apiClient.get<{ results: Order[] } | Order[]>(
        '/api/v1/orders/orders/',
        { headers: authHeaders(token) }
      );
      const data = response.data as any;
      return Array.isArray(data) ? data : (data.results ?? []);
    },

    /** Obtener detalle de una orden por ID */
    async getOrder(token: string, orderId: number): Promise<Order> {
      const response = await apiClient.get<Order>(
        `/api/v1/orders/orders/${orderId}/`,
        { headers: authHeaders(token) }
      );
      return response.data;
    },

    /** Obtener detalle de una orden por número (ORD-2026-00001) */
    async getOrderByNumber(token: string, orderNumber: string): Promise<Order> {
      const response = await apiClient.get<{ results: Order[] }>(
        `/api/v1/orders/orders/?order_number=${orderNumber}`,
        { headers: authHeaders(token) }
      );
      const data = response.data as any;
      const results: Order[] = Array.isArray(data) ? data : (data.results ?? []);
      if (!results.length) throw new Error('Orden no encontrada');
      return results[0];
    },

    /** Subir comprobante de pago para una sub-orden */
    async uploadPaymentProof(token: string, payload: UploadPaymentProofPayload): Promise<void> {
      const formData = new FormData();
      formData.append('sub_order_id', String(payload.sub_order_id));
      formData.append('payment_method', payload.payment_method);
      formData.append('file', payload.file);
      formData.append('amount', String(payload.amount));
      if (payload.operation_number) {
        formData.append('operation_number', payload.operation_number);
      }
      await apiClient.post(
        '/api/v1/orders/orders/upload_payment_proof/',
        formData,
        {
          headers: {
            ...authHeaders(token),
            'Content-Type': 'multipart/form-data',
          },
        }
      );
    },

    /** Marcar una sub-orden como recibida por el cliente */
    async markSubOrderReceived(token: string, subOrderId: number): Promise<SubOrder> {
      const response = await apiClient.post<{ sub_order: SubOrder }>(
        `/api/v1/orders/suborders/${subOrderId}/mark-received/`,
        {},
        { headers: authHeaders(token) }
      );
      return response.data.sub_order;
    },
  },
};

export default api;
