<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';
  import { onMount } from 'svelte';

  export let data: PageData;

  // Animated stats
  let statsVisible = false;
  let searchQuery = '';

  onMount(() => {
    // Trigger stat counters on load
    setTimeout(() => { statsVisible = true; }, 200);
  });

  function handleSearch(e: Event) {
    e.preventDefault();
    if (searchQuery.trim()) {
      window.location.href = `/productos?q=${encodeURIComponent(searchQuery.trim())}`;
    } else {
      window.location.href = '/productos';
    }
  }
</script>

<svelte:head>
  <title>ECOMPARTS — Marketplace Industrial de Autopartes · Perú</title>
  <meta name="description" content="Marketplace B2B de autopartes en Perú. Repuestos de calidad, precio justo, entrega rápida." />
</svelte:head>

<!-- ══════════════════════════════════════════════
     VENDOR RECRUITMENT STRIP
═══════════════════════════════════════════════ -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-3">
    <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
      <div class="flex items-center gap-4">
        <div class="w-px h-8 bg-rust-600 hidden sm:block"></div>
        <div>
          <p class="font-mono text-xs text-bone uppercase tracking-industrial">¿Vendes autopartes?</p>
          <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">Únete a ECOMPARTS · Llega a miles de clientes B2B</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <a href="/vendedor"
           class="font-mono text-[11px] uppercase tracking-industrial text-steel-300 border border-steel-600/60 px-4 py-1.5 hover:border-steel-400 hover:text-bone transition-colors">
          VER PLANES
        </a>
        <a href="/vendedor/registro"
           class="font-mono text-[11px] uppercase tracking-industrial text-bone bg-rust-600 px-4 py-1.5 hover:bg-rust-700 transition-colors"
           style="clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)">
          REGISTRARME →
        </a>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════
     HERO SECTION — INDUSTRIAL BRUTAL
