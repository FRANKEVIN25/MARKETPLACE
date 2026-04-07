<script lang="ts">
  import type { PublicProviderDetail } from '$lib/api/types';

  export let provider: PublicProviderDetail;
  export let averageRating = 0;
  export let productCatalogUrl = '#';

  const fallbackInitial = (name: string) => name.trim().charAt(0).toUpperCase() || 'P';
</script>

<section class="relative overflow-hidden rounded-[2rem] bg-[radial-gradient(circle_at_top_left,_rgba(248,250,252,0.95),_rgba(226,232,240,0.88)_32%,_rgba(15,23,42,1)_100%)] p-8 md:p-10 text-slate-950 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.75)]">
  <div class="absolute inset-0 bg-[linear-gradient(135deg,rgba(14,116,144,0.18),transparent_48%,rgba(249,115,22,0.20))]"></div>

  <div class="relative grid gap-8 xl:grid-cols-[1.1fr,0.9fr] xl:items-start">
    <div class="space-y-6">
      <div class="flex flex-wrap items-center gap-3 text-sm font-semibold uppercase tracking-[0.25em] text-sky-900/75">
        <span class="rounded-full border border-sky-900/10 bg-white/70 px-4 py-2">Plantilla proveedor</span>
        <span>{provider.tier_display}</span>
      </div>

      <div class="flex items-start gap-5">
        {#if provider.logo_url}
          <div class="h-24 w-24 overflow-hidden rounded-[1.5rem] border border-white/80 bg-white shadow-lg shadow-slate-900/10">
            <img src={provider.logo_url} alt={provider.name} class="h-full w-full object-cover" />
          </div>
        {:else}
          <div class="flex h-24 w-24 items-center justify-center rounded-[1.5rem] bg-slate-900 text-3xl font-black text-white shadow-lg shadow-slate-900/20">
            {fallbackInitial(provider.name)}
          </div>
        {/if}

        <div class="space-y-3">
          <div>
            <p class="text-sm font-semibold uppercase tracking-[0.28em] text-sky-900/70">Perfil comercial</p>
            <h1 class="mt-2 text-4xl font-black leading-tight text-slate-950 md:text-5xl">{provider.name}</h1>
            <p class="mt-3 max-w-3xl text-lg font-medium text-sky-900/80">{provider.headline}</p>
          </div>

          <div class="flex flex-wrap items-center gap-3 text-sm text-slate-700">
            <span class="rounded-full border border-slate-900/10 bg-white/70 px-4 py-2 font-semibold">
              {averageRating.toFixed(1)}/5 de reputacion
            </span>
            <span class="rounded-full border border-slate-900/10 bg-white/70 px-4 py-2 font-semibold">
              {provider.rating_count} opiniones
            </span>
            <span class="rounded-full border border-slate-900/10 bg-white/70 px-4 py-2 font-semibold">
              {provider.products_count} productos publicados
            </span>
          </div>
        </div>
      </div>

      <p class="max-w-3xl text-base leading-8 text-slate-700 md:text-lg">
        {provider.long_description || provider.short_description || 'Esta vitrina resume la confianza operativa del proveedor con una estructura comun para todos: reputacion, reglas tributarias, volumen visible del catalogo y comentarios de clientes ya entregados.'}
      </p>

      <div class="flex flex-wrap gap-3 text-sm font-semibold text-slate-700">
        <span class="rounded-full bg-white/75 px-4 py-2">{provider.tax_regime_display}</span>
        <span class="rounded-full bg-white/75 px-4 py-2">{provider.emite_comprobante_display}</span>
        <span class="rounded-full bg-white/75 px-4 py-2">
          {provider.igv_applicable ? 'Opera con IGV' : 'Operacion sin IGV'}
        </span>
        <span class="rounded-full bg-white/75 px-4 py-2">{provider.vehicle_scope_count} variantes habilitadas</span>
      </div>
    </div>

    <aside class="rounded-[1.75rem] border border-white/70 bg-white/82 p-6 backdrop-blur">
      <p class="text-sm font-semibold uppercase tracking-[0.24em] text-sky-800/70">Datos visibles</p>
      <div class="mt-5 grid gap-4 sm:grid-cols-2">
        <div class="rounded-[1.25rem] bg-slate-950 p-5 text-white">
          <p class="text-xs uppercase tracking-[0.24em] text-white/55">Pedidos mensuales</p>
          <p class="mt-3 text-3xl font-black">{provider.monthly_orders}</p>
          <p class="mt-2 text-sm text-white/72">Actividad consolidada para el perfil publico.</p>
        </div>
        <div class="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-5">
          <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Equipo visible</p>
          <p class="mt-3 text-3xl font-black text-slate-950">{provider.members_count}</p>
          <p class="mt-2 text-sm text-slate-600">Usuarios internos vinculados al proveedor.</p>
        </div>
      </div>

      <div class="mt-5 rounded-[1.25rem] border border-slate-200 p-5">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Contacto</p>
        <div class="mt-3 space-y-2 text-sm text-slate-700">
          <p><span class="font-semibold text-slate-950">Correo:</span> {provider.email || 'No publicado'}</p>
          <p><span class="font-semibold text-slate-950">Telefono:</span> {provider.phone || 'No publicado'}</p>
          <p><span class="font-semibold text-slate-950">RUC:</span> {provider.ruc || 'No publicado'}</p>
        </div>
      </div>

      <a href={productCatalogUrl} class="mt-5 inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-5 py-4 text-sm font-semibold text-white transition hover:bg-slate-800">
        Explorar catalogo del proveedor
      </a>
    </aside>
  </div>
</section>
