<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';
  export let data: PageData;
</script>

<svelte:head>
  <title>ECOMPARTS - Marketplace de Autopartes en Perú</title>
  <meta name="description" content="Encuentra repuestos de calidad de múltiples proveedores" />
</svelte:head>

<div class="bg-gradient-to-r from-blue-600 to-blue-800 text-white py-4">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex flex-col md:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span class="text-2xl">💼</span>
        <div>
          <p class="font-bold">¿Vendes autopartes?</p>
          <p class="text-sm text-blue-100">Únete a ECOMPARTS y llega a miles de clientes</p>
        </div>
      </div>
      <div class="flex gap-2">
        <a
          href="/vendedor"
          class="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-sm font-medium"
        >
          Ver planes
        </a>
        <a
          href="/vendedor/registro"
          class="px-4 py-2 bg-white text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors text-sm"
        >
          Registrarme
        </a>
      </div>
    </div>
  </div>
</div>

<section class="bg-gradient-to-r from-blue-600 via-blue-700 to-blue-900 text-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-32">
    <div class="max-w-3xl">
      <h1 class="text-5xl md:text-6xl font-bold mb-6">
        Encuentra los mejores <span class="text-blue-200">repuestos</span> para tu vehículo
      </h1>
      <p class="text-xl md:text-2xl text-blue-100 mb-8">
        Compara precios de múltiples proveedores en un solo lugar
      </p>
      <a href="/productos" class="inline-block px-8 py-3 bg-white text-blue-600 font-bold rounded-lg hover:bg-blue-50 transition-colors">
        Ver todos los productos
      </a>
    </div>
  </div>
</section>

<section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
  <div class="mb-12">
    <h2 class="text-4xl font-bold text-gray-900 mb-3">Productos Destacados</h2>
    <p class="text-gray-600 text-lg">Últimos productos agregados al marketplace</p>
  </div>
  
  {#if data.error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
      <p class="font-semibold">Error al cargar productos</p>
      <p class="text-sm mt-1">{data.error}</p>
    </div>
  {:else if !data.products || data.products.length === 0}
    <div class="bg-gray-100 rounded-lg p-12 text-center">
      <p class="text-gray-600 text-lg">No hay productos disponibles</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-10">
      {#each data.products as product (product.id)}
        <ProductCard {product} />
      {/each}
    </div>
    <div class="text-center">
      <a href="/productos" class="inline-block px-8 py-3 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors">
        Ver todos los {data.totalCount} productos →
      </a>
    </div>
  {/if}
</section>