═══════════════════════════════════════════════ -->
<section class="hero-industrial relative overflow-hidden">

  <!-- Decorative diagonal lines (left) -->
  <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-rust-600/40 to-transparent pointer-events-none"></div>

  <!-- Large background text (watermark) -->
  <div class="absolute inset-0 flex items-center justify-end pr-8 pointer-events-none overflow-hidden select-none" aria-hidden="true">
    <span class="font-display text-[20vw] text-steel-600/5 leading-none uppercase tracking-tighter whitespace-nowrap">
      AUTOPARTES
    </span>
  </div>

  <div class="container-responsive py-20 md:py-32 relative z-10">

    <!-- ── B2B Badge ── -->
    <div class="inline-flex items-center gap-3 border border-rust-600/60 bg-rust-600/10 px-4 py-2 mb-8">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rust-500 opacity-75"></span>
        <span class="relative inline-flex h-2 w-2 rounded-full bg-rust-600"></span>
      </span>
      <span class="font-mono text-[11px] text-rust-500 uppercase tracking-widest">B2B · PERÚ · AUTOPARTES · INDUSTRIA</span>
    </div>

    <!-- ── Main headline ── -->
    <h1 class="font-display uppercase leading-none mb-8 max-w-5xl">
      <span class="block text-[clamp(52px,9vw,110px)] text-bone">EL REPUESTO</span>
      <span class="block text-[clamp(52px,9vw,110px)] text-rust-600">CORRECTO.</span>
      <span class="block text-[clamp(52px,9vw,110px)] text-bone">PRECIO JUSTO.</span>
      <span class="block text-[clamp(52px,9vw,110px)] text-steel-400">HOY.</span>
    </h1>

    <!-- ── Sub-copy ── -->
    <p class="font-mono text-sm text-steel-400 uppercase tracking-industrial mb-12 max-w-xl">
      Compara precios · Múltiples proveedores · Entrega en todo el Perú
    </p>

    <!-- ── Stats row ── -->
    <div class="flex flex-wrap gap-8 mb-12 {statsVisible ? 'counter-animate' : 'opacity-0'}">
      <div class="stat-block">
        <span class="font-display text-4xl md:text-5xl text-rust-600 leading-none">+5,000</span>
        <span class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">PRODUCTOS</span>
      </div>
      <div class="stat-block">
        <span class="font-display text-4xl md:text-5xl text-rust-600 leading-none">+120</span>
        <span class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">PROVEEDORES</span>
      </div>
      <div class="stat-block">
        <span class="font-display text-4xl md:text-5xl text-rust-600 leading-none">24H</span>
        <span class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">ENTREGA LIMA</span>
      </div>
      <div class="stat-block">
        <span class="font-display text-4xl md:text-5xl text-rust-600 leading-none">100%</span>
        <span class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">GARANTÍA</span>
      </div>
    </div>

    <!-- ── Search bar ── -->
    <form on:submit={handleSearch} class="flex max-w-2xl mb-10">
      <div class="relative flex-1">
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Busca por nombre, SKU, marca o modelo..."
          class="w-full bg-iron-800 border border-steel-600/60 border-r-0 text-bone font-mono text-sm
                 px-5 py-4 placeholder-steel-600 outline-none focus:border-rust-600 transition-colors"
        />
      </div>
      <button
        type="submit"
        class="bg-rust-600 hover:bg-rust-700 text-bone font-mono text-xs uppercase tracking-industrial
               px-8 py-4 transition-colors border border-rust-600 hover:border-rust-500 whitespace-nowrap"
        style="clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)"
      >
        BUSCAR
      </button>
    </form>

    <!-- ── Quick links ── -->
    <div class="flex flex-wrap items-center gap-2">
      <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">Búsquedas populares:</span>
      {#each ['FRENOS', 'FILTROS', 'BATERÍAS', 'AMORTIGUADORES', 'EMBRAGUE'] as tag}
        <a href="/productos?q={tag.toLowerCase()}"
           class="font-mono text-[10px] uppercase tracking-widest text-steel-400 border border-steel-600/40 px-3 py-1
                  hover:border-rust-600/60 hover:text-rust-500 transition-colors">
          {tag}
        </a>
      {/each}
    </div>
  </div>

  <!-- Bottom edge separator -->
  <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-rust-600/50 to-transparent"></div>
</section>

<!-- ══════════════════════════════════════════════
     TICKER TAPE — Industrial marquee
═══════════════════════════════════════════════ -->
<div class="ticker-wrap">
  <div class="ticker-content">
    {#each Array(2) as _}
      <span class="font-mono text-[10px] uppercase tracking-widest text-steel-600 mx-8">
        FRENOS &nbsp;·&nbsp; FILTROS &nbsp;·&nbsp; AMORTIGUADORES &nbsp;·&nbsp; BATERÍAS &nbsp;·&nbsp;
        EMBRAGUE &nbsp;·&nbsp; DIRECCIÓN &nbsp;·&nbsp; MOTOR &nbsp;·&nbsp; TRANSMISIÓN &nbsp;·&nbsp;
        SUSPENSIÓN &nbsp;·&nbsp; ENCENDIDO &nbsp;·&nbsp; ESCAPE &nbsp;·&nbsp; REFRIGERACIÓN &nbsp;·&nbsp;
        CARROCERÍA &nbsp;·&nbsp; ELÉCTRICO &nbsp;·&nbsp; ACCESORIOS &nbsp;·&nbsp;
      </span>
    {/each}
  </div>
</div>

<!-- ══════════════════════════════════════════════
     FEATURED PRODUCTS SECTION
═══════════════════════════════════════════════ -->
<section class="container-responsive py-16">

  <!-- Section header -->
  <div class="flex items-end justify-between mb-10 border-b border-steel-600/25 pb-6">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// CATÁLOGO</p>
      <h2 class="font-display text-5xl md:text-6xl text-bone uppercase leading-none">
        PRODUCTOS<br/>DESTACADOS
      </h2>
    </div>
    <div class="hidden sm:block text-right">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">
        {data.totalCount ? `${data.totalCount} PRODUCTOS DISPONIBLES` : 'CARGANDO INVENTARIO...'}
      </p>
    </div>
  </div>

  {#if data.error}
    <!-- Error state -->
    <div class="border border-rust-700/50 bg-iron-900 p-8 relative"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="flex items-center gap-3 mb-3">
        <span class="w-2 h-2 bg-rust-600"></span>
        <p class="font-mono text-xs text-rust-500 uppercase tracking-widest">ERROR AL CARGAR PRODUCTOS</p>
      </div>
      <p class="font-mono text-sm text-steel-400">{data.error}</p>
      <a href="/productos" class="inline-block mt-4 font-mono text-xs uppercase tracking-industrial text-bone border border-steel-600 px-4 py-2 hover:border-rust-600 hover:text-rust-500 transition-colors">
        INTENTAR NUEVAMENTE →
      </a>
    </div>

  {:else if !data.products || data.products.length === 0}
    <!-- Empty state -->
    <div class="border border-steel-600/30 bg-iron-900 p-16 text-center relative"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <svg class="w-16 h-16 mx-auto text-steel-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
          d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
      </svg>
      <p class="font-display text-3xl text-steel-600 uppercase mb-2">INVENTARIO VACÍO</p>
      <p class="font-mono text-xs text-steel-600 uppercase tracking-widest">NO HAY PRODUCTOS DISPONIBLES EN ESTE MOMENTO</p>
    </div>

  {:else}
    <!-- Product grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-10">
      {#each data.products as product (product.id)}
        <ProductCard {product} />
      {/each}
    </div>

    <!-- View all CTA -->
    <div class="flex justify-center pt-4 border-t border-steel-600/20">
      <a
        href="/productos"
        class="inline-flex items-center gap-3 font-mono text-xs uppercase tracking-industrial text-bone
               border border-steel-600/60 px-10 py-4 hover:border-rust-600 hover:text-rust-500
               transition-all duration-200 group"
      >
        <span>VER TODOS LOS {data.totalCount} PRODUCTOS</span>
        <span class="group-hover:translate-x-1 transition-transform">→</span>
      </a>
    </div>
  {/if}
</section>

<!-- ══════════════════════════════════════════════
     WHY ECOMPARTS — Industrial Feature Strip
═══════════════════════════════════════════════ -->
<section class="bg-iron-900 border-t border-b border-steel-600/25 py-16">
  <div class="container-responsive">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-8 text-center">// POR QUÉ ECOMPARTS</p>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-0">

      {#each [
        { num: '01', title: 'PRECIO JUSTO', desc: 'Compara precios de múltiples proveedores verificados en un solo lugar.' },
        { num: '02', title: 'STOCK REAL', desc: 'Inventario actualizado en tiempo real. Sin sorpresas al momento del pedido.' },
        { num: '03', title: 'B2B ENFOCADO', desc: 'Plataforma diseñada para talleres, flotas y distribuidores de autopartes.' },
        { num: '04', title: 'ENTREGA RÁPIDA', desc: 'Red de proveedores en Lima y provincias. Despacho en 24-48 horas.' },
      ] as feature, i}
        <div class="border-r border-steel-600/20 last:border-r-0 px-8 py-6 first:pl-0 last:pr-0
                    {i === 0 ? 'pl-0' : ''} {i === 3 ? 'pr-0' : ''}">
          <span class="font-display text-6xl text-rust-600/20 leading-none block mb-3">{feature.num}</span>
          <h3 class="font-display text-2xl text-bone uppercase mb-2">{feature.title}</h3>
          <p class="font-mono text-xs text-steel-500 leading-relaxed">{feature.desc}</p>
        </div>
      {/each}

    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     VENDOR CTA SECTION
═══════════════════════════════════════════════ -->
<section class="container-responsive py-16">
  <div class="relative bg-iron-900 border border-steel-600/25 p-10 md:p-16 overflow-hidden"
       style="clip-path: polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 0 100%)">

    <!-- BG decoration -->
    <div class="absolute top-0 right-0 w-64 h-64 opacity-5 pointer-events-none select-none" aria-hidden="true">
      <svg viewBox="0 0 200 200" fill="none" stroke="#e64a19" stroke-width="0.5">
        <circle cx="100" cy="100" r="90"/>
        <circle cx="100" cy="100" r="70"/>
        <circle cx="100" cy="100" r="50"/>
        <circle cx="100" cy="100" r="30"/>
        <line x1="10" y1="100" x2="190" y2="100"/>
        <line x1="100" y1="10" x2="100" y2="190"/>
        <line x1="29" y1="29" x2="171" y2="171"/>
        <line x1="171" y1="29" x2="29" y2="171"/>
      </svg>
    </div>

    <div class="relative z-10">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">// PARA PROVEEDORES</p>
      <h2 class="font-display text-5xl md:text-7xl text-bone uppercase leading-none mb-4">
        ¿VENDES<br/>AUTOPARTES?
      </h2>
      <p class="font-mono text-sm text-steel-400 uppercase tracking-industrial mb-8 max-w-lg">
        Registra tu empresa · Sube tu catálogo · Llega a miles de talleres y distribuidores en todo el Perú.
      </p>

      <div class="flex flex-wrap gap-4">
        <a href="/vendedor/registro"
           class="btn-rust">
          QUIERO VENDER EN ECOMPARTS
        </a>
        <a href="/vendedor"
           class="btn-outline">
          VER PLANES →
        </a>
      </div>
    </div>
  </div>
</section>
