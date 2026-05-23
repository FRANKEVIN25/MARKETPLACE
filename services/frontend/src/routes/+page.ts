import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

const HOME_PRODUCT_LIMIT = 8;

export const load: PageLoad = async () => {
  try {
    // Cargar productos destacados con un tope estricto para el home
    const response = await api.products.list({ page_size: HOME_PRODUCT_LIMIT });
    
    return {
      products: (response.results || []).slice(0, HOME_PRODUCT_LIMIT),
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
