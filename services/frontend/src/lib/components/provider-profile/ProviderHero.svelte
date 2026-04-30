<script lang="ts">
  import type { PublicProviderDetail } from '$lib/api/types';

  export let provider: PublicProviderDetail;
  export let averageRating = 0;
  export let productCatalogUrl = '#';

  const fallbackInitial = (name: string) => name.trim().charAt(0).toUpperCase() || 'P';
</script>

<div class="bg-iron-900 border border-steel-600/25"
     style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
  <div class="border-b border-steel-600/25 px-6 py-3 flex items-center gap-3">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PERFIL COMERCIAL</p>
    <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">
      {provider.tier_display}
    </span>
  </div>

  <div class="p-6 md:p-8 grid gap-8 xl:grid-cols-[1.1fr_0.9fr] xl:items-start">
    <div class="space-y-5">
      <div class="flex items-start gap-5">
        {#if provider.logo_url}
          <div class="h-20 w-20 overflow-hidden border border-steel-600/40 bg-iron-800 flex-shrink-0">
            <img src={provider.logo_url} alt={provider.name} class="h-full w-full object-cover" />
          </div>
        {:else}
          <div class="flex h-20 w-20 items-center justify-center bg-iron-800 border border-steel-600/40 font-display text-3xl text-rust-600 flex-shrink-0">
            {fallbackInitial(provider.name)}
          </div>
        {/if}
        <div>
          <h1 class="font-display text-4xl md:text-5xl text-bone uppercase leading-none mb-2">{provider.name}</h1>
          <p class="font-mono text-xs text-steel-400">{provider.headline}</p>
        </div>
      </div>

      <p class="font-mono text-xs text-steel-400 leading-relaxed max-w-2xl">
        {provider.long_description || provider.short_description || 'Esta vitrina resume la confianza operativa del proveedor con una estructura comun para todos: reputacion, reglas tributarias, volumen visible del catalogo y comentarios de clientes ya entregados.'}
      </p>

      <div class="flex flex-wrap gap-2">
        {#each [
          provider.tax_regime_display,
          provider.emite_comprobante_display,
          provider.igv_applicable ? 'OPERA CON IGV' : 'SIN IGV',
          `${provider.vehicle_scope_count} VARIANTES`,
        ] as tag}
          <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">{tag}</span>
        {/each}
      </div>

      <div class="flex flex-wrap gap-3">
        {#each [
          `${averageRating.toFixed(1)}/5 REPUTACIÓN`,
          `${provider.rating_count} OPINIONES`,
          `${provider.products_count} PRODUCTOS`,
        ] as stat}
          <span class="font-mono text-[10px] uppercase tracking-widest border border-steel-600/25 text-steel-300 px-3 py-1.5">{stat}</span>
        {/each}
      </div>
    </div>

    <div class="bg-iron-800 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-5 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS VISIBLES</p>
      </div>
      <div class="grid grid-cols-2 divide-x divide-steel-600/20 border-b border-steel-600/20">
        <div class="px-5 py-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">PEDIDOS/MES</p>
          <p class="font-display text-4xl text-rust-600 leading-none">{provider.monthly_orders}</p>
        </div>
        <div class="px-5 py-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">EQUIPO</p>
          <p class="font-display text-4xl text-bone leading-none">{provider.members_count}</p>
        </div>
      </div>
      <div class="px-5 py-4 space-y-2 border-b border-steel-600/20">
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">CONTACTO</p>
        {#each [
          { label: 'CORREO', value: provider.email || 'No publicado' },
          { label: 'TELÉFONO', value: provider.phone || 'No publicado' },
          { label: 'RUC', value: provider.ruc || 'No publicado' },
        ] as row}
          <div class="flex justify-between gap-3">
            <span class="font-mono text-[10px] text-steel-600 uppercase">{row.label}</span>
            <span class="font-mono text-[10px] text-bone">{row.value}</span>
          </div>
        {/each}
      </div>
      <div class="px-5 py-4">
        <a href={productCatalogUrl} class="btn-rust w-full text-center block">EXPLORAR CATÁLOGO →</a>
      </div>
    </div>
  </div>
</div>
