<script lang="ts">
  import type { PageData } from './$types';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import type { VehicleModelo } from '$lib/api/types';
  import {
    budgetMatches,
    budgetOptions,
    confidenceLabel,
    formatDuration,
    formatPriceRange,
    groupWorkshopAggregates,
    scoreListing,
    serviceLevelLabels,
    serviceTypeLabels,
    vehicleMatches,
  } from '$lib/data/service-showcase';
  import type { ServiceCategoryItem } from '$lib/api/types';

  export let data: PageData;

  type ViewMode = 'service' | 'workshop';
  type TrustFilter = 'all' | 'verified' | 'mostRequested' | 'topRated';

  const customer = auth.customer;

  const serviceListings = data.serviceListings ?? [];
  const serviceCategories = data.serviceCategories ?? [];

  // ── Vehículo (desde backend) ──────────────────────────────────────────────
  let marcas = data.marcas ?? [];
  let modelos: VehicleModelo[] = data.modelos ?? [];
  let loadingModelos = false;

  let selectedMarcaId: number | null = data.initialFilters?.marca_id ?? null;
  let selectedModeloId: number | null = data.initialFilters?.modelo_id ?? null;

  $: selectedMarca  = marcas.find((m) => m.id === selectedMarcaId);
  $: selectedModelo = modelos.find((m) => m.id === selectedModeloId);
  $: selectedBrandName = selectedMarca?.nombre  ?? '';
  $: selectedModelName = selectedModelo?.nombre ?? '';

  async function handleMarcaChange() {
    if (!selectedMarcaId) {
      selectedModeloId = null;
      modelos = [];
      return;
    }
    loadingModelos = true;
    selectedModeloId = null;
    modelos = [];
    modelos = await api.publicVehicles.modelos(selectedMarcaId);
    loadingModelos = false;
  }

  // ── Otros filtros ─────────────────────────────────────────────────────────
  let viewMode: ViewMode = 'service';
  let selectedBudget = 'all';
  let selectedTrust: TrustFilter = 'all';

  let selectedDepartment = data.initialFilters?.department || 'all';
  let selectedProvince   = data.initialFilters?.province   || 'all';
  let selectedDistrict   = data.initialFilters?.district   || 'all';

  // Categoría: inicializar por ID si viene del wizard, sino 'all'
  const _initCatId = data.initialFilters?.category_id ?? null;
  let selectedCategory: string = _initCatId
    ? (serviceCategories.find((c: ServiceCategoryItem) => c.id === _initCatId)?.name ?? 'all')
    : 'all';

  // Categoría seleccionada completa (para mostrar descripción)
  $: activeCategoryItem = serviceCategories.find(
    (c: ServiceCategoryItem) => c.name === selectedCategory
  ) ?? null;

  // Listas dinámicas para filtros de ubicación
  $: districts   = ['all', ...Array.from(new Set(serviceListings.map((l) => l.district)))];
  $: provinces   = ['all', ...Array.from(new Set(serviceListings.map((l) => l.province)))];
  $: departments = ['all', ...Array.from(new Set(serviceListings.map((l) => l.department)))];

  // Listings con score + filtros aplicados
  $: scoredListings = (() => {
    const withScore = serviceListings.map((listing) => ({
      ...listing,
      score: scoreListing(listing, {
        selectedCategory: selectedCategory !== 'all' ? selectedCategory : undefined,
        selectedBrand: selectedBrandName,
        selectedModel: selectedModelName,
        selectedDistrict,
        selectedProvince,
        selectedDepartment,
      }),
    }));

    // Filtro de confianza
    const trustPredicate = (l: typeof withScore[number]) => {
      if (selectedTrust === 'verified')      return l.verified;
      if (selectedTrust === 'mostRequested') return l.totalJobs >= 50;
      if (selectedTrust === 'topRated')      return l.avgRating >= 4;
      return true;
    };

    const base = withScore.filter((listing) =>
      (selectedCategory === 'all' || listing.category === selectedCategory) &&
      budgetMatches(listing, selectedBudget) &&
      (selectedBrandName
        ? vehicleMatches(listing, selectedBrandName, selectedModelName)
        : true) &&
      trustPredicate(listing)
    );

    // Filtro de ubicación con fallback: distrito → provincia → departamento
    let locationFiltered = base;
    if (selectedDistrict !== 'all') {
      const byDistrict = base.filter((l) => l.district.toLowerCase() === selectedDistrict.toLowerCase());
      if (byDistrict.length > 0) {
        locationFiltered = byDistrict;
      } else if (selectedProvince !== 'all') {
        locationFiltered = base.filter((l) => l.province.toLowerCase() === selectedProvince.toLowerCase());
      } else if (selectedDepartment !== 'all') {
        locationFiltered = base.filter((l) => l.department.toLowerCase() === selectedDepartment.toLowerCase());
      }
    } else if (selectedProvince !== 'all') {
      locationFiltered = base.filter((l) => l.province.toLowerCase() === selectedProvince.toLowerCase());
    } else if (selectedDepartment !== 'all') {
      locationFiltered = base.filter((l) => l.department.toLowerCase() === selectedDepartment.toLowerCase());
    }

    return locationFiltered.sort((a, b) => b.score - a.score);
  })();

  $: topRecommendations = scoredListings.slice(0, 3);
  $: workshopResults    = groupWorkshopAggregates(scoredListings);
  $: usingProvinceFallback = (() => {
    if (selectedDistrict === 'all') return false;
    const byDistrict = serviceListings.filter((l) => l.district.toLowerCase() === selectedDistrict.toLowerCase());
    return byDistrict.length === 0 && selectedProvince !== 'all';
  })();

  const trustOptions: { value: TrustFilter; label: string; icon: string }[] = [
    { value: 'all',           label: 'Todos',             icon: '🔍' },
    { value: 'verified',      label: 'Verificados',       icon: '✔'  },
    { value: 'mostRequested', label: 'Más solicitados',   icon: '🔥' },
    { value: 'topRated',      label: 'Mejor calificados', icon: '⭐' },
  ];
