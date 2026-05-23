<script lang="ts">
  const SIDE_LABELS = {
    left: 'Izquierda',
    right: 'Derecha',
    front: 'Delantera',
    rear: 'Posterior',
    both: 'Ambos lados',
    na: 'No aplica',
  } as const;

  const QUALITY_LABELS = {
    original: 'Original',
    oem: 'OEM',
    aftermarket_premium: 'Alternativo Premium',
    aftermarket_standard: 'Alternativo Estándar',
  } as const;

  export let product: {
    id: number;
    nombre?: string;
    name?: string;
    slug?: string;
    proveedor?: string;
    supplier?: string;
    provider_name?: string;
    provider_slug?: string;
    categoria?: string;
    category?: string | number;
    category_name?: string;
    precio?: number;
    price?: number | string;
    image_url?: string;
    imagen?: string;
    image?: string;
    stock?: number;
    sku?: string;
    autopart_side?: keyof typeof SIDE_LABELS;
    autopart_side_display?: string;
    autopart_quality?: keyof typeof QUALITY_LABELS;
    autopart_quality_display?: string;
  };

  // Map API properties
  $: nombre     = product.nombre || product.name || 'SIN NOMBRE';
  $: proveedor  = product.proveedor || product.supplier || product.provider_name || 'SIN PROVEEDOR';
  $: proveedorUrl = product.provider_slug ? `/proveedores/${product.provider_slug}` : null;
  $: categoria  = product.categoria || product.category || product.category_name || 'GENERAL';
  $: precio     = product.precio || product.price || 0;
  $: imagen     = product.image_url || product.imagen || product.image;
  $: sku        = product.sku || `ECO-${String(product.id).padStart(6, '0')}`;
  $: inStock    = product.stock === undefined || product.stock > 0;
  $: lado = product.autopart_side_display
    || (product.autopart_side ? SIDE_LABELS[product.autopart_side] : undefined);
  $: calidad = product.autopart_quality_display
    || (product.autopart_quality ? QUALITY_LABELS[product.autopart_quality] : undefined);
  $: mostrarLado = Boolean(lado && product.autopart_side !== 'na');
  $: mostrarCalidad = Boolean(calidad);

  function formatPrice(p: number | string): string {
    const n = parseFloat(p.toString());
    return isNaN(n) ? '0.00' : n.toFixed(2);
  }
</script>

<!-- Industrial product card — ficha técnica style -->
<div class="card-3d group relative flex flex-col" style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">

  <!-- ── SKU header bar ── -->
  <div class="bg-rust-600 px-3 py-1.5 flex items-center justify-between">
    <span class="font-mono text-[10px] text-bone tracking-widest uppercase">{sku}</span>
    <div class="flex items-center gap-2">
      <span class="font-mono text-[10px] text-bone/70 uppercase tracking-wide">{String(categoria).toUpperCase()}</span>
      <span class="w-1.5 h-1.5 rounded-full {inStock ? 'bg-green-400' : 'bg-red-400'}"></span>
    </div>
  </div>

  <!-- ── Image area ── -->
  <div class="relative bg-iron-800 h-44 flex items-center justify-center overflow-hidden">

    {#if imagen}
      <img
        src={imagen}
        alt={nombre}
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
      />
      <!-- Metal sheen overlay on hover -->
      <div class="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    {:else}
      <!-- Industrial no-image placeholder -->
      <div class="text-center relative z-10">
        <svg class="w-14 h-14 mx-auto text-steel-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest">SIN IMAGEN</p>
      </div>

      <!-- Grid pattern on placeholder -->
      <div class="absolute inset-0 pointer-events-none opacity-40"
           style="background-image: linear-gradient(rgba(84,110,122,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(84,110,122,0.15) 1px, transparent 1px); background-size: 20px 20px;">
      </div>
    {/if}

    <!-- Corner cut decoration (top-right) -->
    <div class="absolute top-0 right-0 w-[14px] h-[14px] bg-iron-900 pointer-events-none"
         style="clip-path: polygon(0 0, 100% 0, 100% 100%)"></div>

    <!-- Stock badge -->
    <div class="absolute bottom-2 left-2">
      {#if inStock}
        <span class="font-mono text-[9px] uppercase tracking-widest bg-iron-900/80 text-green-400 border border-green-500/30 px-2 py-0.5">
          EN STOCK
        </span>
      {:else}
        <span class="font-mono text-[9px] uppercase tracking-widest bg-iron-900/80 text-red-400 border border-red-500/30 px-2 py-0.5">
          AGOTADO
        </span>
      {/if}
    </div>
  </div>

  <!-- ── Content ── -->
  <div class="flex flex-col flex-1 bg-iron-900 border-t border-steel-600/20 p-4">

    <!-- Product name -->
    <h3 class="font-display text-2xl text-bone leading-tight uppercase mb-1 line-clamp-2" title={nombre}>
      {nombre}
    </h3>

    <!-- Provider -->
    <div class="mb-3">
      {#if proveedorUrl}
        <a href={proveedorUrl}
           class="font-mono text-[10px] text-steel-500 hover:text-rust-500 transition-colors uppercase tracking-widest">
          /{proveedor}
        </a>
      {:else}
        <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">/{proveedor}</span>
      {/if}
    </div>

    <!-- Horizontal rule -->
    <div class="border-t border-steel-600/25 mb-3"></div>

    {#if mostrarLado || mostrarCalidad}
      <div class="mb-4 flex flex-wrap gap-2">
        {#if mostrarLado}
          <span class="border border-steel-600/40 bg-iron-800 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-steel-300">
            LADO: {lado}
          </span>
        {/if}
        {#if mostrarCalidad}
          <span class="border border-rust-600/35 bg-rust-600/10 px-2 py-1 font-mono text-[9px] uppercase tracking-widest text-rust-300">
            CALIDAD: {calidad}
          </span>
        {/if}
      </div>
    {/if}

    <!-- Price block -->
    <div class="flex items-baseline gap-1.5 mb-4">
      <span class="font-mono text-xs text-steel-500 self-start mt-1">S/.</span>
      <span class="font-display text-5xl text-bone leading-none">
        {formatPrice(precio).split('.')[0]}
      </span>
      <span class="font-mono text-sm text-steel-400 self-end mb-0.5">
        .{formatPrice(precio).split('.')[1]}
      </span>
    </div>

    <!-- CTA button -->
    <a
      href={`/productos/${product.id}`}
      class="mt-auto block w-full bg-iron-800 hover:bg-rust-600 text-bone font-mono text-[11px] uppercase tracking-industrial py-3 text-center transition-colors duration-200 border border-steel-600/40 hover:border-rust-600 group-hover:border-rust-600/50"
    >
      VER FICHA TÉCNICA →
    </a>
  </div>

</div>

<style>
  /* Ensure clip-path is applied correctly */
  div[style*="clip-path"] {
    overflow: hidden;
  }
</style>
