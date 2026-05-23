import type { PageLoad } from './$types';
import { api } from '$lib/api/client';

const PAGE_SIZE = 15;

export const load: PageLoad = async ({ url }) => {
  try {
    const params = url.searchParams;

    const page = Number(params.get('page') ?? '1');
    const page_size = PAGE_SIZE;

    // Categoría desde la URL (acepta category_id o category por compatibilidad)
    const categoryIdParam = params.get('category_id') ?? params.get('category');

    const providerIdParam = params.get('provider_id');
    const esUniversalParam = params.get('es_universal');

    const filters = {
      category: categoryIdParam ? Number(categoryIdParam) : undefined,
      search: params.get('q') ?? undefined,
      ordering: params.get('ordering') ?? '-created_at',
      page,
      page_size,
      // Filtros de vehículo (se leen directamente de la URL)
      marca_id: params.get('marca_id') ? Number(params.get('marca_id')) : undefined,
      modelo_id: params.get('modelo_id') ? Number(params.get('modelo_id')) : undefined,
      variante_id: params.get('variante_id') ? Number(params.get('variante_id')) : undefined,
      provider_id: providerIdParam ? Number(providerIdParam) : undefined,
      es_universal:
        esUniversalParam === null
          ? undefined
          : esUniversalParam === 'true'
          ? true
          : esUniversalParam === 'false'
          ? false
          : undefined,
    };

    const [response, marcas, categories] = await Promise.all([
      api.products.list(filters),
      api.publicVehicles.marcas(),
      api.categories.list(),
    ]);

    const products = (response.results || []).slice(0, PAGE_SIZE);

    return {
      products,
      totalCount: response.count || 0,
      marcas,
      categories,
      filtrosIniciales: {
        marca_id: params.get('marca_id'),
        modelo_id: params.get('modelo_id'),
        variante_id: params.get('variante_id'),
        q: params.get('q') ?? '',
        ordering: params.get('ordering') ?? '-created_at',
        page,
        category_id: categoryIdParam,
        provider_id: providerIdParam,
        es_universal: esUniversalParam,
      },
      error: null,
    };
  } catch (error: any) {
    console.error('Error cargando productos:', error);

    return {
      products: [],
      totalCount: 0,
      marcas: [],
      categories: [],
      filtrosIniciales: {
        marca_id: null,
        modelo_id: null,
        variante_id: null,
        q: '',
        ordering: '-created_at',
        page: 1,
        category_id: null,
        provider_id: null,
        es_universal: null,
      },
      error: error.message || 'Error al cargar productos',
    };
  }
};
