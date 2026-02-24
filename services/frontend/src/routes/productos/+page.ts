import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageLoad = async () => {
  try {
    // Llamar a la API para obtener productos
    const response = await api.products.list({ page_size: 100 });
    
    return {
      products: response.results || [],
      totalCount: response.count || 0,
      error: null
    };
  } catch (error: any) {
    console.error('Error cargando productos:', error);
    
    return {
      products: [],
      totalCount: 0,
      error: error.message || 'Error al cargar productos'
    };
  }
};
