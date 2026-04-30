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

<div class="min-h-screen">
  <!-- Breadcrumb -->
  <div class="bg-iron-900 border-b border-steel-600/30">
    <div class="container-responsive py-3">
      <div class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-steel-500">
        <a href="/productos" class="hover:text-rust-500 transition-colors">PRODUCTOS</a>
        <span class="text-steel-700">/</span>
        <span class="text-bone truncate">{provider.name.toUpperCase()}</span>
      </div>
    </div>
  </div>

  <!-- Hero -->
  <div class="container-responsive py-8">
    <ProviderHero {provider} {averageRating} {productCatalogUrl} />
  </div>

  <div class="container-responsive pb-12 space-y-6">
    {#if data.warnings.length > 0}
      <div class="border border-rust-700/50 bg-rust-600/10 p-5 flex items-start gap-3">
        <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
        <div>
          <p class="font-mono text-xs text-rust-400 uppercase tracking-widest mb-2">PARTE DEL PERFIL NO PUDO REFRESCARSE</p>
          {#each data.warnings as warning}
            <p class="font-mono text-[10px] text-steel-400">{warning}</p>
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

    <div class="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <!-- Ficha estructurada -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// FICHA BASE</p>
            <h2 class="font-display text-3xl text-bone uppercase leading-none">INFORMACIÓN ESTRUCTURADA</h2>
          </div>
          <a href={productCatalogUrl} class="btn-ghost font-mono text-[10px] uppercase tracking-widest shrink-0">VER CATÁLOGO →</a>
        </div>
        <div class="p-5 grid gap-3 sm:grid-cols-2">
          {#each signalCards as card}
            <div class="bg-iron-800/50 border border-steel-600/20 p-4">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">{card.label.toUpperCase()}</p>
              <p class="font-display text-2xl text-rust-600 leading-none mb-1">{card.value}</p>
              <p class="font-mono text-[10px] text-steel-500 leading-relaxed">{card.description}</p>
            </div>
          {/each}
        </div>
        <div class="border-t border-steel-600/25 bg-iron-800/30 px-6 py-5">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// LECTURA COMERCIAL</p>
          <p class="font-mono text-xs text-steel-400 leading-relaxed">
            Esta plantilla no intenta inventar una landing distinta por proveedor. Mantiene una base común y deja que el contenido real cambie con reputación, catálogo, contacto y actividad operativa.
          </p>
        </div>
      </div>

      <ProviderReviewFeed {reviews} />
    </div>

    <!-- Catálogo de productos -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// CATÁLOGO PUBLICADO</p>
          <h2 class="font-display text-3xl text-bone uppercase leading-none">PRODUCTOS VISIBLES</h2>
        </div>
        <a href={productCatalogUrl} class="btn-outline shrink-0">ABRIR TODO EL CATÁLOGO</a>
      </div>

      {#if products.length === 0}
        <div class="p-8 text-center">
          <p class="font-mono text-xs text-steel-600 uppercase tracking-widest">ESTE PROVEEDOR AÚN NO TIENE PRODUCTOS VISIBLES</p>
        </div>
      {:else}
        <div class="p-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {#each products as product}
            <ProductCard {product} />
          {/each}
        </div>
      {/if}
    </div>
  </div>
</div>
