<script lang="ts">
  import type { PageData } from './$types';
  import type { StockItem } from '$lib/api/types';
  import { goto } from '$app/navigation';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';

  export let data: PageData;

  const product = data.product;

  let cantidad = 1;
  let carritoAbiert = false;
  let productoEnCarrito = false;
  let imagenActiva = 0;

  // Calcular precio con impuesto
  $: precioBase = parseFloat(product.price || '0');
  $: impuesto = parseFloat(product.tax_percent || '18') || 18;
  $: precioConImpuesto = precioBase + (precioBase * impuesto / 100);
  $: precioTotal = precioConImpuesto * cantidad;

  // Verificar disponibilidad total
  $: totalStock = product.total_stock || 0;
  $: estaDisponible = totalStock > 0;
  $: esStock = totalStock > 0 ? 'EN STOCK' : 'SIN STOCK';

  // Agrupar stock por almacén
  $: stockItems = product.stock_items || product.stock_por_almacen || [];
  $: providerUrl = product.provider_slug ? `/proveedores/${product.provider_slug}` : null;
  $: stockPorAlmacen = stockItems.reduce((acc: Record<string, StockItem[]>, item: StockItem) => {
    const ciudad = item.warehouse_city || 'Sin ciudad';
    if (!acc[ciudad]) acc[ciudad] = [];
    acc[ciudad].push(item);
    return acc;
  }, {});

  const agregarAlCarrito = async () => {
    if (!auth.getAccessToken()) {
      goto('/login');
      return;
    }
    await cart.addItem(product.id, cantidad);
    productoEnCarrito = true;
    setTimeout(() => {
      productoEnCarrito = false;
    }, 2000);
  };

  const incrementarCantidad = () => {
    if (cantidad < totalStock) cantidad++;
  };

  const decrementarCantidad = () => {
    if (cantidad > 1) cantidad--;
  };
</script>

