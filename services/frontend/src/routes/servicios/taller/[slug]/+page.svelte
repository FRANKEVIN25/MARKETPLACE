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
      label: 'Servicios publicados',
      value: `${workshop.services.length}`,
      description: 'Oferta activa visible para cliente final.',
    },
    {
      label: 'Demanda acumulada',
      value: `${workshop.totalJobs}`,
      description: 'Historial agregado para medir consistencia.',
    },
    {
      label: 'Rating más alto',
      value: `${(workshop.highestSuccessRate / 20).toFixed(1)}/5`,
      description: 'Mejor valoración observada en el catálogo publicado.',
    },
    {
      label: 'Experiencia',
      value: `${workshop.yearsExperience} años`,
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
  <title>{workshop.workshopName} | Plantilla de Taller | ECOMPARTS</title>
  <meta
    name="description"
    content={`Detalle de taller para ${workshop.workshopName}, con expertise por vehículo, catálogo y señales de confianza.`}
  />
</svelte:head>

<section class="bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 text-white">
  <div class="max-w-7xl mx-auto px-6 py-16 md:py-20 space-y-8">
    <div class="flex flex-wrap items-center gap-3 text-sm text-blue-100">
      <a href="/servicios" class="hover:text-white transition">Servicios</a>
      <span class="text-white/40">/</span>
      <a href="/servicios/resultados" class="hover:text-white transition">Resultados</a>
      <span class="text-white/40">/</span>
      <span>{workshop.workshopName}</span>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1.05fr,0.95fr] gap-10 items-start">
      <div class="space-y-7">
        <div class="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-blue-100">
          <span>Plantilla 3</span>
          <span class="text-white/40">•</span>
          <span>Perfil del taller</span>
        </div>

        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-200 mb-3">Ficha pro del taller</p>
          <h1 class="text-4xl md:text-5xl font-black leading-tight max-w-4xl">{workshop.workshopName}</h1>
          <p class="text-xl text-blue-100 mt-3 max-w-3xl">{workshop.workshopHeadline}</p>
          <p class="text-blue-100/80 mt-5 max-w-3xl leading-relaxed">
            La plantilla del taller consolida confianza real: experiencia por vehículo, catálogo activo, métricas de desempeño y señales operativas que ayudan al cliente a decidir sin depender de ratings vacíos.
          </p>
        </div>

        <div class="flex flex-wrap gap-3">
          <span class="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold">{workshop.district}</span>
          <span class="rounded-full bg-white/10 px-4 py-2 text-sm font-semibold">{serviceLevelLabels[workshop.serviceLevel]}</span>
          {#if workshop.verified}
            <span class="rounded-full bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-200">✔ Verificado</span>
          {/if}
          {#if workshop.erpIntegrated}
            <span class="rounded-full bg-indigo-500/15 px-4 py-2 text-sm font-semibold text-indigo-200">🧠 ERP integrado</span>
          {/if}
          {#if workshop.certified}
            <span class="rounded-full bg-blue-500/15 px-4 py-2 text-sm font-semibold text-blue-200">🏅 Certificado</span>
          {/if}
        </div>
      </div>

      <aside class="rounded-3xl bg-white text-slate-900 p-6 md:p-7 shadow-2xl">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">Snapshot del taller</p>
        <h2 class="text-2xl font-bold mb-3">KPIs visibles para el cliente</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
          {#each capabilityBlocks as item}
            <div class="rounded-2xl border border-gray-200 bg-slate-50 p-4">
              <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">{item.label}</p>
              <p class="text-2xl font-bold text-gray-900">{item.value}</p>
              <p class="text-sm text-gray-600 mt-1">{item.description}</p>
            </div>
          {/each}
        </div>

        <div class="rounded-2xl border border-gray-200 p-5">
          <p class="text-sm font-semibold text-gray-900 mb-2">Cobertura de precios</p>
          <p class="text-lg font-bold text-blue-700">{formatPriceRange(workshop.lowestPrice, workshop.highestPrice)}</p>
          <p class="text-sm text-gray-600 mt-2">Rating tope del catálogo: {(workshop.highestSuccessRate / 20).toFixed(1)}/5</p>
        </div>
      </aside>
    </div>
  </div>
</section>

<section class="max-w-7xl mx-auto px-6 py-16 space-y-10">
  {#if data.error}
    <div class="rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
      <h3 class="text-xl font-bold mb-2">No se pudo refrescar el perfil desde el backend</h3>
      <p class="text-sm">{data.error}</p>
    </div>
  {/if}

  <section class="grid grid-cols-1 lg:grid-cols-[1.02fr,0.98fr] gap-8">
    <article class="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
      <div class="flex items-center justify-between gap-4 mb-6">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">Servicios publicados</p>
          <h2 class="text-3xl font-bold text-gray-900">Catálogo activo del taller</h2>
        </div>
        <a href="/servicios/resultados" class="text-sm font-semibold text-blue-600 hover:text-blue-700">Volver a resultados</a>
      </div>

      <div class="space-y-4">
        {#each workshop.services as service}
          <article class="rounded-3xl border border-gray-200 p-6">
            <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-4">
              <div>
                <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-1">
                  {service.category} · {serviceTypeLabels[service.serviceType]}
                </p>
                <h3 class="text-2xl font-bold text-gray-900">{service.serviceName}</h3>
                <p class="text-gray-600 mt-2">{formatPriceRange(service.priceMin, service.priceMax)} · {formatDuration(service.durationMin)}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                {#if service.verified}
                  <span class="rounded-full bg-emerald-50 text-emerald-700 px-3 py-1 text-xs font-semibold">✔ Verificado</span>
                {/if}
                {#if service.specialized}
                  <span class="rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-semibold">🏆 Especializado</span>
                {/if}
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Demanda</p>
                <p class="font-bold text-gray-900">{service.totalJobs}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Rating</p>
                <p class="font-bold text-gray-900">{service.avgRating.toFixed(1)}/5</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Variación</p>
                <p class="font-bold text-gray-900">{service.repeatFailureRate.toFixed(1)}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-4">
                <p class="text-xs uppercase tracking-wide text-gray-500 mb-1">Vehículos</p>
                <p class="font-bold text-gray-900">{service.vehicleExpertise.length}</p>
              </div>
            </div>

            <div class="flex flex-wrap gap-2 mb-5">
              {#each service.trustNotes as note}
                <span class="rounded-full bg-slate-100 text-slate-700 px-3 py-1 text-xs font-semibold">{note}</span>
              {/each}
            </div>

            <a href={`/servicios/servicio/${service.serviceSlug}`} class="inline-flex rounded-xl bg-blue-600 text-white font-semibold px-5 py-3 hover:bg-blue-700 transition">
              Ver detalle del servicio
            </a>
          </article>
        {/each}
      </div>
    </article>

    <div class="space-y-8">
      <article class="rounded-3xl border border-gray-200 bg-slate-950 p-8 text-white shadow-sm">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-300 mb-3">Señales operativas</p>
        <h2 class="text-3xl font-bold mb-6">Cómo se comunica la confianza real</h2>
        <div class="space-y-3">
          {#each operatingSignals as signal}
            <div class="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4">
              <span class="text-emerald-300">✓</span>
              <p class="text-blue-100">{signal}</p>
            </div>
          {/each}
        </div>
      </article>

      <article class="rounded-3xl border border-gray-200 bg-white p-8 shadow-sm">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-3">Expertise vehicular</p>
        <h2 class="text-3xl font-bold text-gray-900 mb-6">Vehículos donde este taller tiene más tracción</h2>
        <div class="flex flex-wrap gap-3 mb-6">
          {#each workshop.vehicleExpertise as vehicle}
            <span class="rounded-full bg-blue-50 text-blue-700 px-4 py-2 text-sm font-semibold">{vehicle}</span>
          {/each}
        </div>
        <div class="rounded-2xl bg-slate-50 p-5 text-sm text-gray-700">
          <p>
            El detalle del taller debe reforzar que no solo publica servicios: también demuestra en qué combinaciones de marca/modelo ya tiene experiencia real.
          </p>
        </div>
      </article>
    </div>
  </section>

  {#if data.relatedListings.length > 0}
    <section class="space-y-5">
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600 mb-2">Siguiente navegación</p>
        <h2 class="text-3xl font-bold text-gray-900">Otros servicios para seguir explorando</h2>
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
