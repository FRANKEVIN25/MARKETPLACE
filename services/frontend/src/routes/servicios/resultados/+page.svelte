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

  const _initCatId = data.initialFilters?.category_id ?? null;
  let selectedCategory: string = _initCatId
    ? (serviceCategories.find((c: ServiceCategoryItem) => c.id === _initCatId)?.name ?? 'all')
    : 'all';

  $: activeCategoryItem = serviceCategories.find(
    (c: ServiceCategoryItem) => c.name === selectedCategory
  ) ?? null;

  $: districts   = ['all', ...Array.from(new Set(serviceListings.map((l) => l.district)))];
  $: provinces   = ['all', ...Array.from(new Set(serviceListings.map((l) => l.province)))];
  $: departments = ['all', ...Array.from(new Set(serviceListings.map((l) => l.department)))];

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

  const trustOptions: { value: TrustFilter; label: string }[] = [
    { value: 'all',           label: 'TODOS' },
    { value: 'verified',      label: 'VERIFICADOS' },
    { value: 'mostRequested', label: 'MÁS SOLICITADOS' },
    { value: 'topRated',      label: 'MEJOR CALIFICADOS' },
  ];
</script>

<svelte:head>
  <title>Servicios de taller | ECOMPARTS</title>
  <meta name="description" content="Encuentra talleres verificados para tu vehículo. Filtra por categoría, ubicación, presupuesto y criterios de confianza." />
</svelte:head>

