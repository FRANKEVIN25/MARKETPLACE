<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/store/auth';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';
  import { api } from '$lib/api/client';
  import type { ServiceCategoryItem, VehicleMarca, VehicleModelo } from '$lib/api/types';

  const customer = auth.customer;

  let categories: ServiceCategoryItem[] = [];
  let marcas: VehicleMarca[] = [];
  let modelos: VehicleModelo[] = [];
  let departments: string[] = [];
  let provinces: string[] = [];
  let districts: string[] = [];

  let selectedCategoryId: number | null = null;
  let selectedMarcaId: number | null = null;
  let selectedModeloId: number | null = null;
  let wizardDepartment = '';
  let wizardProvince = '';
  let wizardDistrict = '';

  let loadingInit = true;
  let loadingModelos = false;
  let loadingLocation = false;

  onMount(async () => {
    const [cats, ms, locs] = await Promise.all([
      api.services.categories(),
      api.publicVehicles.marcas(),
      api.services.locationOptions(),
    ]);

    categories = cats;
    if (cats.length) selectedCategoryId = cats[0].id;

    marcas = ms;
    departments = locs.departments;

    const defaultDept = departments.includes('Lima') ? 'Lima' : (departments[0] ?? '');
    if (defaultDept) {
      wizardDepartment = defaultDept;
      const locOpts = await api.services.locationOptions(defaultDept);
      provinces = locOpts.provinces;
      districts = locOpts.districts;
    }

    if (ms.length) {
      selectedMarcaId = ms[0].id;
      const firstModelos = await api.publicVehicles.modelos(ms[0].id);
      modelos = firstModelos;
      if (firstModelos.length) selectedModeloId = firstModelos[0].id;
    }

    loadingInit = false;
  });

  async function handleMarcaChange() {
    if (!selectedMarcaId) return;
    loadingModelos = true;
    selectedModeloId = null;
    modelos = [];
    const ms = await api.publicVehicles.modelos(selectedMarcaId);
    modelos = ms;
    selectedModeloId = ms[0]?.id ?? null;
    loadingModelos = false;
  }

  async function handleDepartmentChange() {
    wizardProvince = '';
    wizardDistrict = '';
    provinces = [];
    districts = [];
    if (!wizardDepartment) return;
    loadingLocation = true;
    const opts = await api.services.locationOptions(wizardDepartment);
    provinces = opts.provinces;
    districts = opts.districts;
    loadingLocation = false;
  }

  async function handleProvinceChange() {
    wizardDistrict = '';
    districts = [];
    if (!wizardProvince || !wizardDepartment) return;
    loadingLocation = true;
    const opts = await api.services.locationOptions(wizardDepartment, wizardProvince);
    districts = opts.districts;
    loadingLocation = false;
  }

  function runDiagnosis(): void {
    const params = new URLSearchParams();
    if (selectedCategoryId) params.set('category_id', String(selectedCategoryId));
    if (selectedMarcaId) params.set('marca_id', String(selectedMarcaId));
    if (selectedModeloId) params.set('modelo_id', String(selectedModeloId));
    if (wizardDepartment) params.set('department', wizardDepartment);
    if (wizardProvince) params.set('province', wizardProvince);
    if (wizardDistrict) params.set('district', wizardDistrict);
    goto(`/servicios/resultados?${params.toString()}`);
  }

  function openWorkshopSetup(): void {
    if ($customer && isWorkshopBusinessActivity($customer.business_activity)) {
      goto('/taller/perfil');
      return;
    }
    goto('/registro');
  }

  function categoryIcon(icon: string | undefined): string {
    if (!icon) return '🔧';
    return icon;
  }
</script>

<svelte:head>
  <title>Servicios de Taller — ECOMPARTS</title>
  <meta
    name="description"
    content="Encuentra servicios de taller con búsqueda guiada, matching por vehículo y confianza basada en historial real de trabajos en ECOMPARTS."
  />
</svelte:head>

