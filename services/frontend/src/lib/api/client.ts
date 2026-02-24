/**
 * Cliente HTTP para la API de Django
 */
import axios, { type AxiosInstance } from 'axios';
import type { Product, Category, PaginatedResponse, ProductFilters } from './types';

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
      const params = new URLSearchParams();
      
      if (filters?.category) params.append('category', filters.category.toString());
      if (filters?.search) params.append('search', filters.search);
      if (filters?.ordering) params.append('ordering', filters.ordering);
      if (filters?.page) params.append('page', filters.page.toString());
      if (filters?.page_size) params.append('page_size', filters.page_size.toString());

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
   * CATEGORÍAS
   */
  categories: {
    /**
     * Obtener lista de categorías
     */
    async list(): Promise<Category[]> {
      const response = await apiClient.get<Category[]>(
        '/api/v1/products/categories/'
      );
      return response.data;
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
};

export default api;
