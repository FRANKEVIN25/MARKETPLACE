<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';
  import ProviderHero from '$lib/components/provider-profile/ProviderHero.svelte';
  import ProviderMetrics from '$lib/components/provider-profile/ProviderMetrics.svelte';
  import ProviderReviewFeed from '$lib/components/provider-profile/ProviderReviewFeed.svelte';

  export let data: PageData;

  const provider = data.provider;
  const reviews = data.reviews;
  const products = data.products;
  const averageRating = Number(provider.rating_average || 0);
  const productCatalogUrl = `/productos?provider_id=${provider.id}`;

  const signalCards = [
    {
      label: 'Plan operativo',
      value: provider.tier_display,
      description: 'Nivel comercial visible para el cliente final.',
    },
    {
      label: 'Catalogo vivo',
      value: `${provider.products_count}`,
      description: 'Productos publicados por este proveedor en el marketplace.',
    },
    {
      label: 'Scope vehicular',
      value: `${provider.vehicle_scope_count}`,
      description: 'Variantes habilitadas para su operacion actual.',
    },
    {
      label: 'Comprobantes',
      value: provider.emite_comprobante_display,
      description: 'Regla tributaria visible en la ficha publica.',
    },
  ];
</script>

<svelte:head>
  <title>{provider.name} | Proveedor | ECOMPARTS</title>
  <meta
    name="description"
    content={`Perfil del proveedor ${provider.name} con rating, reseñas y catálogo publicado en ECOMPARTS.`}
  />
</svelte:head>

<div class="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eff6ff_18%,#fff7ed_100%)]">
  <section class="mx-auto max-w-7xl px-6 py-10 md:py-14">
    <div class="mb-6 flex flex-wrap items-center gap-3 text-sm font-medium text-slate-500">
      <a href="/productos" class="transition hover:text-slate-900">Productos</a>
      <span>/</span>
      <span class="text-slate-900">{provider.name}</span>
    </div>

    <ProviderHero {provider} {averageRating} {productCatalogUrl} />
  </section>

  <section class="mx-auto max-w-7xl space-y-10 px-6 pb-16">
    {#if data.warnings.length > 0}
      <div class="rounded-[1.75rem] border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <h2 class="text-lg font-bold">Parte del perfil no pudo refrescarse</h2>
        <div class="mt-3 space-y-1 text-sm">
          {#each data.warnings as warning}
            <p>{warning}</p>
          {/each}
        </div>
      </div>
    {/if}

    <ProviderMetrics
      ratingBreakdown={provider.rating_breakdown}
      {averageRating}
      ratingCount={provider.rating_count}
      publishedAt={provider.created_at}
    />

    <section class="grid gap-8 xl:grid-cols-[0.95fr,1.05fr]">
      <article class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_24px_70px_-45px_rgba(15,23,42,0.55)]">
        <div class="flex items-end justify-between gap-4">
          <div>
            <p class="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">Ficha base</p>
            <h2 class="mt-2 text-3xl font-black text-slate-950">Informacion estructurada del proveedor</h2>
          </div>
          <a href={productCatalogUrl} class="text-sm font-semibold text-cyan-700 transition hover:text-cyan-800">Ver catalogo completo</a>
        </div>

        <div class="mt-8 grid gap-4 sm:grid-cols-2">
          {#each signalCards as card}
            <div class="rounded-[1.5rem] border border-slate-200 bg-[linear-gradient(180deg,#ffffff,#f8fafc)] p-5">
              <p class="text-xs uppercase tracking-[0.22em] text-slate-500">{card.label}</p>
              <p class="mt-3 text-2xl font-black text-slate-950">{card.value}</p>
              <p class="mt-2 text-sm leading-6 text-slate-600">{card.description}</p>
            </div>
          {/each}
        </div>

        <div class="mt-6 rounded-[1.5rem] bg-slate-950 p-6 text-white">
          <p class="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">Lectura comercial</p>
          <p class="mt-3 text-lg leading-8 text-white/80">
            Esta plantilla no intenta inventar una landing distinta por proveedor. Mantiene una base comun y deja que el contenido real cambie con reputacion, catalogo, contacto y actividad operativa.
          </p>
        </div>
      </article>

      <ProviderReviewFeed {reviews} />
    </section>

    <section class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_24px_70px_-45px_rgba(15,23,42,0.55)]">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-700">Catalogo publicado</p>
          <h2 class="mt-2 text-3xl font-black text-slate-950">Productos visibles de este proveedor</h2>
        </div>
        <a href={productCatalogUrl} class="rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:text-slate-950">
          Abrir todo el catalogo
        </a>
      </div>

      {#if products.length === 0}
        <div class="mt-8 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
          Este proveedor aun no tiene productos visibles en el catalogo publico.
        </div>
      {:else}
        <div class="mt-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {#each products as product}
            <ProductCard {product} />
          {/each}
        </div>
      {/if}
    </section>
  </section>
</div>