<!-- Hero de servicios -->
<div class="bg-iron-900 border-b border-steel-600/30">
  <div class="container-responsive py-6">
    <h1 class="font-display text-5xl md:text-6xl text-bone uppercase leading-none mb-3">SERVICIOS<br/>DE TALLER</h1>
    <p class="font-mono text-xs text-steel-800 uppercase tracking-widest">
      Búsqueda guiada · Matching por vehículo · Más de 500 talleres
    </p>
  </div>
</div>

<div class="container-responsive py-6">
  <div class="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-8 items-start">

    <!-- ══════════════════════════════════
         PASO 1: CATEGORÍA DEL PROBLEMA
    ═══════════════════════════════════ -->
    <div>
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)">

        <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between">
          <div>
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PASO 01</p>
            <p class="font-display text-2xl text-bone uppercase mt-1">¿QUÉ PROBLEMA TIENES?</p>
          </div>
          <span class="font-display text-6xl text-rust-600/15 leading-none">01</span>
        </div>

        <div class="p-6">
          {#if loadingInit}
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {#each Array(6) as _}
                <div class="bg-iron-800 border border-steel-600/20 p-4 h-24 animate-pulse"></div>
              {/each}
            </div>

          {:else if categories.length === 0}
            <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">SIN CATEGORÍAS DISPONIBLES</p>

          {:else}
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {#each categories as category (category.id)}
                <button
                  type="button"
                  onclick={() => (selectedCategoryId = category.id)}
                  class="border p-4 text-left transition-all duration-150 group
                    {selectedCategoryId === category.id
                      ? 'border-rust-600 bg-rust-600/10'
                      : 'border-steel-600/30 bg-iron-800/50 hover:border-steel-400'}"
                >
                  <div class="flex items-start justify-between gap-3 mb-2">
                    <p class="text-xl">
                      {#if category.icon && category.icon.trim().startsWith('fa-')}
                        <i class="fa-solid {category.icon}" aria-hidden="true"></i>
                      {:else}
                        {categoryIcon(category.icon)}
                      {/if}
                    </p>
                    {#if selectedCategoryId === category.id}
                      <span class="font-mono text-[9px] uppercase tracking-widest text-rust-500 border border-rust-600/40 px-2 py-0.5">
                        SELEC.
                      </span>
                    {/if}
                  </div>
                  <h3 class="font-display text-lg uppercase leading-none mb-1
                    {selectedCategoryId === category.id ? 'text-bone' : 'text-steel-300 group-hover:text-bone'}">
                    {category.name}
                  </h3>
                  <p class="font-mono text-[10px] leading-relaxed
                    {selectedCategoryId === category.id ? 'text-steel-400' : 'text-steel-600'}">
                    {category.description ?? ''}
                  </p>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════
         SIDEBAR: PASOS 2, 3 + CTA
    ═══════════════════════════════════ -->
    <aside class="space-y-5">

      <!-- Wizard: vehículo + ubicación -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">

        <!-- Paso 2: Vehículo -->
        <div class="border-b border-steel-600/25 px-5 py-4">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PASO 02 — VEHÍCULO</p>
        </div>
        <div class="p-5 space-y-3">
          <div>
            <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MARCA</label>
            <select
              bind:value={selectedMarcaId}
              onchange={handleMarcaChange}
              disabled={loadingInit}
              class="input-industrial disabled:opacity-50"
            >
              {#if loadingInit}
                <option value={null}>Cargando...</option>
              {:else if marcas.length === 0}
                <option value={null}>Sin datos</option>
              {:else}
                {#each marcas as marca (marca.id)}
                  <option value={marca.id}>{marca.nombre}</option>
                {/each}
              {/if}
            </select>
          </div>
          <div>
            <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MODELO</label>
            <select
              bind:value={selectedModeloId}
              disabled={loadingInit || loadingModelos || modelos.length === 0}
              class="input-industrial disabled:opacity-50"
            >
              {#if loadingModelos}
                <option value={null}>Cargando...</option>
              {:else if modelos.length === 0}
                <option value={null}>Sin datos</option>
              {:else}
                {#each modelos as modelo (modelo.id)}
                  <option value={modelo.id}>{modelo.nombre}</option>
                {/each}
              {/if}
            </select>
          </div>
        </div>

        <!-- Paso 3: Ubicación -->
        <div class="border-t border-steel-600/25 px-5 py-4">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PASO 03 — UBICACIÓN</p>
        </div>
        <div class="p-5 space-y-3">
          <div>
            <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">DEPARTAMENTO</label>
            <select
              bind:value={wizardDepartment}
              onchange={handleDepartmentChange}
              disabled={loadingInit}
              class="input-industrial disabled:opacity-50"
            >
              {#if loadingInit}
                <option value="">Cargando...</option>
              {:else if departments.length === 0}
                <option value="">Sin talleres registrados</option>
              {:else}
                <option value="">Todos los departamentos</option>
                {#each departments as dept}
                  <option value={dept}>{dept}</option>
                {/each}
              {/if}
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">
                PROVINCIA <span class="text-steel-700">(OPC.)</span>
              </label>
              <select
                bind:value={wizardProvince}
                onchange={handleProvinceChange}
                disabled={loadingLocation || provinces.length === 0}
                class="input-industrial disabled:opacity-50"
              >
                <option value="">Todas</option>
                {#each provinces as prov}
                  <option value={prov}>{prov}</option>
                {/each}
              </select>
            </div>
            <div>
              <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">
                DISTRITO <span class="text-steel-700">(OPC.)</span>
              </label>
              <select
                bind:value={wizardDistrict}
                disabled={loadingLocation || districts.length === 0}
                class="input-industrial disabled:opacity-50"
              >
                <option value="">Todos</option>
                {#each districts as dist}
                  <option value={dist}>{dist}</option>
                {/each}
              </select>
            </div>
          </div>
        </div>

        <!-- CTA buscar -->
        <div class="border-t border-steel-600/25 p-5">
          <button
            type="button"
            onclick={runDiagnosis}
            disabled={loadingInit || !selectedCategoryId}
            class="w-full bg-rust-600 hover:bg-rust-700 disabled:opacity-40 disabled:cursor-not-allowed
                   text-bone font-display text-xl uppercase tracking-widest py-4 transition-colors"
            style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)"
          >
            BUSCAR TALLERES →
          </button>
        </div>
      </div>

      <!-- CTA para talleres -->
      <div class="bg-iron-900 border border-steel-600/25 p-6 relative overflow-hidden"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <!-- BG decoration -->
        <div class="absolute top-0 right-0 w-32 h-32 opacity-5 pointer-events-none" aria-hidden="true">
          <svg viewBox="0 0 200 200" fill="none" stroke="#e64a19" stroke-width="0.5">
            <circle cx="100" cy="100" r="90"/><circle cx="100" cy="100" r="60"/>
            <line x1="10" y1="100" x2="190" y2="100"/>
            <line x1="100" y1="10" x2="100" y2="190"/>
          </svg>
        </div>
        <div class="relative z-10">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-3">// PARA TALLERES</p>
          <h2 class="font-display text-2xl text-bone uppercase leading-none mb-3">
            TU TALLER TAMBIÉN<br/>PUEDE PUBLICAR AQUÍ
          </h2>
          <p class="font-mono text-xs text-steel-500 leading-relaxed mb-5 uppercase tracking-wide">
            Define categorías, publica servicios, exhibe expertise por vehículo.
          </p>
          <div class="flex flex-col gap-2">
            <button
              onclick={openWorkshopSetup}
              class="btn-rust text-center"
            >
              CONFIGURAR MI TALLER
            </button>
            <a href="/taller/servicios" class="btn-outline text-center text-sm">
              VER PLANTILLA INTERNA
            </a>
          </div>
        </div>
      </div>

    </aside>
  </div>
</div>
