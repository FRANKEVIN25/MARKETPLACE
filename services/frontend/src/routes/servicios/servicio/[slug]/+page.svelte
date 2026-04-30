<script lang="ts">
  import type { PageData } from './$types';
  import {
    formatDuration,
    formatPriceRange,
    serviceLevelLabels,
    serviceTypeLabels,
  } from '$lib/data/service-showcase';

  export let data: PageData;

  const service = data.service;

  const processByType = {
    maintenance: [
      'Recepción y checklist inicial',
      'Ejecución preventiva con trazabilidad',
      'Entrega con tareas futuras sugeridas',
    ],
    repair: [
      'Diagnóstico corto para confirmar causa',
      'Intervención correctiva y validación',
      'Prueba final y cierre documentado',
    ],
    diagnostic: [
      'Levantamiento de síntomas y contexto',
      'Lectura de códigos y pruebas dirigidas',
      'Informe priorizado con siguiente acción',
    ],
  } as const;

  const deliverablesByType = {
    maintenance: ['Checklist digital', 'Consumo recomendado', 'Próximo hito sugerido'],
    repair: ['Diagnóstico confirmado', 'Registro de piezas', 'Validación post reparación'],
    diagnostic: ['Códigos relevantes', 'Pruebas realizadas', 'Ruta de solución propuesta'],
  } as const;

  const trustExplainers = [
    'Historial acumulado del mismo servicio en talleres reales.',
    'Éxito operativo y recurrencia de fallas, no estrellas inventadas.',
    'Compatibilidad vehicular visible para reducir incertidumbre.',
  ];
</script>

<svelte:head>
  <title>{service.serviceName} — Servicio — ECOMPARTS</title>
  <meta
    name="description"
    content={`Detalle del servicio ${service.serviceName}, con talleres que lo ofrecen, precios y métricas reales.`}
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
      <span class="text-bone truncate">{service.serviceName}</span>
    </div>
  </div>
</div>

