<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/store/auth';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';
  import { api } from '$lib/api/client';
  import type { ServiceCategoryItem, VehicleMarca, VehicleModelo } from '$lib/api/types';

  const customer = auth.customer;

  // ── Datos del backend ─────────────────────────────────────────────────────
  let categories: ServiceCategoryItem[] = [];
  let marcas: VehicleMarca[] = [];
  let modelos: VehicleModelo[] = [];
  let departments: string[] = [];
  let provinces: string[] = [];
  let districts: string[] = [];

  // ── Estado del wizard ─────────────────────────────────────────────────────
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

    // Departamento por defecto
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
  <title>Servicios de Taller | ECOMPARTS</title>
  <meta
    name="description"
    content="Encuentra servicios de taller con búsqueda guiada, matching por vehículo y confianza basada en historial real de trabajos en ECOMPARTS."
  />
</svelte:head>

<section class="bg-gradient-to-br from-slate-950 via-blue-950 to-indigo-900 text-white">
  <div class="max-w-7xl mx-auto px-6 py-16 md:py-20 grid grid-cols-1 xl:grid-cols-[1.08fr,0.92fr] gap-10 items-start">

    <!-- ── Paso 1: Categoría del problema ───────────────────────────────── -->
    <div class="space-y-8">
      <div class="rounded-3xl border border-white/15 bg-white/10 backdrop-blur p-6 md:p-7 shadow-2xl">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <p class="text-sm font-semibold uppercase tracking-wide text-blue-200">Búsqueda inteligente guiada</p>
            <h2 class="text-2xl font-bold mt-1">1. ¿Qué problema tienes?</h2>
          </div>
        </div>

        {#if loadingInit}
          <!-- Skeleton de carga -->
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {#each Array(6) as _}
              <div class="rounded-2xl border border-white/10 bg-white/5 p-4 animate-pulse h-24"></div>
            {/each}
          </div>
        {:else if categories.length === 0}
          <p class="text-blue-200 text-sm">No hay categorías disponibles aún.</p>
        {:else}
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {#each categories as category (category.id)}
              <button
                type="button"
                onclick={() => (selectedCategoryId = category.id)}
                class={`rounded-2xl border p-4 text-left transition ${selectedCategoryId === category.id
                  ? 'border-blue-300 bg-white text-slate-900 shadow-lg'
                  : 'border-white/15 bg-white/5 text-white hover:bg-white/10'}`}
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-2xl mb-2">
                      {#if category.icon && category.icon.trim().startsWith('fa-')}
                        <i class={`fa-solid ${category.icon} `} aria-hidden="true"></i>
                      {:else}
                        {categoryIcon(category.icon)}
                      {/if}
                    </p>
                    <h3 class="font-bold">{category.name}</h3>
                  </div>
                  {#if selectedCategoryId === category.id}
                    <span class="text-xs font-semibold rounded-full bg-blue-100 text-blue-700 px-2 py-1 shrink-0">Seleccionado</span>
                  {/if}
                </div>
                <p class={`text-sm mt-2 ${selectedCategoryId === category.id ? 'text-slate-600' : 'text-blue-100'}`}>
                  {category.description ?? ''}
                </p>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- ── Sidebar: Pasos 2 y 3 + CTA talleres ──────────────────────────── -->
    <aside class="space-y-6">

      <!-- Wizard: vehículo + ubicación -->
      <div class="rounded-3xl bg-slate-700 p-2 md:p-4 shadow-2xl">
        <div class="grid grid-cols-1 gap-4 mt-4">

          <!-- Paso 2: Vehículo -->
          <div class="rounded-2xl bg-slate-950/35 border border-white/10 p-4">
            <p class="text-sm font-semibold text-blue-200 mb-3">2. ¿Qué vehículo tienes?</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label>
                <span class="block text-sm text-blue-100 mb-2">Marca</span>
                <select
                  bind:value={selectedMarcaId}
                  onchange={handleMarcaChange}
                  disabled={loadingInit}
                  class="w-full rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
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
              </label>
              <label>
                <span class="block text-sm text-blue-100 mb-2">Modelo</span>
                <select
                  bind:value={selectedModeloId}
                  disabled={loadingInit || loadingModelos || modelos.length === 0}
                  class="w-full rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
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
              </label>
            </div>
          </div>

          <!-- Paso 3: Ubicación -->
          <div class="rounded-2xl bg-slate-950/35 border border-white/10 p-4">
            <p class="text-sm font-semibold text-blue-200 mb-3">3. ¿Dónde estás?</p>
            <div class="grid grid-cols-1 gap-3">
              <label>
                <span class="block text-sm text-blue-100 mb-2">Departamento</span>
                <select
                  bind:value={wizardDepartment}
                  onchange={handleDepartmentChange}
                  disabled={loadingInit}
                  class="w-full rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
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
              </label>
              <div class="grid grid-cols-2 gap-3">
                <label>
                  <span class="block text-sm text-blue-100 mb-2">
                    Provincia <span class="text-blue-300/60 text-xs">(opcional)</span>
                  </span>
                  <select
                    bind:value={wizardProvince}
                    onchange={handleProvinceChange}
                    disabled={loadingLocation || provinces.length === 0}
                    class="w-full rounded-xl border border-white/15 bg-white/10 px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
                  >
                    <option value="">Todas</option>
                    {#each provinces as prov}
                      <option value={prov}>{prov}</option>
                    {/each}
                  </select>
                </label>
                <label>
                  <span class="block text-sm text-blue-100 mb-2">
                    Distrito <span class="text-blue-300/60 text-xs">(opcional)</span>
                  </span>
                  <select
                    bind:value={wizardDistrict}
                    disabled={loadingLocation || districts.length === 0}
                    class="w-full rounded-xl border border-white/15 bg-white/10 px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-50"
                  >
                    <option value="">Todos</option>
                    {#each districts as dist}
                      <option value={dist}>{dist}</option>
                    {/each}
                  </select>
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 px-2 pb-2">
          <button
            type="button"
            onclick={runDiagnosis}
            disabled={loadingInit || !selectedCategoryId}
            class="w-full rounded-2xl bg-blue-500 hover:bg-blue-400 disabled:bg-blue-800 disabled:opacity-60 text-white font-bold px-6 py-4 text-base transition shadow-lg"
          >
            Buscar talleres →
          </button>
        </div>
      </div>

      <!-- CTA: activación para talleres -->
      <section class="rounded-3xl border border-white/15 bg-white/10 backdrop-blur p-6 text-white shadow-xl">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-200 mb-3">Activación para talleres</p>
        <h2 class="text-2xl font-bold mb-3">Tu negocio también puede publicar aquí</h2>
        <p class="text-blue-100 mb-5">
          Si tu empresa opera como taller, puedes definir categorías, publicar servicios, exhibir expertise por vehículo y escalar después hacia una operación más gestionada.
        </p>
        <div class="flex flex-wrap gap-3">
          <button onclick={openWorkshopSetup} class="rounded-xl bg-white text-blue-800 font-semibold px-5 py-3 hover:bg-blue-50 transition">
            Configurar mi taller
          </button>
          <a href="/taller/servicios" class="rounded-xl border border-white/25 px-5 py-3 font-semibold hover:bg-white/10 transition">
            Ver plantilla interna
          </a>
        </div>
      </section>
    </aside>
  </div>
</section>
