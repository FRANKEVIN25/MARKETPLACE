import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

export const load: PageLoad = async () => {
  try {
    // Cargar productos destacados (primeros 12)
    const response = await api.products.list({ page_size: 12 });
    
    return {
      products: response.results,
      totalCount: response.count,
    };
  } catch (error) {
    console.error('Error cargando productos:', error);
    return {
      products: [],
      totalCount: 0,
      error: 'No se pudieron cargar los productos',
    };
  }
};