<svelte:head>
  <title>{product.name} — ECOMPARTS</title>
  <meta name="description" content={product.description || `Detalle del producto ${product.name}`} />
  <meta property="og:title" content={product.name} />
  <meta property="og:description" content={product.description || `Detalle del producto ${product.name}`} />
  {#if product.image_url}
    <meta property="og:image" content={product.image_url} />
  {/if}
</svelte:head>

<!-- ── Breadcrumb ── -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-3">
    <div class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-steel-500">
      <a href="/productos" class="hover:text-rust-500 transition-colors">CATÁLOGO</a>
      <span class="text-steel-700">/</span>
      {#if product.category_name}
        <span class="text-steel-500">{product.category_name}</span>
        <span class="text-steel-700">/</span>
      {/if}
      <span class="text-bone truncate max-w-xs">{product.name}</span>
    </div>
  </div>
</div>

<!-- ── Contenido Principal ── -->
<div class="container-responsive py-10">
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">

    <!-- ══════════════════════════════════
         COLUMNA IZQUIERDA — GALERÍA
    ═══════════════════════════════════ -->
    <div class="flex flex-col gap-4">

      <!-- Imagen principal -->
      <div class="relative bg-iron-900 border border-steel-600/30 overflow-hidden"
           style="aspect-ratio: 4/3; clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
        {#if product.image_url}
          <img
            src={product.image_url}
            alt={product.name}
            class="w-full h-full object-contain p-6"
          />
        {:else}
          <div class="w-full h-full flex flex-col items-center justify-center gap-4 text-steel-700">
            <svg class="w-20 h-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="0.75"
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p class="font-mono text-xs uppercase tracking-widest">SIN IMAGEN</p>
          </div>
        {/if}

        <!-- Corner bracket decoration -->
        <div class="absolute top-3 left-3 w-4 h-4 border-t border-l border-rust-600/50"></div>
        <div class="absolute bottom-3 right-3 w-4 h-4 border-b border-r border-rust-600/50"></div>
      </div>

      <!-- Stock por almacén -->
      {#if stockItems.length > 0}
        <div class="bg-iron-900 border border-steel-600/25 p-5"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">// DISPONIBILIDAD POR ALMACÉN</p>
          <div class="space-y-3">
            {#each Object.entries(stockPorAlmacen) as [ciudad, items]}
              <div class="border-l-2 border-steel-600/50 pl-4">
                <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">{ciudad}</p>
                <div class="space-y-1.5">
                  {#each items as item}
                    <div class="flex justify-between items-center">
                      <span class="font-mono text-xs text-steel-400">{item.warehouse_name}</span>
                      <span class="font-mono text-xs px-3 py-0.5 border {item.is_out_of_stock
                        ? 'border-rust-700/50 text-rust-500 bg-rust-600/10'
                        : 'border-green-700/50 text-green-400 bg-green-600/10'}">
                        {item.quantity} {item.quantity === 1 ? 'UNIDAD' : 'UNIDADES'}
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

    <!-- ══════════════════════════════════
         COLUMNA DERECHA — INFO TÉCNICA
    ═══════════════════════════════════ -->
    <div class="flex flex-col gap-5">

      <!-- Header del producto -->
      <div>
        <!-- Categoría + stock badge -->
        <div class="flex items-center gap-3 mb-3 flex-wrap">
          {#if product.category_name}
            <span class="font-mono text-[10px] uppercase tracking-widest text-steel-500 border border-steel-600/40 px-3 py-1">
              {product.category_name}
            </span>
          {/if}
          <span class="font-mono text-[10px] uppercase tracking-widest px-3 py-1 border {estaDisponible
            ? 'border-green-700/60 text-green-400 bg-green-600/10'
            : 'border-rust-700/60 text-rust-500 bg-rust-600/10'}">
            {#if estaDisponible}
              <span class="inline-block w-1.5 h-1.5 bg-green-400 mr-1.5 align-middle"></span>
            {/if}
            {esStock}
          </span>
        </div>

        <!-- Nombre del producto -->
        <h1 class="font-display text-4xl md:text-5xl text-bone uppercase leading-none mb-3">
          {product.name}
        </h1>

        <!-- Referencia -->
        <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">
          REF: <span class="text-bone">{product.reference}</span>
        </p>
      </div>

      <!-- FICHA MECÁNICA — specs grid -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// FICHA TÉCNICA</p>
        </div>
        <div class="grid grid-cols-2 divide-x divide-steel-600/20">
          <div class="px-5 py-4 border-b border-steel-600/20">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">SKU / REFERENCIA</p>
            <p class="font-mono text-sm text-bone">{product.reference}</p>
          </div>
          {#if product.manufacturer_code}
            <div class="px-5 py-4 border-b border-steel-600/20">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CÓDIGO OEM</p>
              <p class="font-mono text-sm text-bone">{product.manufacturer_code}</p>
            </div>
          {:else}
            <div class="px-5 py-4 border-b border-steel-600/20">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CÓDIGO OEM</p>
              <p class="font-mono text-sm text-steel-600">—</p>
            </div>
          {/if}
          <div class="px-5 py-4 border-b border-steel-600/20">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">PROVEEDOR</p>
            {#if providerUrl}
              <a href={providerUrl} class="font-mono text-sm text-rust-500 hover:text-rust-400 transition-colors">
                {product.provider_name}
              </a>
            {:else}
              <p class="font-mono text-sm text-bone">{product.provider_name || '—'}</p>
            {/if}
          </div>
          <div class="px-5 py-4 border-b border-steel-600/20">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">STOCK TOTAL</p>
            <p class="font-mono text-sm {estaDisponible ? 'text-green-400' : 'text-rust-500'}">
              {totalStock} {totalStock === 1 ? 'UNIDAD' : 'UNIDADES'}
            </p>
          </div>
          <div class="px-5 py-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">IMPUESTO (IGV)</p>
            <p class="font-mono text-sm text-bone">{impuesto}%</p>
          </div>
          {#if product.es_universal}
            <div class="px-5 py-4">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COMPATIBILIDAD</p>
              <span class="font-mono text-[10px] text-bone border border-steel-600/40 px-2 py-0.5 uppercase">
                UNIVERSAL
              </span>
            </div>
          {:else}
            <div class="px-5 py-4">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COMPATIBILIDAD</p>
              <p class="font-mono text-sm text-steel-500">POR VEHÍCULO</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- PRECIO -->
      <div class="bg-iron-900 border border-steel-600/25 p-5"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">PRECIO UNITARIO (INC. IGV)</p>
        <div class="flex items-baseline gap-3">
          <span class="font-display text-5xl text-rust-600 leading-none">
            S/. {precioConImpuesto.toFixed(2)}
          </span>
        </div>
        {#if precioBase !== precioConImpuesto}
          <p class="font-mono text-[10px] text-steel-600 mt-1">
            PRECIO BASE: S/. {precioBase.toFixed(2)} + {impuesto}% IGV
          </p>
        {/if}
        {#if cantidad > 1}
          <div class="mt-3 pt-3 border-t border-steel-600/20">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">TOTAL ({cantidad} UNIDADES)</p>
            <span class="font-display text-3xl text-bone leading-none">S/. {precioTotal.toFixed(2)}</span>
          </div>
        {/if}
      </div>

      <!-- CANTIDAD + CARRITO -->
      <div class="space-y-3">
        <!-- Selector de cantidad -->
        <div class="flex items-center gap-0">
          <span class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mr-4">CANTIDAD:</span>
          <button
            on:click={decrementarCantidad}
            disabled={cantidad <= 1}
            class="bg-iron-800 border border-steel-600/50 text-bone font-mono text-lg w-10 h-10 flex items-center justify-center
                   hover:border-rust-600 hover:text-rust-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >−</button>
          <div class="w-14 h-10 bg-iron-900 border-y border-steel-600/50 flex items-center justify-center">
            <span class="font-mono text-base text-bone">{cantidad}</span>
          </div>
          <button
            on:click={incrementarCantidad}
            disabled={cantidad >= totalStock}
            class="bg-iron-800 border border-steel-600/50 text-bone font-mono text-lg w-10 h-10 flex items-center justify-center
                   hover:border-rust-600 hover:text-rust-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >+</button>
        </div>

        <!-- Botón principal -->
        <button
          on:click={agregarAlCarrito}
          disabled={!estaDisponible}
          class="w-full font-display text-xl uppercase tracking-widest py-4 px-6 transition-all duration-150
                 {estaDisponible
                   ? 'bg-rust-600 hover:bg-rust-700 text-bone border border-rust-600 hover:border-rust-500'
                   : 'bg-iron-800 text-steel-600 border border-steel-600/30 cursor-not-allowed'}"
          style={estaDisponible ? 'clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' : ''}
        >
          {#if !estaDisponible}
            SIN STOCK — NO DISPONIBLE
          {:else}
            AGREGAR AL CARRITO →
          {/if}
        </button>

        {#if providerUrl}
          <a href={providerUrl}
             class="block w-full text-center font-mono text-xs uppercase tracking-industrial text-steel-400
                    border border-steel-600/40 py-3 hover:border-rust-600/60 hover:text-rust-500 transition-colors">
            VER PERFIL DEL PROVEEDOR
          </a>
        {/if}
      </div>
    </div>
  </div>

  <!-- ── Descripción ── -->
  {#if product.description}
    <div class="mt-12 bg-iron-900 border border-steel-600/25 p-8"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">// DESCRIPCIÓN DEL PRODUCTO</p>
      <p class="font-mono text-sm text-steel-400 leading-relaxed whitespace-pre-wrap">{product.description}</p>
    </div>
  {/if}

  <!-- ── Info técnica adicional ── -->
  <div class="mt-6 bg-iron-900 border border-steel-600/25"
       style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
    <div class="border-b border-steel-600/25 px-8 py-4">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// INFORMACIÓN TÉCNICA</p>
    </div>
    <div class="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
      <div class="space-y-5">
        <div>
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">REFERENCIA INTERNA</p>
          <p class="font-mono text-sm text-bone">{product.reference}</p>
        </div>
        {#if product.manufacturer_code}
          <div>
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CÓDIGO DE FABRICANTE</p>
            <p class="font-mono text-sm text-bone">{product.manufacturer_code}</p>
          </div>
        {/if}
        {#if product.category_name}
          <div>
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CATEGORÍA</p>
            <p class="font-mono text-sm text-bone">{product.category_name}</p>
          </div>
        {/if}
      </div>
      <div class="space-y-5">
        <div>
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">STOCK TOTAL DISPONIBLE</p>
          <p class="font-mono text-sm {estaDisponible ? 'text-green-400' : 'text-rust-500'}">
            {totalStock} {totalStock === 1 ? 'unidad' : 'unidades'}
          </p>
        </div>
        {#if product.es_universal}
          <div>
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">COMPATIBILIDAD</p>
            <div class="flex items-center gap-2 border border-steel-600/30 p-3 w-fit">
              <svg class="w-4 h-4 text-bone" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="font-mono text-xs text-bone uppercase tracking-widest">COMPATIBLE CON TODOS LOS VEHÍCULOS</span>
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<!-- ── Toast de confirmación ── -->
{#if productoEnCarrito}
  <div class="fixed top-20 right-4 z-50 bg-iron-900 border border-green-700/60 text-green-400 px-6 py-3
              font-mono text-xs uppercase tracking-widest flex items-center gap-3 shadow-2xl shadow-black/50"
       style="clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)">
    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd"
        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
        clip-rule="evenodd" />
    </svg>
    AGREGADO AL CARRITO
  </div>
{/if}
