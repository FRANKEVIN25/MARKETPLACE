<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';

  export let data: PageData;

  let filtroCategoria = 'todos';
  let busqueda = '';

  $: productosFiltrados = data.products.filter(p => {
    const nombre = p.nombre || p.name || '';
    const categoria = p.categoria || p.category || '';
    const coincidenBusqueda = nombre.toLowerCase().includes(busqueda.toLowerCase());
    const coincidenCategoria = filtroCategoria === 'todos' || categoria === filtroCategoria;
    return coincidenBusqueda && coincidenCategoria;
  });

  const categorias = ['todos', 'frenos', 'bujías', 'amortiguadores', 'pastillas'];
</script>

<svelte:head>
  <title>Productos - ECOMPARTS</title>
  <meta name="description" content="Catálogo completo de autopartes" />
</svelte:head>

<div class="bg-gray-50 min-h-screen">
  <!-- Header -->
  <div class="bg-white border-b border-gray-200 sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">Catálogo de Productos</h1>
      <p class="text-gray-600">Explora nuestro completo catálogo de autopartes de calidad</p>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Filtros -->
    <div class="bg-white rounded-lg shadow p-6 mb-8">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Búsqueda -->
        <div>
          <label for="busqueda" class="block text-sm font-medium text-gray-700 mb-2">
            Buscar productos
          </label>
          <input
            id="busqueda"
            type="text"
            placeholder="Ej: Disco de Freno, Bujías..."
            bind:value={busqueda}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>

        <!-- Filtro de categoría -->
        <div>
          <label for="categoria" class="block text-sm font-medium text-gray-700 mb-2">
            Categoría
          </label>
          <select
            id="categoria"
            bind:value={filtroCategoria}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          >
            {#each categorias as cat}
              <option value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    <!-- Resultados -->
    {#if data.error}
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 text-center">
        <p class="font-medium">Error al cargar productos</p>
        <p class="text-sm mt-1">{data.error}</p>
      </div>
    {:else if productosFiltrados.length === 0}
      <div class="bg-white rounded-lg shadow p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 21l-4.35-4.35m0 0A7.5 7.5 0 103.305 3.305a7.5 7.5 0 0110.345 10.345z" />
        </svg>
        <p class="text-gray-500 mt-4 text-lg">No se encontraron productos</p>
        <p class="text-gray-400 text-sm mt-1">Intenta con otros términos de búsqueda</p>
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
  </div>
</div>