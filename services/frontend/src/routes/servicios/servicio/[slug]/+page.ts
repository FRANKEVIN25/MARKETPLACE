import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import { buildServiceAggregate } from '$lib/data/service-showcase';
import type { ServiceListing } from '$lib/api/types';

export const load: PageLoad = async ({ params }) => {
  let listings: ServiceListing[] = [];
  let loadError: string | null = null;

  try {
    const response = await api.services.list({ page_size: 200 });
    listings = response.results ?? [];
  } catch (err: any) {
    console.error('Error cargando detalle del servicio:', err);
    loadError = err?.message || 'No se pudo cargar el detalle del servicio';
  }

  if (loadError && listings.length === 0) {
    throw error(503, loadError);
  }

  const serviceListings = listings.filter((listing) => listing.serviceSlug === params.slug);

  if (!serviceListings.length) {
    throw error(404, 'Servicio no encontrado');
  }

  const service = buildServiceAggregate(serviceListings);
  const relatedListings = listings
    .filter((listing) => listing.serviceSlug !== params.slug && listing.category === service.category)
    .slice(0, 4);

  return {
    service,
    relatedListings,
    error: loadError,
  };
};
