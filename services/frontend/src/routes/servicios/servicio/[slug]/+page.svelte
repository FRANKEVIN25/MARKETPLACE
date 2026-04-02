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
  <title>{service.serviceName} | Plantilla de Servicio | ECOMPARTS</title>
  <meta
    name="description"
    content={`Detalle del servicio ${service.serviceName}, con talleres que lo ofrecen, precios y métricas reales.`}
  />
</svelte:head>

<section class="bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-900 text-white">
  <div class="max-w-7xl mx-auto px-6 py-16 md:py-20 space-y-8">
    <div class="flex flex-wrap items-center gap-3 text-sm text-blue-100">
      <a href="/servicios" class="hover:text-white transition">Servicios</a>
      <span class="text-white/40">/</span>
      <a href="/servicios/resultados" class="hover:text-white transition">Resultados</a>
      <span class="text-white/40">/</span>
      <span>{service.serviceName}</span>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1.05fr,0.95fr] gap-10 items-start">
      <div class="space-y-7">
        <div class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-blue-100">
          <span>Plantilla 4</span>
          <span class="text-white/40">•</span>
          <span>Detalle del servicio</span>
        </div>

        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-200 mb-3">Ficha explicativa del servicio</p>
          <h1 class="text-4xl md:text-5xl font-black leading-tight max-w-4xl">{service.serviceName}</h1>
          <p class="text-xl text-blue-100 mt-3 max-w-3xl">{service.category} · {serviceTypeLabels[service.serviceType]}</p>
          <p class="text-blue-100/80 mt-5 max-w-3xl leading-relaxed">
            Esta plantilla explica qué resuelve el servicio, qué señales usa para ordenar talleres y cómo aterriza el siguiente paso comercial sin perder claridad técnica.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="rounded-2xl border border-white/10 bg-white/10 p-5">
            <p class="text-xs uppercase tracking-wide text-blue-200 mb-1">Cobertura</p>
            <p class="text-2xl font-bold">{service.workshops.length} talleres</p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/10 p-5">
            <p class="text-xs uppercase tracking-wide text-blue-200 mb-1">Precio</p>
            <p class="text-2xl font-bold">{formatPriceRange(service.minPrice, service.maxPrice)}</p>
          </div>
          <div class="rounded-2xl border border-white/10 bg-white/10 p-5">
            <p class="text-xs uppercase tracking-wide text-blue-200 mb-1">Tiempo mínimo</p>
            <p class="text-2xl font-bold">{formatDuration(service.minDuration)}</p>
          </div>
        </div>
      </div>

      <aside class="rounded-3xl bg-white text-slate-900 p-6 md:p-7 shadow-2xl">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">Snapshot del servicio</p>
        <h2 class="text-2xl font-bold mb-3">Indicadores listos para decisión</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          <div class="rounded-2xl border border-gray-200 bg-slate-50 p-4">
            <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Demanda</p>
            <p class="text-2xl font-bold text-gray-900">{service.totalJobs}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-slate-50 p-4">
            <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Rating máx.</p>
            <p class="text-2xl font-bold text-gray-900">{(service.highestSuccessRate / 20).toFixed(1)}/5</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-slate-50 p-4">
            <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Variación</p>
            <p class="text-2xl font-bold text-gray-900">{service.averageRepeatFailureRate.toFixed(1)}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-slate-50 p-4">
            <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Distritos</p>
            <p class="text-2xl font-bold text-gray-900">{service.districts.length}</p>
          </div>
        </div>

        <div class="rounded-2xl border border-gray-200 p-5">
          <p class="text-sm font-semibold text-gray-900 mb-2">Compatibilidad visible</p>
          <div class="flex flex-wrap gap-2">
            {#each service.vehicleExpertise as vehicle}
              <span class="rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-semibold">{vehicle}</span>
            {/each}
          </div>
        </div>
      </aside>
    </div>
  </div>
</section>

<section class="max-w-7xl mx-auto px-6 py-16 space-y-10">
  {#if data.error}
    <div class="rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
      <h3 class="text-xl font-bold mb-2">No se pudo refrescar el detalle desde el backend</h3>
      <p class="text-sm">{data.error}</p>
    </div>
  {/if}

  <section class="grid grid-cols-1 lg:grid-cols-[0.95fr,1.05fr] gap-8">
    <article class="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-3">Qué incluye esta ficha</p>
      <h2 class="text-3xl font-bold text-gray-900 mb-6">Explicación clara del servicio</h2>

      <div class="space-y-4 mb-8">
        {#each deliverablesByType[service.serviceType] as item}
          <div class="flex items-start gap-3 rounded-2xl border border-gray-200 p-4">
            <span class="text-emerald-600">✓</span>
            <p class="text-gray-700">{item}</p>
          </div>
        {/each}
      </div>

      <div class="rounded-3xl bg-slate-950 p-6 text-white">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-300 mb-3">Flujo operativo esperado</p>
        <div class="space-y-3">
          {#each processByType[service.serviceType] as step, index}
            <div class="flex gap-4 rounded-2xl border border-white/10 bg-white/5 p-4">
              <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-600 font-bold text-white">
                {index + 1}
              </div>
              <p class="text-blue-100">{step}</p>
            </div>
          {/each}
        </div>
      </div>
    </article>

    <article class="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-3">Talleres que lo ofrecen</p>
      <h2 class="text-3xl font-bold text-gray-900 mb-6">Oferta comparativa por confianza</h2>

      <div class="space-y-4">
        {#each service.workshops as workshop}
          <article class="rounded-3xl border border-gray-200 p-6">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-4">
              <div>
                <h3 class="text-2xl font-bold text-gray-900">{workshop.workshopName}</h3>
                <p class="text-gray-600 mt-1">{workshop.workshopHeadline}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                {#if workshop.verified}
                  <span class="rounded-full bg-emerald-50 text-emerald-700 px-3 py-1 text-xs font-semibold">✔ Verificado</span>
                {/if}
                {#if workshop.specialized}
                  <span class="rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-semibold">🏆 Especializado</span>
                {/if}
                {#if workshop.erpIntegrated}
                  <span class="rounded-full bg-indigo-50 text-indigo-700 px-3 py-1 text-xs font-semibold">🧠 ERP integrado</span>
                {/if}
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Precio</p>
                <p class="font-bold text-gray-900">{formatPriceRange(workshop.priceMin, workshop.priceMax)}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Tiempo</p>
                <p class="font-bold text-gray-900">{formatDuration(workshop.durationMin)}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Éxito</p>
                <p class="font-bold text-gray-900">{workshop.avgRating.toFixed(1)}/5</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Nivel</p>
                <p class="font-bold text-gray-900">{serviceLevelLabels[workshop.serviceLevel]}</p>
              </div>
            </div>

            <div class="flex flex-wrap gap-2 mb-5">
              {#each workshop.trustNotes as note}
                <span class="rounded-full bg-slate-100 text-slate-700 px-3 py-1 text-xs font-semibold">{note}</span>
              {/each}
            </div>

            <div class="flex gap-3">
              <a href={`/servicios/taller/${workshop.workshopSlug}`} class="rounded-xl bg-blue-600 text-white font-semibold px-5 py-3 hover:bg-blue-700 transition">
                Ver taller
              </a>
              <a href="/servicios/resultados" class="rounded-xl border border-gray-300 px-5 py-3 font-semibold text-gray-700 hover:bg-gray-50 transition">
                Comparar más
              </a>
            </div>
          </article>
        {/each}
      </div>
    </article>
  </section>

  <section class="grid grid-cols-1 lg:grid-cols-[1fr,1fr] gap-8">
    <article class="rounded-3xl border border-gray-200 bg-slate-950 p-8 text-white shadow-sm">
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-300 mb-3">Cómo se ordena la confianza</p>
      <h2 class="text-3xl font-bold mb-6">Señales explícitas para evitar marketplace genérico</h2>
      <div class="space-y-3">
        {#each trustExplainers as item}
          <div class="rounded-2xl border border-white/10 bg-white/5 p-4 text-blue-100">
            {item}
          </div>
        {/each}
      </div>
    </article>

    <article class="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-3">Cobertura geográfica</p>
      <h2 class="text-3xl font-bold text-gray-900 mb-6">Dónde aparece disponible este servicio</h2>
      <div class="flex flex-wrap gap-3 mb-6">
        {#each service.districts as district}
          <span class="rounded-full bg-blue-50 text-blue-700 px-4 py-2 text-sm font-semibold">{district}</span>
        {/each}
      </div>

      <p class="text-sm font-semibold text-gray-900 mb-3">Notas de confianza más repetidas</p>
      <div class="flex flex-wrap gap-2">
        {#each service.trustNotes as note}
          <span class="rounded-full bg-slate-100 text-slate-700 px-3 py-1 text-xs font-semibold">{note}</span>
        {/each}
      </div>
    </article>
  </section>

  {#if data.relatedListings.length > 0}
    <section class="space-y-5">
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">Servicios relacionados</p>
        <h2 class="text-3xl font-bold text-gray-900">Más opciones dentro de la misma categoría</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        {#each data.relatedListings as listing}
          <a href={`/servicios/servicio/${listing.serviceSlug}`} class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition block">
            <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">{listing.category}</p>
            <h3 class="text-xl font-bold text-gray-900 mb-2">{listing.serviceName}</h3>
            <p class="text-sm text-gray-600 mb-4">{listing.workshopName}</p>
            <p class="text-sm text-gray-700">{formatPriceRange(listing.priceMin, listing.priceMax)}</p>
          </a>
        {/each}
      </div>
    </section>
  {/if}
</section>
