<script lang="ts">
  import type { PageData } from './$types';
  import type { StockItem } from '$lib/api/types';
  import { cart } from '$lib/store/cart';

  export let data: PageData;

  const product = data.product;

  let cantidad = 1;
  let carritoAbiert = false;
  let productoEnCarrito = false;

  // Calcular precio con impuesto
  $: precioBase = parseFloat(product.price || '0');
  $: impuesto = parseFloat(product.tax_percent || '18') || 18;
  $: precioConImpuesto = precioBase + (precioBase * impuesto / 100);
  $: precioTotal = precioConImpuesto * cantidad;

  // Verificar disponibilidad total
  $: totalStock = product.total_stock || 0;
  $: estaDisponible = totalStock > 0;
  $: esStock = totalStock > 0 ? 'En Stock' : 'Sin Stock';
  $: clasesStock = totalStock > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';

  // Agrupar stock por almacén
  $: stockItems = product.stock_items || product.stock_por_almacen || [];
  $: providerUrl = product.provider_slug ? `/proveedores/${product.provider_slug}` : null;
  $: stockPorAlmacen = stockItems.reduce((acc: Record<string, StockItem[]>, item: StockItem) => {
    const ciudad = item.warehouse_city || 'Sin ciudad';
    if (!acc[ciudad]) acc[ciudad] = [];
    acc[ciudad].push(item);
    return acc;
  }, {});

  const agregarAlCarrito = () => {
    cart.addItem(product, cantidad);
    productoEnCarrito = true;
    setTimeout(() => {
      productoEnCarrito = false;
    }, 2000);
  };

  const incrementarCantidad = () => {
    if (cantidad < totalStock) {
      cantidad++;
    }
  };

  const decrementarCantidad = () => {
    if (cantidad > 1) {
      cantidad--;
    }
  };
</script>

