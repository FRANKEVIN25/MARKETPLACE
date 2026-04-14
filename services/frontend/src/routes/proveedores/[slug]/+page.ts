import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { Product, ProviderReview } from '$lib/api/types';

export const load: PageLoad = async ({ params }) => {
  const providerResult = await api.marketplace.providers.getPublicBySlug(params.slug).catch((err: any) => {
    const status = err?.response?.status;
    if (status === 404) {
      throw error(404, 'Proveedor no encontrado');
    }

    throw error(503, err?.message || 'No se pudo cargar el perfil del proveedor');
  });

  const [reviewsResult, productsResult] = await Promise.allSettled([
    api.marketplace.providers.getPublicReviews(params.slug),
    api.products.list({ provider_id: providerResult.id, page_size: 8 }),
  ]);

  const reviews: ProviderReview[] =
    reviewsResult.status === 'fulfilled' ? reviewsResult.value : providerResult.latest_reviews ?? [];

  const products: Product[] =
    productsResult.status === 'fulfilled' ? productsResult.value.results ?? [] : [];

  const warnings: string[] = [];

  if (reviewsResult.status === 'rejected') {
    warnings.push(reviewsResult.reason?.message || 'No se pudieron cargar las reseñas completas del proveedor.');
  }

  if (productsResult.status === 'rejected') {
    warnings.push(productsResult.reason?.message || 'No se pudo cargar el catálogo del proveedor.');
  }

  return {
    provider: providerResult,
    reviews,
    products,
    warnings,
  };
};