<!-- Hero del servicio -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-10">
    <div class="grid grid-cols-1 xl:grid-cols-[1.05fr_0.95fr] gap-8 items-start">

      <!-- Info principal -->
      <div>
        <div class="flex flex-wrap gap-2 mb-5">
          <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-3 py-1">
            FICHA EXPLICATIVA DEL SERVICIO
          </span>
        </div>

        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">
          {service.category} · {serviceTypeLabels[service.serviceType]}
        </p>
        <h1 class="font-display text-5xl md:text-6xl text-bone uppercase leading-none mb-4">
          {service.serviceName}
        </h1>
        <p class="font-mono text-xs text-steel-400 max-w-2xl leading-relaxed">
          Esta ficha explica qué resuelve el servicio, qué señales usa para ordenar talleres y cómo aterriza el siguiente paso comercial sin perder claridad técnica.
        </p>

        <!-- KPIs resumen -->
        <div class="grid grid-cols-3 gap-3 mt-6">
          <div class="bg-iron-800 border border-steel-600/25 p-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COBERTURA</p>
            <p class="font-display text-3xl text-rust-600 leading-none">{service.workshops.length}</p>
            <p class="font-mono text-[9px] text-steel-600">TALLERES</p>
          </div>
          <div class="bg-iron-800 border border-steel-600/25 p-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">PRECIO</p>
            <p class="font-display text-2xl text-bone leading-none">{formatPriceRange(service.minPrice, service.maxPrice)}</p>
          </div>
          <div class="bg-iron-800 border border-steel-600/25 p-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">TIEMPO MÍN.</p>
            <p class="font-display text-3xl text-bone leading-none">{formatDuration(service.minDuration)}</p>
          </div>
        </div>
      </div>

      <!-- Snapshot -->
      <div class="bg-iron-800 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SNAPSHOT DEL SERVICIO</p>
        </div>
        <div class="grid grid-cols-2 divide-x divide-steel-600/20">
          {#each [
            { label: 'DEMANDA',   value: `${service.totalJobs}` },
            { label: 'RATING MÁX.', value: `${(service.highestSuccessRate / 20).toFixed(1)}/5` },
            { label: 'VARIACIÓN', value: `${service.averageRepeatFailureRate.toFixed(1)}` },
            { label: 'DISTRITOS', value: `${service.districts.length}` },
          ] as kpi, i}
            <div class="px-5 py-4 {i < 2 ? 'border-b border-steel-600/20' : ''}">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{kpi.label}</p>
              <p class="font-display text-3xl text-rust-600 leading-none">{kpi.value}</p>
            </div>
          {/each}
        </div>
        <div class="border-t border-steel-600/25 px-5 py-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-3">COMPATIBILIDAD VEHICULAR</p>
          <div class="flex flex-wrap gap-2">
            {#each service.vehicleExpertise as vehicle}
              <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">{vehicle}</span>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Contenido principal -->
<div class="container-responsive py-10 space-y-8">

  {#if data.error}
    <div class="border border-rust-700/50 bg-rust-600/10 p-6 flex items-start gap-3">
      <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
      <div>
        <p class="font-mono text-xs text-rust-400 uppercase tracking-widest mb-1">ERROR AL CARGAR DATOS</p>
        <p class="font-mono text-xs text-steel-400">{data.error}</p>
      </div>
    </div>
  {/if}

  <div class="grid grid-cols-1 lg:grid-cols-[0.95fr_1.05fr] gap-8">

    <!-- Qué incluye + flujo operativo -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// QUÉ INCLUYE ESTA FICHA</p>
        <h2 class="font-display text-3xl text-bone uppercase leading-none">EXPLICACIÓN DEL SERVICIO</h2>
      </div>
      <div class="p-6 space-y-3 mb-2">
        {#each deliverablesByType[service.serviceType] as item}
          <div class="flex items-start gap-3 border border-steel-600/20 bg-iron-800/50 px-4 py-3">
            <span class="text-green-400 font-mono text-xs flex-shrink-0">✓</span>
            <p class="font-mono text-xs text-steel-400">{item}</p>
          </div>
        {/each}
      </div>

      <div class="border-t border-steel-600/25 bg-iron-800/30 px-6 py-5">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">// FLUJO OPERATIVO ESPERADO</p>
        <div class="space-y-3">
          {#each processByType[service.serviceType] as step, index}
            <div class="flex gap-4 border border-steel-600/20 bg-iron-800/50 px-4 py-3 items-center">
              <div class="w-8 h-8 bg-rust-600/20 border border-rust-700/50 flex items-center justify-center flex-shrink-0">
                <span class="font-display text-lg text-rust-500 leading-none">{index + 1}</span>
              </div>
              <p class="font-mono text-xs text-steel-400">{step}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Talleres que lo ofrecen -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// TALLERES QUE LO OFRECEN</p>
        <h2 class="font-display text-3xl text-bone uppercase leading-none">OFERTA COMPARATIVA</h2>
      </div>
      <div class="divide-y divide-steel-600/20">
        {#each service.workshops as workshop}
          <div class="p-5">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3 mb-4">
              <div>
                <h3 class="font-display text-2xl text-bone uppercase leading-none mb-1">{workshop.workshopName}</h3>
                <p class="font-mono text-xs text-steel-400">{workshop.workshopHeadline}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                {#if workshop.verified}
                  <span class="font-mono text-[9px] uppercase border border-green-700/50 text-green-400 px-2 py-0.5">✓ VERIF.</span>
                {/if}
                {#if workshop.specialized}
                  <span class="font-mono text-[9px] uppercase border border-rust-700/50 text-rust-500 px-2 py-0.5">★ ESPEC.</span>
                {/if}
                {#if workshop.erpIntegrated}
                  <span class="font-mono text-[9px] uppercase border border-steel-600/40 text-steel-400 px-2 py-0.5">ERP</span>
                {/if}
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
              {#each [
                { label: 'PRECIO', value: formatPriceRange(workshop.priceMin, workshop.priceMax) },
                { label: 'TIEMPO', value: formatDuration(workshop.durationMin) },
                { label: 'RATING', value: `${workshop.avgRating.toFixed(1)}/5` },
                { label: 'NIVEL',  value: serviceLevelLabels[workshop.serviceLevel] },
              ] as kpi}
                <div class="bg-iron-800/50 border border-steel-600/20 p-3">
                  <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{kpi.label}</p>
                  <p class="font-mono text-xs text-bone">{kpi.value}</p>
                </div>
              {/each}
            </div>

            {#if workshop.trustNotes.length > 0}
              <div class="flex flex-wrap gap-1.5 mb-4">
                {#each workshop.trustNotes as note}
                  <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-500 px-2 py-0.5">{note}</span>
                {/each}
              </div>
            {/if}

            <div class="flex gap-3">
              <a href={`/servicios/taller/${workshop.workshopSlug}`} class="btn-rust text-xs">VER TALLER →</a>
              <a href="/servicios/resultados" class="btn-outline text-xs">COMPARAR MÁS</a>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Confianza + Cobertura -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">

    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-5 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// CÓMO SE ORDENA LA CONFIANZA</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">SEÑALES EXPLÍCITAS</h2>
      </div>
      <div class="p-5 space-y-2">
        {#each trustExplainers as item}
          <div class="flex items-start gap-3 border border-steel-600/20 bg-iron-800/50 p-3">
            <span class="text-green-400 font-mono text-xs flex-shrink-0">✓</span>
            <p class="font-mono text-xs text-steel-400 leading-relaxed">{item}</p>
          </div>
        {/each}
      </div>
    </div>

    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-5 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// COBERTURA GEOGRÁFICA</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">DISPONIBILIDAD</h2>
      </div>
      <div class="p-5">
        <div class="flex flex-wrap gap-2 mb-5">
          {#each service.districts as district}
            <span class="font-mono text-[10px] uppercase tracking-widest border border-steel-600/40 text-steel-300 px-3 py-1">{district}</span>
          {/each}
        </div>
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-3">NOTAS DE CONFIANZA MÁS REPETIDAS</p>
        <div class="flex flex-wrap gap-2">
          {#each service.trustNotes as note}
            <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-500 px-2 py-0.5">{note}</span>
          {/each}
        </div>
      </div>
    </div>
  </div>

  <!-- Servicios relacionados -->
  {#if data.relatedListings.length > 0}
    <div class="border-t border-steel-600/25 pt-8">
      <div class="border-b border-steel-600/25 pb-4 mb-6">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// SERVICIOS RELACIONADOS</p>
        <h2 class="font-display text-3xl text-bone uppercase leading-none">MÁS OPCIONES</h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {#each data.relatedListings as listing}
          <a href={`/servicios/servicio/${listing.serviceSlug}`}
             class="bg-iron-900 border border-steel-600/25 p-5 hover:border-rust-600/60 transition-colors group block"
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