<svelte:head>
  <title>{product.name} - ECOMPARTS</title>
  <meta name="description" content={product.description || `Detalle del producto ${product.name}`} />
  <meta property="og:title" content={product.name} />
  <meta property="og:description" content={product.description || `Detalle del producto ${product.name}`} />
  {#if product.image_url}
    <meta property="og:image" content={product.image_url} />
  {/if}
</svelte:head>

<div class="bg-gray-50 min-h-screen">
  <!-- Breadcrumb -->
  <div class="bg-white border-b border-gray-200">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
      <div class="flex items-center space-x-2 text-sm">
        <a href="/productos" class="text-blue-600 hover:text-blue-800">Productos</a>
        <span class="text-gray-400">/</span>
        {#if product.category_name}
          <span class="text-gray-700">
            {product.category_name}
          </span>
          <span class="text-gray-400">/</span>
        {/if}
        <span class="text-gray-700 font-medium">{product.name}</span>
      </div>
    </div>
  </div>

  <!-- Contenido Principal -->
  <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-12">
      <!-- Imagen del Producto -->
      <div class="flex flex-col gap-4">
        <div class="bg-white rounded-lg shadow-lg overflow-hidden flex items-center justify-center h-96">
          {#if product.image_url}
            <img
              src={product.image_url}
              alt={product.name}
              class="w-full h-full object-cover"
            />
          {:else}
            <div class="flex flex-col items-center justify-center text-gray-400">
              <svg class="w-24 h-24 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <p>Sin imagen disponible</p>
            </div>
          {/if}
        </div>

        <!-- Información de Stock por Almacén -->
         
        {#if stockItems.length > 0}
          <div class="bg-white rounded-lg shadow p-6">
            <h3 class="text-lg font-semibold text-gray-900 mb-4">Disponibilidad por Almacén</h3>
            <div class="space-y-3">
              {#each Object.entries(stockPorAlmacen) as [ciudad, items]}
                <div class="border-l-4 border-blue-500 pl-4">
                  <p class="font-medium text-gray-900">{ciudad}</p>
                  <div class="mt-2 space-y-1">
                    {#each items as item}
                      <div class="flex justify-between items-center text-sm">
                        <span class="text-gray-600">{item.warehouse_name}</span>
                        <span
                          class="px-3 py-1 rounded-full text-sm font-medium"
                          class:bg-green-100={!item.is_out_of_stock}
                          class:text-green-800={!item.is_out_of_stock}
                          class:bg-red-100={item.is_out_of_stock}
                          class:text-red-800={item.is_out_of_stock}
                        >
                          {item.quantity} {item.quantity === 1 ? 'unidad' : 'unidades'}
                        </span>
                      </div>
                    {/each}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
        
      </div>

      <!-- Información del Producto -->
      <div class="flex flex-col gap-4">
        <!-- Header -->
        <div>
          <div class="flex items-start justify-between mb-4">
            <div>
              <h1 class="text-4xl font-bold text-gray-900 mb-2">{product.name}</h1>
              <p class="text-gray-600 text-lg">Referencia: {product.reference}</p>
            </div>
          <!-- Categoría -->
          {#if product.category_name}
            <div class="flex gap-2 items-center mb-4 text-sm">
              <span class="text-gray-600">Categoría:</span>
              <span class="bg-blue-100 text-blue-800 px-4 py-2 rounded-full">
                {product.category_name}
              </span>
            </div>
          {/if}
          </div>
          <!-- Proveedor -->
          <div class="flex gap-2 items-center mb-2">
            <span class="text-gray-600">Proveedor:</span>
            {#if providerUrl}
              <a href={providerUrl} class="text-gray-900 font-medium hover:text-blue-700 transition-colors">
                {product.provider_name}
              </a>
            {:else}
              <p class="text-gray-900 font-medium">{product.provider_name}</p>
            {/if}
          </div>
          {#if providerUrl}
            <div class="mb-2">
              <a href={providerUrl} class="inline-flex items-center rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-200 transition-colors">
                Ver perfil del proveedor
              </a>
            </div>
          {/if}
        </div>

        <!-- Precios -->
        <div class="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
          <div class="grid grid-cols-3 gap-4">
            <div>
              <p class="text-gray-600 text-sm">Precio</p>
              <p class="text-2xl font-bold text-green-600">
                S/. {precioConImpuesto.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        <!-- Estado de Stock -->
        <div class={`rounded-lg p-4 ${clasesStock}`}>
          <div class="flex items-center gap-2">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
            <div>
              <p class="font-semibold">{esStock}</p>
              <p class="text-sm">{totalStock} {totalStock === 1 ? 'unidad' : 'unidades'} disponibles</p>
            </div>
          </div>
        </div>
        <!-- Botón Agregar al Carrito -->
        <button
          on:click={agregarAlCarrito}
          disabled={!estaDisponible}
          class="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded-lg transition text-lg"
        >
          {#if !estaDisponible}
            No Disponible
          {:else}
            Agregar al Carrito
          {/if}
        </button>

        <!-- Confirmación añadido -->
        {#if productoEnCarrito}
          <div
            class="fixed top-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 animate-pulse"
          >
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fill-rule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clip-rule="evenodd"
              />
            </svg>
            ✓ Agregado al carrito
          </div>
        {/if}
      </div>
    </div>

    <!-- Descripción del Producto -->
    {#if product.description}
      <div class="mt-12 bg-white rounded-lg shadow p-8">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">Descripción</h2>
        <p class="text-gray-700 text-lg leading-relaxed whitespace-pre-wrap">
          {product.description}
        </p>
      </div>
    {/if}

    <!-- Información Técnica -->
    <div class="mt-12 bg-white rounded-lg shadow p-8">
      <h2 class="text-2xl font-bold text-gray-900 mb-6">Información Técnica</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        <!-- Columna 1 -->
        <div class="space-y-4">
          <div>
            <p class="text-gray-600 text-sm">Referencia</p>
            <p class="text-gray-900 font-medium font-mono">{product.reference}</p>
          </div>
          {#if product.manufacturer_code}
            <div>
              <p class="text-gray-600 text-sm">Código Fabricante</p>
              <p class="text-gray-900 font-medium font-mono">{product.manufacturer_code}</p>
            </div>
          {/if}
        </div>

        <!-- Columna 2 -->
        <div class="space-y-4">
          <div>
            <p class="text-gray-600 text-sm">Stock Total</p>
            <p class="text-gray-900 font-medium">
              {totalStock} {totalStock === 1 ? 'unidad' : 'unidades'}
            </p>
          </div>
          {#if product.es_universal}
            <div class="flex items-center gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <svg class="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clip-rule="evenodd"
                />
              </svg>
              <span class="text-sm font-medium text-amber-800">Compatible con todos los vehículos</span>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  :global(html) {
    scroll-behavior: smooth;
  }
</style>