<div class="container-responsive py-8 flex flex-col xl:flex-row gap-8 items-start">

  <!-- ══════════════════════════════════════
       ASIDE — FILTROS
  ══════════════════════════════════════ -->
  <aside class="w-full xl:w-64 shrink-0 space-y-4 xl:sticky xl:top-6">

    <!-- Categoría -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-4 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// CATEGORÍA</p>
      </div>
      <div class="p-4 space-y-3">
        <select
          bind:value={selectedCategory}
          class="input-industrial text-xs"
        >
          <option value="all">TODAS LAS CATEGORÍAS</option>
          {#each serviceCategories as cat}
            <option value={cat.name}>{cat.name.toUpperCase()}</option>
          {/each}
        </select>
        {#if activeCategoryItem?.description}
          <div class="border border-steel-600/20 bg-iron-800/50 px-3 py-2">
            <p class="font-mono text-[10px] text-steel-400 leading-relaxed">{activeCategoryItem.description}</p>
          </div>
        {/if}
      </div>
    </div>

    <!-- Vehículo -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-4 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// VEHÍCULO</p>
      </div>
      <div class="p-4 space-y-3">
        <div>
          <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">MARCA</label>
          <select
            bind:value={selectedMarcaId}
            onchange={handleMarcaChange}
            class="input-industrial text-xs"
          >
            <option value={null}>TODAS LAS MARCAS</option>
            {#each marcas as marca (marca.id)}
              <option value={marca.id}>{marca.nombre.toUpperCase()}</option>
            {/each}
          </select>
        </div>
        <div>
          <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">MODELO</label>
          <select
            bind:value={selectedModeloId}
            disabled={!selectedMarcaId || loadingModelos || modelos.length === 0}
            class="input-industrial text-xs disabled:opacity-50"
          >
            {#if !selectedMarcaId}
              <option value={null}>TODOS LOS MODELOS</option>
            {:else if loadingModelos}
              <option value={null}>CARGANDO...</option>
            {:else if modelos.length === 0}
              <option value={null}>SIN MODELOS</option>
            {:else}
              <option value={null}>TODOS LOS MODELOS</option>
              {#each modelos as modelo (modelo.id)}
                <option value={modelo.id}>{modelo.nombre.toUpperCase()}</option>
              {/each}
            {/if}
          </select>
        </div>
      </div>
    </div>

    <!-- Presupuesto -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-4 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PRESUPUESTO</p>
      </div>
      <div class="p-3 space-y-1">
        {#each budgetOptions as option}
          <button
            type="button"
            on:click={() => (selectedBudget = option.value)}
            class="w-full text-left px-3 py-2 font-mono text-[10px] uppercase tracking-widest transition-colors
              {selectedBudget === option.value
                ? 'bg-rust-600/20 border border-rust-600/60 text-rust-400'
                : 'border border-transparent text-steel-500 hover:text-bone hover:border-steel-600/40'}"
          >
            {option.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- Confianza -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-4 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// CONFIANZA</p>
      </div>
      <div class="p-3 space-y-1">
        {#each trustOptions as opt}
          <button
            type="button"
            on:click={() => (selectedTrust = opt.value)}
            class="w-full text-left px-3 py-2 font-mono text-[10px] uppercase tracking-widest transition-colors
              {selectedTrust === opt.value
                ? 'bg-rust-600/20 border border-rust-600/60 text-rust-400'
                : 'border border-transparent text-steel-500 hover:text-bone hover:border-steel-600/40'}"
          >
            {opt.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- Ubicación -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-4 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// UBICACIÓN</p>
      </div>
      <div class="p-4 space-y-4">

        <!-- Departamento -->
        <div>
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">DEPARTAMENTO</p>
          <div class="flex flex-wrap gap-1.5">
            {#each departments as dept}
              <button
                type="button"
                on:click={() => { selectedDepartment = dept; selectedProvince = 'all'; selectedDistrict = 'all'; }}
                class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border transition-colors
                  {selectedDepartment === dept
                    ? 'border-rust-600 text-rust-400 bg-rust-600/10'
                    : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
              >
                {dept === 'all' ? 'TODOS' : dept.toUpperCase()}
              </button>
            {/each}
          </div>
        </div>

        <!-- Provincia -->
        {#if provinces.length > 1}
          <div>
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">PROVINCIA</p>
            <div class="flex flex-wrap gap-1.5">
              {#each provinces as prov}
                {#if selectedDepartment === 'all' || serviceListings.some((l) => l.department === selectedDepartment && l.province === prov) || prov === 'all'}
                  <button
                    type="button"
                    on:click={() => { selectedProvince = prov; selectedDistrict = 'all'; }}
                    class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border transition-colors
                      {selectedProvince === prov
                        ? 'border-rust-600 text-rust-400 bg-rust-600/10'
                        : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                  >
                    {prov === 'all' ? 'TODAS' : prov.toUpperCase()}
                  </button>
                {/if}
              {/each}
            </div>
          </div>
        {/if}

        <!-- Distrito -->
        <div>
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">DISTRITO</p>
          <div class="flex flex-wrap gap-1.5">
            {#each districts as district}
              <button
                type="button"
                on:click={() => (selectedDistrict = district)}
                class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border transition-colors
                  {selectedDistrict === district
                    ? 'border-rust-600 text-rust-400 bg-rust-600/10'
                    : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
              >
                {district === 'all' ? 'TODOS' : district.toUpperCase()}
              </button>
            {/each}
          </div>
        </div>

        {#if usingProvinceFallback}
          <div class="border border-yellow-700/50 bg-yellow-600/10 px-3 py-2">
            <p class="font-mono text-[10px] text-yellow-400 leading-relaxed">
              SIN RESULTADOS EN {selectedDistrict.toUpperCase()}. MOSTRANDO TALLERES EN {selectedProvince.toUpperCase()}.
            </p>
          </div>
        {/if}
      </div>
    </div>

  </aside>

  <!-- ══════════════════════════════════════
       CONTENIDO PRINCIPAL
  ══════════════════════════════════════ -->
  <main class="flex-1 min-w-0 space-y-8">

    <!-- Error -->
    {#if data.error}
      <div class="border border-rust-700/50 bg-rust-600/10 p-5 flex items-start gap-3">
        <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
        <div>
          <p class="font-mono text-xs text-rust-400 uppercase tracking-widest mb-1">ERROR AL CARGAR DATOS</p>
          <p class="font-mono text-xs text-steel-400">{data.error}</p>
        </div>
      </div>
    {/if}

    <!-- Encabezado + toggle de vista -->
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 border-b border-steel-600/25 pb-5">
      <div>
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// SERVICIOS / RESULTADOS</p>
        <h2 class="font-display text-4xl text-bone uppercase leading-none">
          {selectedCategory === 'all' ? 'TODOS LOS SERVICIOS' : selectedCategory.toUpperCase()}
        </h2>
        {#if activeCategoryItem?.description}
          <p class="font-mono text-xs text-steel-500 mt-2 max-w-lg">{activeCategoryItem.description}</p>
        {:else}
          <p class="font-mono text-xs text-steel-500 mt-2">
            {scoredListings.length} RESULTADO{scoredListings.length !== 1 ? 'S' : ''}
            {selectedBrandName ? ` PARA ${selectedBrandName.toUpperCase()}${selectedModelName ? ' ' + selectedModelName.toUpperCase() : ''}` : ''}
          </p>
        {/if}
      </div>

      <!-- Toggle vista -->
      <div class="inline-flex border border-steel-600/40 shrink-0">
        <button
          type="button"
          on:click={() => (viewMode = 'service')}
          class="px-4 py-2 font-mono text-[10px] uppercase tracking-widest transition-colors
            {viewMode === 'service'
              ? 'bg-rust-600/20 text-rust-400 border-r border-rust-600/60'
              : 'text-steel-500 hover:text-bone border-r border-steel-600/40'}"
        >
          POR SERVICIO
        </button>
        <button
          type="button"
          on:click={() => (viewMode = 'workshop')}
          class="px-4 py-2 font-mono text-[10px] uppercase tracking-widest transition-colors
            {viewMode === 'workshop'
              ? 'bg-rust-600/20 text-rust-400'
              : 'text-steel-500 hover:text-bone'}"
        >
          POR TALLER
        </button>
      </div>
    </div>

    <!-- ── RECOMENDACIONES PRINCIPALES ── -->
    {#if topRecommendations.length > 0}
      <section class="space-y-4">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// RECOMENDACIONES PRINCIPALES</p>
            <h3 class="font-display text-2xl text-bone uppercase leading-none">
              MEJOR MATCH PARA {selectedBrandName ? `${selectedBrandName.toUpperCase()} ${selectedModelName.toUpperCase()}` : 'TU BÚSQUEDA'}
            </h3>
          </div>
          <a href="/servicios" class="btn-ghost font-mono text-[10px] uppercase tracking-widest shrink-0">
            CAMBIAR BÚSQUEDA
          </a>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {#each topRecommendations as rec}
            <div class="bg-iron-900 border border-steel-600/25 hover:border-rust-600/50 transition-colors"
                 style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
              <div class="border-b border-steel-600/25 px-5 py-3 flex items-start justify-between gap-2">
                <div>
                  <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest">{rec.category}</p>
                  <h4 class="font-display text-xl text-bone uppercase leading-none">{rec.serviceName}</h4>
                </div>
                <span class="font-mono text-[9px] uppercase tracking-widest border border-green-700/50 text-green-400 px-2 py-0.5 flex-shrink-0">
                  {confidenceLabel(rec.score)}
                </span>
              </div>
              <div class="p-5">
                <p class="font-mono text-xs text-bone mb-0.5">{rec.workshopName}</p>
                <p class="font-mono text-[10px] text-steel-500 mb-4">{rec.workshopHeadline}</p>

                <div class="grid grid-cols-2 gap-2 mb-4">
                  <div class="bg-iron-800/50 border border-steel-600/20 p-3">
                    <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CONFIANZA</p>
                    <p class="font-mono text-xs text-bone">{rec.avgRating.toFixed(1)}/5</p>
                    <p class="font-mono text-[9px] text-steel-600">{rec.totalJobs} SOLICITUDES</p>
                  </div>
                  <div class="bg-iron-800/50 border border-steel-600/20 p-3">
                    <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ESTIMACIÓN</p>
                    <p class="font-mono text-xs text-bone">{formatPriceRange(rec.priceMin, rec.priceMax)}</p>
                    <p class="font-mono text-[9px] text-steel-600">{formatDuration(rec.durationMin)}</p>
                  </div>
                </div>

                <div class="space-y-1 mb-4">
                  {#each [
                    `${rec.avgRating.toFixed(1)}/5 VALORACIÓN PROMEDIO`,
                    `EXPERTISE: ${rec.vehicleExpertise.slice(0, 2).join(' · ')}`,
                    `${serviceLevelLabels[rec.serviceLevel]}${rec.erpIntegrated ? ' · ERP' : ''}`,
                  ] as signal}
                    <div class="flex items-center gap-2">
                      <span class="text-green-400 font-mono text-xs">✓</span>
                      <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest">{signal}</span>
                    </div>
                  {/each}
                </div>

                {#if rec.trustNotes.length > 0}
                  <div class="flex flex-wrap gap-1.5 mb-4">
                    {#each rec.trustNotes as note}
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-500 px-2 py-0.5">{note}</span>
                    {/each}
                  </div>
                {/if}

                <div class="flex gap-2">
                  <a href={`/servicios/servicio/${rec.serviceSlug}`} class="btn-rust flex-1 text-center text-xs">VER SERVICIO</a>
                  <a href={`/servicios/taller/${rec.workshopSlug}`} class="btn-outline text-xs">TALLER</a>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- ── LISTA COMPLETA ── -->
    {#if viewMode === 'service'}
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {#each scoredListings as listing}
          <div class="bg-iron-900 border border-steel-600/25 hover:border-steel-600/50 transition-colors"
               style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">

            <div class="border-b border-steel-600/25 px-5 py-3 flex items-start justify-between gap-3">
              <div>
                <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-1">
                  {listing.category} · {serviceTypeLabels[listing.serviceType]}
                </p>
                <h3 class="font-display text-2xl text-bone uppercase leading-none">{listing.serviceName}</h3>
              </div>
              <div class="text-right flex-shrink-0">
                <p class="font-mono text-[9px] text-steel-600 uppercase">SCORE</p>
                <p class="font-display text-2xl text-rust-600 leading-none">{listing.score}</p>
              </div>
            </div>

            <div class="border-b border-steel-600/20 px-5 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-iron-800/30">
              <div>
                <p class="font-mono text-xs text-bone">{listing.workshopName}</p>
                <p class="font-mono text-[10px] text-steel-500">{listing.workshopHeadline}</p>
              </div>
              <div class="flex flex-wrap gap-1.5">
                {#if listing.verified}
                  <span class="font-mono text-[9px] uppercase border border-green-700/50 text-green-400 px-2 py-0.5">✓ VERIF.</span>
                {/if}
                {#if listing.specialized}
                  <span class="font-mono text-[9px] uppercase border border-rust-700/50 text-rust-500 px-2 py-0.5">★ ESPEC.</span>
                {/if}
                {#if listing.erpIntegrated}
                  <span class="font-mono text-[9px] uppercase border border-steel-600/40 text-steel-400 px-2 py-0.5">ERP</span>
                {/if}
              </div>
            </div>

            <div class="px-5 py-4">
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
                {#each [
                  { label: 'PRECIO',   value: formatPriceRange(listing.priceMin, listing.priceMax) },
                  { label: 'TIEMPO',   value: formatDuration(listing.durationMin) },
                  { label: 'CONFIANZA',value: `${listing.avgRating.toFixed(1)}/5` },
                  { label: 'DEMANDA',  value: `${listing.totalJobs}` },
                ] as kpi}
                  <div class="bg-iron-800/50 border border-steel-600/20 p-3">
                    <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{kpi.label}</p>
                    <p class="font-mono text-xs text-bone">{kpi.value}</p>
                  </div>
                {/each}
              </div>

              <div class="space-y-0.5 mb-3">
                <p class="font-mono text-[10px] text-steel-500 uppercase">VEHÍCULOS: {listing.vehicleExpertise.join(' · ')}</p>
                <p class="font-mono text-[10px] text-steel-500 uppercase">UBICACIÓN: {listing.district.toUpperCase()}</p>
              </div>

              {#if listing.trustNotes.length > 0}
                <div class="flex flex-wrap gap-1.5 mb-4">
                  {#each listing.trustNotes as note}
                    <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-500 px-2 py-0.5">{note}</span>
                  {/each}
                </div>
              {/if}

              <div class="flex gap-3">
                <a href={`/servicios/servicio/${listing.serviceSlug}`} class="btn-rust flex-1 text-center text-xs">VER SERVICIO</a>
                <a href={`/servicios/taller/${listing.workshopSlug}`} class="btn-outline text-xs">VER TALLER</a>
              </div>
            </div>
          </div>
        {/each}
      </section>

    {:else}
      <!-- Vista por taller -->
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {#each workshopResults as workshop}
          <div class="bg-iron-900 border border-steel-600/25 hover:border-steel-600/50 transition-colors"
               style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">

            <div class="border-b border-steel-600/25 px-5 py-3 flex items-start justify-between gap-3">
              <div>
                <h3 class="font-display text-2xl text-bone uppercase leading-none">{workshop.workshopName}</h3>
                <p class="font-mono text-[10px] text-steel-500">{workshop.workshopHeadline}</p>
              </div>
              <div class="flex flex-col items-end gap-1.5">
                {#if workshop.verified}
                  <span class="font-mono text-[9px] uppercase border border-green-700/50 text-green-400 px-2 py-0.5">✓ VERIF.</span>
                {/if}
                {#if workshop.erpIntegrated}
                  <span class="font-mono text-[9px] uppercase border border-steel-600/40 text-steel-400 px-2 py-0.5">ERP</span>
                {/if}
              </div>
            </div>

            <div class="px-5 py-4">
              <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 mb-4">
                {#each [
                  { label: 'DESDE',      value: formatPriceRange(workshop.lowestPrice, workshop.highestPrice) },
                  { label: 'RATING MÁX.', value: `${(workshop.highestSuccessRate / 20).toFixed(1)}/5` },
                  { label: 'DEMANDA',    value: `${workshop.totalJobs}` },
                  { label: 'PERFIL',     value: serviceLevelLabels[workshop.serviceLevel] },
                ] as kpi}
                  <div class="bg-iron-800/50 border border-steel-600/20 p-3">
                    <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{kpi.label}</p>
                    <p class="font-mono text-xs text-bone">{kpi.value}</p>
                  </div>
                {/each}
              </div>

              <div class="space-y-3 mb-4">
                <div>
                  <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">SERVICIOS DESTACADOS</p>
                  <div class="flex flex-wrap gap-1.5">
                    {#each workshop.featuredServices as service}
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">{service}</span>
                    {/each}
                  </div>
                </div>
                <div>
                  <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">EXPERTISE VEHICULAR</p>
                  <div class="flex flex-wrap gap-1.5">
                    {#each workshop.vehicleExpertise as vehicle}
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 text-steel-500 px-2 py-0.5">{vehicle}</span>
                    {/each}
                  </div>
                </div>
              </div>

              <div class="border-t border-steel-600/20 pt-4 flex items-center justify-between gap-4">
                <div>
                  <p class="font-mono text-[10px] text-steel-500 uppercase">DISTRITO: {workshop.district.toUpperCase()}</p>
                  <p class="font-mono text-[10px] text-steel-500 uppercase">EXPERIENCIA: {workshop.yearsExperience} AÑOS</p>
                </div>
                <a href={`/servicios/taller/${workshop.workshopSlug}`} class="btn-rust text-xs shrink-0">
                  VER PERFIL →
                </a>
              </div>
            </div>
          </div>
        {/each}
      </section>
    {/if}

    <!-- Sin resultados -->
    {#if scoredListings.length === 0}
      <div class="bg-iron-900 border border-steel-600/25 p-8 text-center"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <p class="font-display text-3xl text-steel-600 uppercase mb-2">SIN RESULTADOS</p>
        <p class="font-mono text-xs text-steel-700 uppercase tracking-widest">
          PRUEBA AMPLIAR EL PRESUPUESTO, CAMBIAR LA CATEGORÍA O DESACTIVAR EL FILTRO DE CONFIANZA.
        </p>
      </div>
    {/if}

    <!-- Footer CTA -->
    <div class="bg-iron-900 border border-steel-600/25 p-8"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
        <div>
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// SEGUIR EXPLORANDO</p>
          <h2 class="font-display text-3xl text-bone uppercase leading-none">DETALLE DE TALLER O SERVICIO</h2>
        </div>
        <div class="flex flex-wrap gap-3">
          <a href="/servicios" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">NUEVA BÚSQUEDA</a>
          <a href="/servicios" class="btn-rust">VOLVER AL OVERVIEW →</a>
        </div>
      </div>
    </div>

  </main>
</div>
