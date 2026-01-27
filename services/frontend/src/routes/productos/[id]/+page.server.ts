import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { Product } from '$lib/api/types';

interface ApiError {
  response?: {
    status: number;
    data: {
      detail?: string;
    };
  };
}

export const load: PageServerLoad = async ({ params }) => {
  try {
    const product: Product = await api.products.getById(params.id);

    return {
      product,
      title: product.name,
      description: product.description || `Detalle del producto ${product.name}`
    };
  } catch (err) {
    const apiError = err as ApiError;
    const status = apiError.response?.status || 500;
    const message = apiError.response?.data?.detail || 'No se pudo cargar el producto';

    throw error(status, message);
  }
};
