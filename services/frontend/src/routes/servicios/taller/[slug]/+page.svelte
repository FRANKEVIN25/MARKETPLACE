<script lang="ts">
  import type { PageData } from './$types';
  import {
    commerceLevelLabels,
    formatDuration,
    formatPriceRange,
    serviceLevelLabels,
    serviceTypeLabels,
  } from '$lib/data/service-showcase';

  export let data: PageData;

  const workshop = data.workshop;

  const capabilityBlocks = [
    {
      label: 'SERVICIOS PUBLICADOS',
      value: `${workshop.services.length}`,
      description: 'Oferta activa visible para el cliente final.',
    },
    {
      label: 'DEMANDA ACUMULADA',
      value: `${workshop.totalJobs}`,
      description: 'Historial agregado para medir consistencia.',
    },
    {
      label: 'RATING MÁS ALTO',
      value: `${(workshop.highestSuccessRate / 20).toFixed(1)}/5`,
      description: 'Mejor valoración observada en el catálogo.',
    },
    {
      label: 'EXPERIENCIA',
      value: `${workshop.yearsExperience} AÑOS`,
      description: 'Tiempo operativo comunicado al usuario.',
    },
  ];

  const operatingSignals = [
    `Nivel de servicio: ${serviceLevelLabels[workshop.serviceLevel]}`,
    `Perfil comercial: ${commerceLevelLabels[workshop.commerceLevel]}`,
    workshop.erpIntegrated ? 'ERP integrado para trazabilidad' : 'Operación sin ERP integrado',
    workshop.certified ? 'Certificaciones visibles para reforzar confianza' : 'Certificación aún no declarada',
  ];
</script>

<svelte:head>
  <title>{workshop.workshopName} — Taller — ECOMPARTS</title>
  <meta
    name="description"
    content={`Detalle de taller para ${workshop.workshopName}, con expertise por vehículo, catálogo y señales de confianza.`}
  />
</svelte:head>

<!-- Breadcrumb -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-3">
    <div class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-steel-500">
      <a href="/servicios" class="hover:text-rust-500 transition-colors">SERVICIOS</a>
      <span class="text-steel-700">/</span>
      <a href="/servicios/resultados" class="hover:text-rust-500 transition-colors">RESULTADOS</a>
      <span class="text-steel-700">/</span>
      <span class="text-bone truncate">{workshop.workshopName}</span>
    </div>
  </div>
</div>

