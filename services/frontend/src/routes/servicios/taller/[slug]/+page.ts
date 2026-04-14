import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import { buildWorkshopAggregate } from '$lib/data/service-showcase';
import type { ServiceListing } from '$lib/api/types';

export const load: PageLoad = async ({ params }) => {
  let listings: ServiceListing[] = [];
  let loadError: string | null = null;

  try {
    const response = await api.services.list({ page_size: 200 });
    listings = response.results ?? [];
  } catch (err: any) {
    console.error('Error cargando detalle del taller:', err);
    loadError = err?.message || 'No se pudo cargar el detalle del taller';
  }

  if (loadError && listings.length === 0) {
    throw error(503, loadError);
  }

  const workshopListings = listings.filter((listing) => listing.workshopSlug === params.slug);

  if (!workshopListings.length) {
    throw error(404, 'Taller no encontrado');
  }

  const workshop = buildWorkshopAggregate(workshopListings);
  const relatedListings = listings.filter((listing) => listing.workshopSlug !== params.slug).slice(0, 4);

  return {
    workshop,
    relatedListings,
    error: loadError,
  };
};