</script>

<svelte:head>
  <title>Servicios de taller | ECOMPARTS</title>
  <meta name="description" content="Encuentra talleres verificados para tu vehículo. Filtra por categoría, ubicación, presupuesto y criterios de confianza." />
</svelte:head>

<!-- ── LAYOUT PRINCIPAL: aside + contenido ── -->
<div class="max-w-7xl mx-auto px-4 sm:px-6 py-10 flex flex-col xl:flex-row gap-8 items-start">

  <!-- ══════════════════════════════════════
       ASIDE — FILTROS
  ══════════════════════════════════════ -->
  <aside class="w-full xl:w-72 shrink-0 space-y-6 xl:sticky xl:top-6">

    <!-- Categoría (reemplaza problema + categoría) -->
    <div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      <p class="text-xs font-bold uppercase tracking-widest text-gray-500">Categoría</p>

      <div class="space-y-1">
        <label class="block">
          <select
            bind:value={selectedCategory}
            class="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todas las categorías</option>
            {#each serviceCategories as cat}
              <option value={cat.name}>{cat.name}</option>
            {/each}
          </select>
        </label>
      </div>

      <!-- Descripción de la categoría activa (síntomas / problemas) -->
      {#if activeCategoryItem?.description}
        <div class="rounded-xl bg-blue-50 border border-blue-100 px-3 py-2.5 text-xs text-blue-800 leading-relaxed">
          {activeCategoryItem.description}
        </div>
      {/if}
    </div>

    <!-- Vehículo -->
    <div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      <p class="text-xs font-bold uppercase tracking-widest text-gray-500">Vehículo</p>

      <label class="block">
        <span class="block text-xs font-medium text-gray-600 mb-1">Marca</span>
        <select
          bind:value={selectedMarcaId}
          onchange={handleMarcaChange}
          class="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={null}>Todas las marcas</option>
          {#each marcas as marca (marca.id)}
            <option value={marca.id}>{marca.nombre}</option>
          {/each}
        </select>
      </label>

      <label class="block">
        <span class="block text-xs font-medium text-gray-600 mb-1">Modelo</span>
        <select
          bind:value={selectedModeloId}
          disabled={!selectedMarcaId || loadingModelos || modelos.length === 0}
          class="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {#if !selectedMarcaId}
            <option value={null}>Todos los modelos</option>
          {:else if loadingModelos}
            <option value={null}>Cargando...</option>
          {:else if modelos.length === 0}
            <option value={null}>Sin modelos</option>
          {:else}
            <option value={null}>Todos los modelos</option>
            {#each modelos as modelo (modelo.id)}
              <option value={modelo.id}>{modelo.nombre}</option>
            {/each}
          {/if}
        </select>
      </label>
    </div>

    <!-- Presupuesto -->
    <div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      <p class="text-xs font-bold uppercase tracking-widest text-gray-500">Presupuesto</p>
      <div class="space-y-1">
        {#each budgetOptions as option}
          <button
            type="button"
            onclick={() => (selectedBudget = option.value)}
            class={`w-full text-left rounded-xl px-3 py-2.5 text-sm font-medium transition
              ${selectedBudget === option.value
                ? 'bg-slate-900 text-white'
                : 'text-gray-700 hover:bg-gray-50'}`}
          >
            {option.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- Confianza -->
    <div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      <p class="text-xs font-bold uppercase tracking-widest text-gray-500">Confianza</p>
      <div class="space-y-1">
        {#each trustOptions as opt}
          <button
            type="button"
            onclick={() => (selectedTrust = opt.value)}
            class={`w-full text-left rounded-xl px-3 py-2.5 text-sm font-medium transition flex items-center gap-2
              ${selectedTrust === opt.value
                ? 'bg-emerald-600 text-white'
                : 'text-gray-700 hover:bg-gray-50'}`}
          >
            <span>{opt.icon}</span>
            {opt.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- Ubicación -->
    <div class="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-4">
      <p class="text-xs font-bold uppercase tracking-widest text-gray-500">Ubicación</p>

      <!-- Departamento -->
      <div>
        <span class="block text-xs font-medium text-gray-600 mb-2">Departamento</span>
        <div class="flex flex-wrap gap-1.5">
          {#each departments as dept}
            <button
              type="button"
              onclick={() => { selectedDepartment = dept; selectedProvince = 'all'; selectedDistrict = 'all'; }}
              class={`rounded-full px-3 py-1.5 text-xs font-medium border transition
                ${selectedDepartment === dept
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              {dept === 'all' ? 'Todos' : dept}
            </button>
          {/each}
        </div>
      </div>

      <!-- Provincia (solo si hay más de una) -->
      {#if provinces.length > 1}
        <div>
          <span class="block text-xs font-medium text-gray-600 mb-2">Provincia</span>
          <div class="flex flex-wrap gap-1.5">
            {#each provinces as prov}
              {#if selectedDepartment === 'all' || serviceListings.some((l) => l.department === selectedDepartment && l.province === prov) || prov === 'all'}
                <button
                  type="button"
                  onclick={() => { selectedProvince = prov; selectedDistrict = 'all'; }}
                  class={`rounded-full px-3 py-1.5 text-xs font-medium border transition
                    ${selectedProvince === prov
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
                >
                  {prov === 'all' ? 'Todas' : prov}
                </button>
              {/if}
            {/each}
          </div>
        </div>
      {/if}

      <!-- Distrito -->
      <div>
        <span class="block text-xs font-medium text-gray-600 mb-2">Distrito</span>
        <div class="flex flex-wrap gap-1.5">
          {#each districts as district}
            <button
              type="button"
              onclick={() => (selectedDistrict = district)}
              class={`rounded-full px-3 py-1.5 text-xs font-medium border transition
                ${selectedDistrict === district
                  ? 'bg-emerald-600 text-white border-emerald-600'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
            >
              {district === 'all' ? 'Todos' : district}
            </button>
          {/each}
        </div>
      </div>

      {#if usingProvinceFallback}
        <div class="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          Sin resultados en <strong>{selectedDistrict}</strong>. Mostrando talleres en la provincia <strong>{selectedProvince}</strong>.
        </div>
      {/if}
    </div>

  </aside>

  <!-- ══════════════════════════════════════
       CONTENIDO PRINCIPAL
  ══════════════════════════════════════ -->
  <main class="flex-1 min-w-0 space-y-10">

    <!-- Aviso de error -->
    {#if data.error}
      <div class="rounded-3xl border border-amber-200 bg-amber-50 p-6 text-amber-900">
        <h3 class="text-xl font-bold mb-2">No se pudo leer el backend en este momento</h3>
        <p class="text-sm">{data.error}</p>
      </div>
    {/if}

    <!-- Encabezado + toggle de vista -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      <div>
        <h2 class="text-2xl md:text-3xl font-bold text-gray-900">
          {selectedCategory === 'all' ? 'Todos los servicios' : selectedCategory}
        </h2>
        {#if activeCategoryItem?.description}
          <p class="text-sm text-gray-500 mt-1 max-w-lg">{activeCategoryItem.description}</p>
        {:else}
          <p class="text-sm text-gray-500 mt-1">
            {scoredListings.length} resultado{scoredListings.length !== 1 ? 's' : ''}{selectedBrandName ? ` para ${selectedBrandName}${selectedModelName ? ' ' + selectedModelName : ''}` : ''}
          </p>
        {/if}
      </div>

      <div class="inline-flex rounded-2xl border border-gray-200 bg-white p-1 shadow-sm shrink-0">
        <button
          type="button"
          onclick={() => (viewMode = 'service')}
          class={`rounded-xl px-4 py-2 text-sm font-semibold transition
            ${viewMode === 'service' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
        >
          Por servicio
        </button>
        <button
          type="button"
          onclick={() => (viewMode = 'workshop')}
          class={`rounded-xl px-4 py-2 text-sm font-semibold transition
            ${viewMode === 'workshop' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
        >
          Por taller
        </button>
      </div>
    </div>

    <!-- ── RECOMENDACIONES PRINCIPALES ── -->
    {#if topRecommendations.length > 0}
      <section class="space-y-4">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="text-xs font-bold uppercase tracking-widest text-emerald-600">Recomendaciones principales</p>
            <h3 class="text-xl font-bold text-gray-900">Mejor match para {selectedBrandName} {selectedModelName}</h3>
          </div>
          <a href="/servicios" class="text-sm font-semibold text-blue-600 hover:text-blue-700 shrink-0">
            Cambiar búsqueda
          </a>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {#each topRecommendations as rec}
            <article class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition">
              <div class="flex items-start justify-between gap-3 mb-4">
                <div>
                  <p class="text-xs font-semibold text-blue-600 uppercase tracking-wide">{rec.category}</p>
                  <h4 class="text-lg font-bold text-gray-900 mt-1">{rec.serviceName}</h4>
                </div>
                <span class="rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold px-3 py-1.5 shrink-0">
                  {confidenceLabel(rec.score)}
                </span>
              </div>

              <p class="font-semibold text-gray-800 mb-0.5">{rec.workshopName}</p>
              <p class="text-xs text-gray-500 mb-4">{rec.workshopHeadline}</p>

              <div class="grid grid-cols-2 gap-3 mb-4">
                <div class="rounded-2xl bg-slate-50 p-3">
                  <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Confianza</p>
                  <p class="font-bold text-gray-900">{rec.avgRating.toFixed(1)}/5 rating</p>
                  <p class="text-xs text-gray-500 mt-0.5">{rec.totalJobs} solicitudes</p>
                </div>
                <div class="rounded-2xl bg-slate-50 p-3">
                  <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Estimación</p>
                  <p class="font-bold text-gray-900">{formatPriceRange(rec.priceMin, rec.priceMax)}</p>
                  <p class="text-xs text-gray-500 mt-0.5">{formatDuration(rec.durationMin)}</p>
                </div>
              </div>

              <div class="space-y-1.5 text-sm text-gray-700 mb-4">
                <div class="flex items-center gap-2">
                  <span class="text-emerald-600">✔</span>
                  <span>{rec.avgRating.toFixed(1)}/5 valoración promedio</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-emerald-600">✔</span>
                  <span>Expertise: {rec.vehicleExpertise.slice(0, 2).join(' · ')}</span>
                </div>
                <div class="flex items-center gap-2">
                  <span class="text-emerald-600">✔</span>
                  <span>{serviceLevelLabels[rec.serviceLevel]} {rec.erpIntegrated ? '· ERP' : ''}</span>
                </div>
              </div>

              <div class="flex flex-wrap gap-1.5 mb-4">
                {#each rec.trustNotes as note}
                  <span class="rounded-full bg-blue-50 text-blue-700 px-3 py-1 text-xs font-semibold">{note}</span>
                {/each}
              </div>

              <div class="flex gap-2">
                <a href={`/servicios/servicio/${rec.serviceSlug}`} class="flex-1 rounded-xl bg-blue-600 text-white text-center font-semibold px-4 py-2.5 text-sm hover:bg-blue-700 transition">
                  Ver servicio
                </a>
                <a href={`/servicios/taller/${rec.workshopSlug}`} class="rounded-xl border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
                  Taller
                </a>
              </div>
            </article>
          {/each}
        </div>
      </section>
    {/if}

    <!-- ── LISTA COMPLETA ── -->
    {#if viewMode === 'service'}
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {#each scoredListings as listing}
          <article class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition">
            <div class="flex items-start justify-between gap-4 mb-4">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-blue-600 mb-1">
                  {listing.category} · {serviceTypeLabels[listing.serviceType]}
                </p>
                <h3 class="text-xl font-bold text-gray-900">{listing.serviceName}</h3>
              </div>
              <div class="text-right shrink-0">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Score</p>
                <p class="text-xl font-bold text-gray-900">{listing.score}</p>
              </div>
            </div>

            <div class="rounded-2xl bg-slate-50 p-4 mb-5">
              <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div>
                  <p class="font-semibold text-gray-900">{listing.workshopName}</p>
                  <p class="text-sm text-gray-600">{listing.workshopHeadline}</p>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  {#if listing.verified}
                    <span class="rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-1 text-xs font-semibold">✔ Verificado</span>
                  {/if}
                  {#if listing.specialized}
                    <span class="rounded-full bg-blue-50 text-blue-700 px-2.5 py-1 text-xs font-semibold">🏆 Especializado</span>
                  {/if}
                  {#if listing.erpIntegrated}
                    <span class="rounded-full bg-indigo-50 text-indigo-700 px-2.5 py-1 text-xs font-semibold">🧠 ERP</span>
                  {/if}
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
              <div class="rounded-2xl border border-gray-200 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Precio</p>
                <p class="font-bold text-gray-900 text-sm">{formatPriceRange(listing.priceMin, listing.priceMax)}</p>
              </div>
              <div class="rounded-2xl border border-gray-200 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Tiempo</p>
                <p class="font-bold text-gray-900 text-sm">{formatDuration(listing.durationMin)}</p>
              </div>
              <div class="rounded-2xl border border-gray-200 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Confianza</p>
                <p class="font-bold text-gray-900 text-sm">{listing.avgRating.toFixed(1)}/5</p>
              </div>
              <div class="rounded-2xl border border-gray-200 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Demanda</p>
                <p class="font-bold text-gray-900 text-sm">{listing.totalJobs} solicitudes</p>
              </div>
            </div>

            <div class="space-y-1.5 text-sm text-gray-700 mb-4">
              <p><span class="font-semibold text-gray-900">Vehículos:</span> {listing.vehicleExpertise.join(' · ')}</p>
              <p><span class="font-semibold text-gray-900">Ubicación:</span> {listing.district}</p>
              <p><span class="font-semibold text-gray-900">Valoración:</span> {listing.avgRating.toFixed(1)}/5</p>
            </div>

            <div class="flex flex-wrap gap-1.5 mb-5">
              {#each listing.trustNotes as note}
                <span class="rounded-full bg-slate-100 text-slate-700 px-2.5 py-1 text-xs font-semibold">{note}</span>
              {/each}
            </div>

            <div class="flex gap-3">
              <a href={`/servicios/servicio/${listing.serviceSlug}`} class="flex-1 rounded-xl bg-slate-900 text-white text-center font-semibold px-4 py-3 hover:bg-slate-800 transition text-sm">
                Ver servicio
              </a>
              <a href={`/servicios/taller/${listing.workshopSlug}`} class="rounded-xl border border-gray-300 px-4 py-3 font-semibold text-gray-700 hover:bg-gray-50 transition text-sm">
                Ver taller
              </a>
            </div>
          </article>
        {/each}
      </section>

    {:else}
      <!-- Vista por taller -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {#each workshopResults as workshop}
          <article class="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm hover:shadow-md transition">
            <div class="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 class="text-xl font-bold text-gray-900">{workshop.workshopName}</h3>
                <p class="text-gray-600 mt-0.5 text-sm">{workshop.workshopHeadline}</p>
              </div>
              <div class="flex flex-col items-end gap-1.5">
                {#if workshop.verified}
                  <span class="rounded-full bg-emerald-50 text-emerald-700 px-2.5 py-1 text-xs font-semibold">✔ Verificado</span>
                {/if}
                {#if workshop.erpIntegrated}
                  <span class="rounded-full bg-indigo-50 text-indigo-700 px-2.5 py-1 text-xs font-semibold">🧠 ERP</span>
                {/if}
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
              <div class="rounded-2xl bg-slate-50 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Desde</p>
                <p class="font-bold text-gray-900 text-sm">{formatPriceRange(workshop.lowestPrice, workshop.highestPrice)}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Rating máx.</p>
                <p class="font-bold text-gray-900 text-sm">{(workshop.highestSuccessRate / 20).toFixed(1)}/5</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Demanda</p>
                <p class="font-bold text-gray-900 text-sm">{workshop.totalJobs}</p>
              </div>
              <div class="rounded-2xl bg-slate-50 p-3">
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-1">Perfil</p>
                <p class="font-bold text-gray-900 text-sm">{serviceLevelLabels[workshop.serviceLevel]}</p>
              </div>
            </div>

            <div class="space-y-3 mb-5">
              <div>
                <p class="text-sm font-semibold text-gray-900 mb-2">Servicios destacados</p>
                <div class="flex flex-wrap gap-1.5">
                  {#each workshop.featuredServices as service}
                    <span class="rounded-full bg-blue-50 text-blue-700 px-2.5 py-1 text-xs font-semibold">{service}</span>
                  {/each}
                </div>
              </div>
              <div>
                <p class="text-sm font-semibold text-gray-900 mb-2">Expertise vehicular</p>
                <div class="flex flex-wrap gap-1.5">
                  {#each workshop.vehicleExpertise as vehicle}
                    <span class="rounded-full bg-slate-100 text-slate-700 px-2.5 py-1 text-xs font-semibold">{vehicle}</span>
                  {/each}
                </div>
              </div>
            </div>

            <div class="flex items-center justify-between gap-4 pt-4 border-t border-gray-100">
              <div class="text-sm text-gray-600">
                <p><span class="font-semibold text-gray-900">Distrito:</span> {workshop.district}</p>
                <p><span class="font-semibold text-gray-900">Experiencia:</span> {workshop.yearsExperience} años</p>
              </div>
              <a href={`/servicios/taller/${workshop.workshopSlug}`} class="rounded-xl bg-blue-600 text-white font-semibold px-5 py-3 text-sm hover:bg-blue-700 transition">
                Ver perfil
              </a>
            </div>
          </article>
        {/each}
      </section>
    {/if}

    <!-- Sin resultados -->
    {#if scoredListings.length === 0}
      <div class="rounded-3xl border border-amber-200 bg-amber-50 p-8 text-amber-900">
        <h3 class="text-2xl font-bold mb-2">No encontramos coincidencias exactas</h3>
        <p class="text-sm">
          Prueba ampliar el presupuesto, cambiar la categoría o desactivar el filtro de confianza. Solo se muestran resultados reales publicados por el backend.
        </p>
      </div>
    {/if}

    <!-- Footer CTA -->
    <div class="rounded-3xl border border-gray-200 bg-slate-950 p-8 text-white shadow-sm">
      <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-300 mb-2">Plantillas conectadas</p>
          <h2 class="text-2xl font-bold">Desde aquí ya puedes entrar al detalle del taller o del servicio</h2>
        </div>
        <div class="flex flex-wrap gap-3">
          <a href="/servicios" class="rounded-2xl border border-white/20 px-5 py-3 text-sm font-semibold hover:bg-white/10 transition">
            Nueva búsqueda
          </a>
          <a href="/servicios" class="rounded-2xl bg-white text-slate-900 px-5 py-3 text-sm font-semibold hover:bg-blue-50 transition">
            Volver al overview
          </a>
        </div>
      </div>
    </div>

  </main>
</div>