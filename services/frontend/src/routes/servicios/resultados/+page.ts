import type { PageLoad } from './$types';
import { api } from '$lib/api/client';
import type { ServiceFilters } from '$lib/api/types';

export const load: PageLoad = async ({ url }) => {
  const category_id  = url.searchParams.get('category_id');
  const marca_id     = url.searchParams.get('marca_id');
  const modelo_id    = url.searchParams.get('modelo_id');
  const department   = url.searchParams.get('department') ?? '';
  const province     = url.searchParams.get('province')   ?? '';
  const district     = url.searchParams.get('district')   ?? '';

  const filters: ServiceFilters = { page_size: 200 };
  if (category_id) filters.category_id = Number(category_id);
  if (marca_id)    filters.marca_id    = Number(marca_id);
  if (modelo_id)   filters.modelo_id   = Number(modelo_id);
  if (department)  filters.department  = department;
  if (province)    filters.province    = province;
  if (district)    filters.district    = district;

  const initialFilters = {
    category_id: category_id ? Number(category_id) : null,
    marca_id:    marca_id    ? Number(marca_id)    : null,
    modelo_id:   modelo_id   ? Number(modelo_id)   : null,
    department,
    province,
    district,
  };

  try {
    const [listingsResponse, categories, marcas] = await Promise.all([
      api.services.list(filters),
      api.services.categories(),
      api.publicVehicles.marcas(),
    ]);

    const marcaIdNum = initialFilters.marca_id;
    const modelos = marcaIdNum ? await api.publicVehicles.modelos(marcaIdNum) : [];

    return {
      serviceListings: listingsResponse.results ?? [],
      serviceCategories: categories ?? [],
      marcas,
      modelos,
      totalCount: listingsResponse.count ?? 0,
      initialFilters,
      error: null,
    };
  } catch (error: any) {
    console.error('Error cargando resultados de servicios:', error);

    return {
      serviceListings: [],
      serviceCategories: [],
      marcas: [],
      modelos: [],
      totalCount: 0,
      initialFilters,
      error: error?.message || 'Error al cargar servicios de taller',
    };
  }
};
