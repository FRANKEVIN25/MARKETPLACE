<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';

  export let data: PageData;

  let categoriaSeleccionada = '';

  $: productosFiltrados = categoriaSeleccionada 
    ? data.products.filter(p => {
        const categoria = p.categoria || p.category || '';
        return categoria.toLowerCase() === categoriaSeleccionada.toLowerCase();
      })
    : data.products;

  $: categorias = Array.from(new Set(
    data.products.map(p => p.categoria || p.category || 'Sin categoría')
  )).filter(cat => cat !== 'Sin categoría');
</script>

<svelte:head>
  <title>Categorías - ECOMPARTS</title>
  <meta name="description" content="Explora productos por categoría" />
</svelte:head>

<div class="bg-gray-50 min-h-screen">
  <!-- Header -->
  <div class="bg-white border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 class="text-4xl font-bold text-gray-900 mb-2">Categorías de Productos</h1>
      <p class="text-gray-600">Explora nuestras categorías de autopartes</p>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    {#if data.error}
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 text-center">
        <p class="font-medium">Error al cargar categorías</p>
        <p class="text-sm mt-1">{data.error}</p>
      </div>
    {:else}
      <!-- Grid de categorías -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
        <button
          on:click={() => (categoriaSeleccionada = '')}
          class="p-6 rounded-lg border-2 transition-all {categoriaSeleccionada === ''
            ? 'border-blue-600 bg-blue-50'
            : 'border-gray-200 bg-white hover:border-blue-400'}"
        >
          <div class="text-4xl mb-3">🔧</div>
          <h3 class="text-lg font-bold text-gray-900">Todas las categorías</h3>
          <p class="text-gray-600 text-sm mt-1">Ver todos los {data.products.length} productos</p>
        </button>

        {#each categorias as categoria}
          <button
            on:click={() => (categoriaSeleccionada = categoria)}
            class="p-6 rounded-lg border-2 transition-all {categoriaSeleccionada === categoria
              ? 'border-blue-600 bg-blue-50'
              : 'border-gray-200 bg-white hover:border-blue-400'}"
          >
            <div class="text-4xl mb-3">
              {categoria.toLowerCase() === 'frenos' && '🛑'}
              {categoria.toLowerCase() === 'bujías' && '⚡'}
              {categoria.toLowerCase() === 'amortiguadores' && '🚗'}
              {categoria.toLowerCase() === 'pastillas' && '🔴'}
              {!['frenos', 'bujías', 'amortiguadores', 'pastillas'].includes(categoria.toLowerCase()) && '📦'}
            </div>
            <h3 class="text-lg font-bold text-gray-900 capitalize">{categoria}</h3>
            <p class="text-gray-600 text-sm mt-1">
              {data.products.filter(p => (p.categoria || p.category || '') === categoria).length} productos
            </p>
          </button>
        {/each}
      </div>

      <!-- Productos filtrados -->
      {#if productosFiltrados.length === 0}
        <div class="bg-white rounded-lg shadow p-12 text-center">
          <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 21l-4.35-4.35m0 0A7.5 7.5 0 103.305 3.305a7.5 7.5 0 0110.345 10.345z" />
          </svg>
          <p class="text-gray-500 mt-4 text-lg">No hay productos en esta categoría</p>
        </div>
      {:else}
        <div>
          <p class="text-gray-600 mb-6 font-medium">
            Mostrando {productosFiltrados.length} de {data.products.length} productos
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {#each productosFiltrados as product (product.id)}
              <ProductCard {product} />
            {/each}
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>