<!-- Hero del taller -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-10">
    <div class="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-8 items-start">

      <!-- Info principal -->
      <div>
        <div class="flex flex-wrap gap-2 mb-5">
          <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-3 py-1">
            FICHA DE TALLER
          </span>
          {#if workshop.verified}
            <span class="font-mono text-[9px] uppercase tracking-widest border border-green-700/50 text-green-400 bg-green-600/10 px-3 py-1">
              ✓ VERIFICADO
            </span>
          {/if}
          {#if workshop.erpIntegrated}
            <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-3 py-1">
              ERP INTEGRADO
            </span>
          {/if}
          {#if workshop.certified}
            <span class="font-mono text-[9px] uppercase tracking-widest border border-rust-700/50 text-rust-500 px-3 py-1">
              CERTIFICADO
            </span>
          {/if}
        </div>

        <h1 class="font-display text-5xl md:text-6xl text-bone uppercase leading-none mb-3">
          {workshop.workshopName}
        </h1>
        <p class="font-mono text-sm text-steel-400 mb-5 max-w-2xl leading-relaxed">
          {workshop.workshopHeadline}
        </p>

        <div class="flex flex-wrap gap-3">
          <span class="font-mono text-[10px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-3 py-1.5">
            📍 {workshop.district}
          </span>
          <span class="font-mono text-[10px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-3 py-1.5">
            {serviceLevelLabels[workshop.serviceLevel]}
          </span>
        </div>
      </div>

      <!-- KPIs snapshot -->
      <div class="bg-iron-800 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// KPIs DEL TALLER</p>
        </div>
        <div class="grid grid-cols-2 divide-x divide-steel-600/20">
          {#each capabilityBlocks as item, i}
            <div class="px-5 py-4 {i < 2 ? 'border-b border-steel-600/20' : ''}">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{item.label}</p>
              <p class="font-display text-3xl text-rust-600 leading-none mb-1">{item.value}</p>
              <p class="font-mono text-[9px] text-steel-600 leading-relaxed">{item.description}</p>
            </div>
          {/each}
        </div>
        <div class="border-t border-steel-600/25 px-5 py-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COBERTURA DE PRECIOS</p>
          <p class="font-display text-2xl text-bone leading-none">
            {formatPriceRange(workshop.lowestPrice, workshop.highestPrice)}
          </p>
          <p class="font-mono text-[9px] text-steel-600 mt-1">
            RATING TOPE: {(workshop.highestSuccessRate / 20).toFixed(1)}/5
          </p>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Contenido principal -->
<div class="container-responsive py-10">

  {#if data.error}
    <div class="border border-rust-700/50 bg-rust-600/10 p-6 mb-8 flex items-start gap-3">
      <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
      <div>
        <p class="font-mono text-xs text-rust-400 uppercase tracking-widest mb-1">ERROR AL CARGAR PERFIL</p>
        <p class="font-mono text-xs text-steel-400">{data.error}</p>
      </div>
    </div>
  {/if}

  <div class="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-8">

    <!-- Catálogo de servicios -->
    <div>
      <div class="border-b border-steel-600/25 pb-4 mb-6 flex items-center justify-between">
        <div>
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// CATÁLOGO ACTIVO</p>
          <h2 class="font-display text-3xl text-bone uppercase leading-none">SERVICIOS PUBLICADOS</h2>
        </div>
        <a href="/servicios/resultados"
           class="font-mono text-[10px] uppercase tracking-widest text-rust-500 hover:text-rust-400 transition-colors">
          ← VOLVER
        </a>
      </div>

      <div class="space-y-4">
        {#each workshop.services as service}
          <div class="bg-iron-900 border border-steel-600/25"
               style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">

            <div class="border-b border-steel-600/25 px-5 py-3 flex items-start justify-between gap-3">
              <div>
                <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-1">
                  {service.category} · {serviceTypeLabels[service.serviceType]}
                </p>
                <h3 class="font-display text-2xl text-bone uppercase leading-none">{service.serviceName}</h3>
              </div>
              <div class="flex flex-wrap gap-2 flex-shrink-0">
                {#if service.verified}
                  <span class="font-mono text-[9px] uppercase border border-green-700/50 text-green-400 px-2 py-0.5">✓ VERIF.</span>
                {/if}
                {#if service.specialized}
                  <span class="font-mono text-[9px] uppercase border border-rust-700/50 text-rust-500 px-2 py-0.5">★ ESPEC.</span>
                {/if}
              </div>
            </div>

            <div class="p-5">
              <p class="font-mono text-xs text-steel-400 mb-4">
                {formatPriceRange(service.priceMin, service.priceMax)} · {formatDuration(service.durationMin)}
              </p>

              <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
                {#each [
                  { label: 'DEMANDA', value: service.totalJobs },
                  { label: 'RATING', value: `${service.avgRating.toFixed(1)}/5` },
                  { label: 'VARIACIÓN', value: service.repeatFailureRate.toFixed(1) },
                  { label: 'VEHÍCULOS', value: service.vehicleExpertise.length },
                ] as kpi}
                  <div class="bg-iron-800 border border-steel-600/20 p-3">
                    <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{kpi.label}</p>
                    <p class="font-display text-xl text-bone leading-none">{kpi.value}</p>
                  </div>
                {/each}
              </div>

              {#if service.trustNotes.length > 0}
                <div class="flex flex-wrap gap-2 mb-4">
                  {#each service.trustNotes as note}
                    <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-400 px-2 py-0.5">{note}</span>
                  {/each}
                </div>
              {/if}

              <a href={`/servicios/servicio/${service.serviceSlug}`}
                 class="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-industrial text-bone
                        border border-steel-600/50 px-5 py-2.5 hover:border-rust-600 hover:text-rust-500 transition-colors">
                VER DETALLE →
              </a>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Sidebar: señales + expertise -->
    <div class="space-y-5">

      <!-- Señales operativas -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SEÑALES OPERATIVAS</p>
        </div>
        <div class="p-5 space-y-2">
          {#each operatingSignals as signal}
            <div class="flex items-start gap-3 border border-steel-600/20 bg-iron-800/50 p-3">
              <span class="text-green-400 font-mono text-xs flex-shrink-0">✓</span>
              <p class="font-mono text-xs text-steel-400 leading-relaxed">{signal}</p>
            </div>
          {/each}
        </div>
      </div>

      <!-- Expertise vehicular -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// EXPERTISE VEHICULAR</p>
        </div>
        <div class="p-5">
          <div class="flex flex-wrap gap-2 mb-4">
            {#each workshop.vehicleExpertise as vehicle}
              <span class="font-mono text-[10px] uppercase tracking-widest border border-steel-600/40 text-steel-300 px-3 py-1">
                {vehicle}
              </span>
            {/each}
          </div>
          <p class="font-mono text-[9px] text-steel-600 leading-relaxed">
            ESTE TALLER TIENE EXPERIENCIA REAL EN ESTAS COMBINACIONES DE MARCA/MODELO.
          </p>
        </div>
      </div>

    </div>
  </div>

  <!-- Otros servicios relacionados -->
  {#if data.relatedListings.length > 0}
    <div class="mt-12 border-t border-steel-600/25 pt-10">
      <div class="border-b border-steel-600/25 pb-4 mb-6">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// SEGUIR EXPLORANDO</p>
        <h2 class="font-display text-3xl text-bone uppercase leading-none">OTROS SERVICIOS</h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {#each data.relatedListings as listing}
          <a href={`/servicios/servicio/${listing.serviceSlug}`}
             class="bg-iron-900 border border-steel-600/25 p-5 hover:border-rust-600/60 transition-colors group"
             style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
            <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-2">{listing.category}</p>
            <h3 class="font-display text-xl text-bone uppercase leading-tight mb-2 group-hover:text-rust-400 transition-colors">
              {listing.serviceName}
            </h3>
            <p class="font-mono text-[10px] text-steel-500 mb-3">{listing.workshopName}</p>
            <p class="font-mono text-xs text-steel-400">{formatPriceRange(listing.priceMin, listing.priceMax)}</p>
          </a>
        {/each}
      </div>
    </div>
  {/if}

</div>
