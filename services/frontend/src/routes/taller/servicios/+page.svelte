<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';
  import type {
    Customer,
    ServiceCatalogCategory,
    ServiceCatalogServiceOption,
    VehicleExpertiseLevel,
    VehicleMarca,
    VehicleModelo,
    WorkshopServiceConfigItem,
    WorkshopVehicleExpertiseItem,
  } from '$lib/api/types';

  type VehicleGranularity = 'marca' | 'modelo';

  const serviceTypeLabels: Record<string, string> = {
    maintenance: 'Mantenimiento',
    repair: 'Reparacion',
    diagnostic: 'Diagnostico',
  };

  const complexityLabels: Record<string, string> = {
    low: 'Baja',
    medium: 'Media',
    high: 'Alta',
  };

  const expertiseLevelOptions: Array<{ value: VehicleExpertiseLevel; label: string }> = [
    { value: 'basic', label: 'Basico' },
    { value: 'pro', label: 'Profesional' },
    { value: 'expert', label: 'Experto' },
  ];

  let customer: Customer | null = null;
  let loading = true;
  let saving = false;
  let loadingVehicleModels = false;
  let accessDenied = false;
  let message = '';
  let error = '';

  let categories: ServiceCatalogCategory[] = [];
  let workshopServices: WorkshopServiceConfigItem[] = [];
  let vehicleExpertise: WorkshopVehicleExpertiseItem[] = [];
  let vehicleBrands: VehicleMarca[] = [];
  let vehicleModelsByBrand: Record<number, VehicleModelo[]> = {};

  let vehiclePicker = {
    granularity: 'marca' as VehicleGranularity,
    marcaId: '',
    modeloId: '',
    expertiseLevel: 'pro' as VehicleExpertiseLevel,
    notes: '',
  };

  function buildWorkshopServiceSeed(service: ServiceCatalogServiceOption, category: ServiceCatalogCategory): WorkshopServiceConfigItem {
    return {
      service: service.id,
      service_name: service.name,
      category_id: category.id,
      category_name: category.name,
      service_type: service.service_type,
      complexity: service.complexity,
      is_specialized: false,
      min_price: null,
      max_price: null,
      currency: 'PEN',
      estimated_time_min: 60,
      available: true,
      has_warranty: false,
      warranty_days: 0,
    };
  }

  function getSelectedService(serviceId: number): WorkshopServiceConfigItem | undefined {
    return workshopServices.find((item) => item.service === serviceId);
  }

  function toggleService(category: ServiceCatalogCategory, service: ServiceCatalogServiceOption) {
    if (getSelectedService(service.id)) {
      workshopServices = workshopServices.filter((item) => item.service !== service.id);
      return;
    }

    workshopServices = [...workshopServices, buildWorkshopServiceSeed(service, category)];
  }

  function updateWorkshopService(serviceId: number, patch: Partial<WorkshopServiceConfigItem>) {
    workshopServices = workshopServices.map((item) => {
      if (item.service !== serviceId) {
        return item;
      }

      const nextItem = { ...item, ...patch };

      if (patch.has_warranty === false) {
        nextItem.warranty_days = 0;
      }

      if ((nextItem.min_price ?? null) !== null && (nextItem.max_price ?? null) !== null) {
        nextItem.max_price = Math.max(nextItem.min_price as number, nextItem.max_price as number);
      }

      nextItem.estimated_time_min = Math.max(Number(nextItem.estimated_time_min || 0), 15);
      nextItem.warranty_days = Math.max(Number(nextItem.warranty_days || 0), 0);

      return nextItem;
    });
  }

  function updatePrice(serviceId: number, field: 'min_price' | 'max_price', value: string) {
    const trimmed = value.trim();
    const numericValue = trimmed ? Number(trimmed) : null;
    updateWorkshopService(serviceId, {
      [field]: numericValue !== null && Number.isFinite(numericValue) ? numericValue : null,
    } as Partial<WorkshopServiceConfigItem>);
  }

  async function ensureModelsLoaded(marcaId: number) {
    if (vehicleModelsByBrand[marcaId]) {
      return;
    }

    const token = auth.getAccessToken();
    if (!token) {
      return;
    }

    loadingVehicleModels = true;
    try {
      const models = await api.services.vehicleModelos(token, marcaId);
      vehicleModelsByBrand = {
        ...vehicleModelsByBrand,
        [marcaId]: models,
      };
    } finally {
      loadingVehicleModels = false;
    }
  }

  async function handleBrandChange(value: string) {
    vehiclePicker = {
      ...vehiclePicker,
      marcaId: value,
      modeloId: '',
    };

    if (vehiclePicker.granularity === 'modelo' && value) {
      await ensureModelsLoaded(Number(value));
    }
  }

  async function handleGranularityChange(value: VehicleGranularity) {
    vehiclePicker = {
      ...vehiclePicker,
      granularity: value,
      modeloId: '',
    };

    if (value === 'modelo' && vehiclePicker.marcaId) {
      await ensureModelsLoaded(Number(vehiclePicker.marcaId));
    }
  }

  function addVehicleExpertise() {
    error = '';

    const marcaId = vehiclePicker.marcaId ? Number(vehiclePicker.marcaId) : null;
    const modeloId = vehiclePicker.modeloId ? Number(vehiclePicker.modeloId) : null;

    if (!marcaId) {
      error = 'Selecciona una marca para agregar expertise vehicular.';
      return;
    }

    if (vehiclePicker.granularity === 'modelo' && !modeloId) {
      error = 'Selecciona un modelo cuando el expertise sea a nivel de modelo.';
      return;
    }

    const duplicate = vehicleExpertise.some((item) => (
      vehiclePicker.granularity === 'modelo'
        ? item.modelo === modeloId
        : item.marca === marcaId && !item.modelo
    ));

    if (duplicate) {
      error = 'Ese expertise ya esta agregado en la configuracion del taller.';
      return;
    }

    const brand = vehicleBrands.find((item) => item.id === marcaId) || null;
    const model = modeloId
      ? (vehicleModelsByBrand[marcaId] || []).find((item) => item.id === modeloId) || null
      : null;

    vehicleExpertise = [
      ...vehicleExpertise,
      {
        marca: vehiclePicker.granularity === 'marca' ? marcaId : null,
        marca_nombre: brand?.nombre || null,
        modelo: vehiclePicker.granularity === 'modelo' ? modeloId : null,
        modelo_nombre: model?.nombre || null,
        granularity: vehiclePicker.granularity,
        label: vehiclePicker.granularity === 'modelo'
          ? `${brand?.nombre || ''} ${model?.nombre || ''}`.trim()
          : brand?.nombre || null,
        expertise_level: vehiclePicker.expertiseLevel,
        notes: vehiclePicker.notes.trim(),
        total_jobs: 0,
        last_job_date: null,
      },
    ];

    vehiclePicker = {
      granularity: vehiclePicker.granularity,
      marcaId: '',
      modeloId: '',
      expertiseLevel: 'pro',
      notes: '',
    };
  }

  function updateVehicleExpertise(index: number, patch: Partial<WorkshopVehicleExpertiseItem>) {
    vehicleExpertise = vehicleExpertise.map((item, itemIndex) => itemIndex === index
      ? { ...item, ...patch }
      : item);
  }

  function removeVehicleExpertise(index: number) {
    vehicleExpertise = vehicleExpertise.filter((_, itemIndex) => itemIndex !== index);
  }

  async function saveCatalog() {
    saving = true;
    message = '';
    error = '';

    try {
      const token = auth.getAccessToken();
      if (!token) {
        window.location.href = '/login';
        return;
      }

      const payload = {
        workshop_services: workshopServices.map((item) => ({
          service: item.service,
          is_specialized: item.is_specialized,
          min_price: item.min_price,
          max_price: item.max_price,
          currency: item.currency || 'PEN',
          estimated_time_min: Math.max(Number(item.estimated_time_min || 0), 15),
          available: item.available,
          has_warranty: item.has_warranty,
          warranty_days: item.has_warranty ? Math.max(Number(item.warranty_days || 0), 0) : 0,
        })),
        vehicle_expertise: vehicleExpertise.map((item) => ({
          ...(item.modelo ? { modelo: item.modelo } : { marca: item.marca }),
          expertise_level: item.expertise_level,
          notes: item.notes || '',
        })),
      };

      const updated = await api.services.updateWorkshopCatalog(token, payload);
      categories = updated.categories;
      workshopServices = updated.workshop_services;
      vehicleExpertise = updated.vehicle_expertise;
      message = 'Catalogo del taller guardado. Servicios y expertise vehicular ya quedaron sincronizados con el backend.';
    } catch (e) {
      error = 'No se pudo guardar la configuracion de servicios del taller.';
    } finally {
      saving = false;
    }
  }

  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }

    try {
      const [profile, catalog, brands] = await Promise.all([
        api.customer.getProfile(token),
        api.services.getWorkshopCatalog(token),
        api.services.vehicleMarcas(token),
      ]);

      customer = profile;
      auth.customer.set(profile);

      if (profile.customer_type !== 'company' || !isWorkshopBusinessActivity(profile.business_activity)) {
        accessDenied = true;
        error = 'Este catalogo solo esta disponible para empresas configuradas como taller mecanico.';
        return;
      }

      categories = catalog.categories;
      workshopServices = catalog.workshop_services;
      vehicleExpertise = catalog.vehicle_expertise;
      vehicleBrands = brands;
    } catch (e) {
      error = 'No se pudo cargar la configuracion de servicios del taller.';
    } finally {
      loading = false;
    }
  });

  $: activeServices = workshopServices.filter((service) => service.available).length;
  $: specializedServices = workshopServices.filter((service) => service.is_specialized).length;
  $: warrantyServices = workshopServices.filter((service) => service.has_warranty).length;
  $: configuredCategories = categories.filter((category) => category.services.some((service) => getSelectedService(service.id)));
  $: selectedCategoryNames = configuredCategories.map((category) => category.name);
  $: serviceCoverage = categories.length ? Math.round((configuredCategories.length / categories.length) * 100) : 0;
  $: publishedVehicleExpertise = vehicleExpertise.filter((item) => item.expertise_level !== 'basic').length;
  $: currentBrandModels = vehiclePicker.marcaId ? (vehicleModelsByBrand[Number(vehiclePicker.marcaId)] || []) : [];
</script>

<svelte:head>
  <title>Servicios del Taller — ECOMPARTS</title>
  <meta name="description" content="Configura el catálogo real del taller: categorías, servicios publicados y expertise vehicular." />
</svelte:head>

<div class="container-responsive py-10">

  {#if loading}
    <div class="bg-iron-900 border border-steel-600/25 p-16 text-center">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO CONFIGURACIÓN DEL CATÁLOGO...</p>
    </div>

  {:else if accessDenied}
    <div class="border border-rust-700/50 bg-rust-600/10 p-8"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// ACCESO NO HABILITADO</p>
      <h1 class="font-display text-3xl text-bone uppercase mb-3">MÓDULO NO DISPONIBLE</h1>
      <p class="font-mono text-xs text-steel-500 leading-relaxed mb-6 max-w-xl">{error}</p>
      <a href="/cliente/perfil" class="btn-outline">← VOLVER A MI PERFIL</a>
    </div>

  {:else}

    <!-- ── Header ── -->
    <div class="border-b border-steel-600/25 pb-8 mb-8">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// CATÁLOGO DEL TALLER</p>
      <h1 class="font-display text-5xl text-bone uppercase leading-none mb-2">CONFIGURA TUS SERVICIOS</h1>
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest mb-8">
        Selecciona solo lo que realmente ofreces · Precios · Tiempos · Expertise vehicular
      </p>

      <!-- Métricas -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <div class="bg-iron-900 border border-steel-600/25 p-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">SERVICIOS</p>
          <p class="font-display text-4xl text-bone leading-none">{workshopServices.length}</p>
          <p class="font-mono text-[9px] text-steel-600 mt-1">{activeServices} VISIBLES</p>
        </div>
        <div class="bg-iron-900 border border-steel-600/25 p-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COBERTURA</p>
          <p class="font-display text-4xl text-bone leading-none">{serviceCoverage}%</p>
          <p class="font-mono text-[9px] text-steel-600 mt-1">{configuredCategories.length} CATEGORÍAS</p>
        </div>
        <div class="bg-iron-900 border border-steel-600/25 p-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ESPECIALIZADOS</p>
          <p class="font-display text-4xl text-bone leading-none">{specializedServices}</p>
          <p class="font-mono text-[9px] text-steel-600 mt-1">SERVICIOS DIFERENCIALES</p>
        </div>
        <div class="bg-iron-900 border border-steel-600/25 p-4">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">EXPERTISE</p>
          <p class="font-display text-4xl text-bone leading-none">{vehicleExpertise.length}</p>
          <p class="font-mono text-[9px] text-steel-600 mt-1">{publishedVehicleExpertise} PRO/EXPERTO</p>
        </div>
      </div>

      <!-- Acciones -->
      <div class="flex flex-wrap gap-3">
        <a href="/taller/perfil" class="btn-ghost">← VOLVER AL PERFIL</a>
        <button
          type="button"
          on:click={saveCatalog}
          disabled={saving}
          class="btn-rust disabled:opacity-50 disabled:cursor-not-allowed"
          style="clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)"
        >
          {saving ? 'GUARDANDO...' : 'GUARDAR CONFIGURACIÓN →'}
        </button>
      </div>
    </div>

    <!-- ── Main grid ── -->
    <div class="grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-6 items-start">

      <!-- ═══════════════════════════════
           COLUMNA IZQUIERDA
      ═══════════════════════════════ -->
      <div class="space-y-6">

        <!-- ── SECCIÓN: Servicios por categoría ── -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4 flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SERVICIOS</p>
              <h2 class="font-display text-3xl text-bone uppercase leading-none mt-1">ARMA TU CATÁLOGO</h2>
              <p class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">
                Disponibilidad · Precios · Tiempo estimado · Garantía
              </p>
            </div>
            <div class="border border-steel-600/30 px-4 py-2 shrink-0">
              <span class="font-mono text-[9px] text-steel-600 uppercase tracking-widest">
                {configuredCategories.length} DE {categories.length} CATEGORÍAS CONFIGURADAS
              </span>
            </div>
          </div>

          <!-- Categorías -->
          <div class="divide-y divide-steel-600/20">
            {#each categories as category}
              {@const selectedCount = category.services.filter((s) => getSelectedService(s.id)).length}
              <div>
                <!-- Category header -->
                <div class="px-6 py-4 flex items-center justify-between gap-3 bg-iron-950/40">
                  <div>
                    <p class="font-display text-xl text-bone uppercase">{category.name}</p>
                    {#if category.description}
                      <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mt-0.5">{category.description}</p>
                    {/if}
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/30 px-2 py-1 text-steel-600">
                      {category.services.length} BASE
                    </span>
                    {#if selectedCount > 0}
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-rust-600/60 text-rust-500 bg-rust-600/10 px-2 py-1">
                        {selectedCount} SEL.
                      </span>
                    {/if}
                  </div>
                </div>

                <!-- Services list -->
                <div class="divide-y divide-steel-600/10">
                  {#each category.services as service}
                    {@const selected = getSelectedService(service.id)}
                    <div class="transition-colors {selected ? 'bg-rust-600/5' : ''}">

                      <!-- Service row -->
                      <div class="px-6 py-4 flex items-center justify-between gap-4">
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2 flex-wrap mb-1.5">
                            <p class="font-mono text-xs text-bone uppercase tracking-widest">{service.name}</p>
                            {#if selected}
                              <span class="font-mono text-[9px] uppercase tracking-widest border border-rust-600/60 text-rust-500 bg-rust-600/10 px-2 py-0.5">
                                EN CATÁLOGO
                              </span>
                            {/if}
                          </div>
                          <div class="flex items-center gap-2 flex-wrap">
                            <span class="font-mono text-[9px] text-steel-600 uppercase tracking-widest border border-steel-600/25 px-2 py-0.5">
                              {serviceTypeLabels[service.service_type] || service.service_type}
                            </span>
                            <span class="font-mono text-[9px] text-steel-600 uppercase tracking-widest border border-steel-600/25 px-2 py-0.5">
                              COMPLEJIDAD {complexityLabels[service.complexity] || service.complexity}
                            </span>
                          </div>
                        </div>
                        <button
                          type="button"
                          on:click={() => toggleService(category, service)}
                          class="font-mono text-[10px] uppercase tracking-widest px-4 py-2 transition-colors shrink-0
                                 {selected
                                   ? 'border border-rust-600/40 text-rust-400 hover:border-rust-500 hover:text-rust-300'
                                   : 'border border-steel-600/40 text-steel-300 hover:text-bone hover:border-steel-400'}"
                        >
                          {selected ? '✕ QUITAR' : '+ AGREGAR'}
                        </button>
                      </div>

                      <!-- Config panel when selected -->
                      {#if selected}
                        <div class="px-6 pb-6 space-y-5 border-t border-steel-600/15 bg-iron-800/30 pt-5">

                          <!-- Precios y tiempos -->
                          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <div>
                              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                                // PRECIO MÍN (S/.)
                              </label>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={selected.min_price ?? ''}
                                on:input={(e) => updatePrice(service.id, 'min_price', (e.currentTarget as HTMLInputElement).value)}
                                placeholder="0.00"
                                class="input-industrial"
                              />
                            </div>
                            <div>
                              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                                // PRECIO MÁX (S/.)
                              </label>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={selected.max_price ?? ''}
                                on:input={(e) => updatePrice(service.id, 'max_price', (e.currentTarget as HTMLInputElement).value)}
                                placeholder="0.00"
                                class="input-industrial"
                              />
                            </div>
                            <div>
                              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                                // DURACIÓN (MIN)
                              </label>
                              <input
                                type="number"
                                min="15"
                                step="15"
                                value={selected.estimated_time_min}
                                on:input={(e) => updateWorkshopService(service.id, { estimated_time_min: Number((e.currentTarget as HTMLInputElement).value) || 15 })}
                                class="input-industrial"
                              />
                            </div>
                            <div>
                              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                                // MONEDA
                              </label>
                              <input
                                value={selected.currency}
                                maxlength="10"
                                on:input={(e) => updateWorkshopService(service.id, { currency: (e.currentTarget as HTMLInputElement).value.toUpperCase() || 'PEN' })}
                                class="input-industrial"
                              />
                            </div>
                          </div>

                          <!-- Checkboxes booleanos -->
                          <div class="flex flex-wrap gap-5 border-t border-steel-600/15 pt-4">
                            <label class="flex items-center gap-2 cursor-pointer group">
                              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                                          {selected.available ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                                <input
                                  type="checkbox"
                                  checked={selected.available}
                                  on:change={(e) => updateWorkshopService(service.id, { available: (e.currentTarget as HTMLInputElement).checked })}
                                  class="sr-only"
                                />
                                {#if selected.available}
                                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                  </svg>
                                {/if}
                              </div>
                              <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">VISIBLE AL CLIENTE</span>
                            </label>

                            <label class="flex items-center gap-2 cursor-pointer group">
                              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                                          {selected.is_specialized ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                                <input
                                  type="checkbox"
                                  checked={selected.is_specialized}
                                  on:change={(e) => updateWorkshopService(service.id, { is_specialized: (e.currentTarget as HTMLInputElement).checked })}
                                  class="sr-only"
                                />
                                {#if selected.is_specialized}
                                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                  </svg>
                                {/if}
                              </div>
                              <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">SERVICIO DIFERENCIAL</span>
                            </label>

                            <label class="flex items-center gap-2 cursor-pointer group">
                              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                                          {selected.has_warranty ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                                <input
                                  type="checkbox"
                                  checked={selected.has_warranty}
                                  on:change={(e) => updateWorkshopService(service.id, { has_warranty: (e.currentTarget as HTMLInputElement).checked })}
                                  class="sr-only"
                                />
                                {#if selected.has_warranty}
                                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                  </svg>
                                {/if}
                              </div>
                              <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">INCLUYE GARANTÍA</span>
                            </label>
                          </div>

                          <!-- Días de garantía -->
                          {#if selected.has_warranty}
                            <div class="max-w-xs">
                              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                                // DÍAS DE GARANTÍA
                              </label>
                              <input
                                type="number"
                                min="0"
                                step="1"
                                value={selected.warranty_days}
                                on:input={(e) => updateWorkshopService(service.id, { warranty_days: Number((e.currentTarget as HTMLInputElement).value) || 0 })}
                                class="input-industrial"
                              />
                            </div>
                          {/if}
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- ── SECCIÓN: Expertise vehicular ── -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4 flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// EXPERTISE VEHICULAR</p>
              <h2 class="font-display text-3xl text-bone uppercase leading-none mt-1">FOCOS VEHICULARES</h2>
              <p class="font-mono text-[9px] text-steel-500 uppercase tracking-widest mt-1">Define en qué marcas o modelos eres fuerte · WorkshopVehicleExpertise</p>
            </div>
            <div class="border border-steel-600/30 px-4 py-2 shrink-0">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest">
                {vehicleExpertise.length} FOCO{vehicleExpertise.length !== 1 ? 'S' : ''} REGISTRADO{vehicleExpertise.length !== 1 ? 'S' : ''}
              </p>
            </div>
          </div>

          <!-- Picker form -->
          <div class="p-6 space-y-5 border-b border-steel-600/20">

            <!-- Granularidad toggle -->
            <div>
              <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// NIVEL DE GRANULARIDAD</p>
              <div class="flex gap-0">
                <button
                  type="button"
                  on:click={() => handleGranularityChange('marca')}
                  class="font-mono text-[10px] uppercase tracking-widest px-5 py-2.5 border transition-colors
                         {vehiclePicker.granularity === 'marca'
                           ? 'bg-rust-600 border-rust-600 text-bone'
                           : 'border-steel-600/40 text-steel-400 hover:text-bone hover:border-steel-400'}"
                >
                  POR MARCA
                </button>
                <button
                  type="button"
                  on:click={() => handleGranularityChange('modelo')}
                  class="font-mono text-[10px] uppercase tracking-widest px-5 py-2.5 border-y border-r transition-colors
                         {vehiclePicker.granularity === 'modelo'
                           ? 'bg-rust-600 border-rust-600 text-bone'
                           : 'border-steel-600/40 text-steel-400 hover:text-bone hover:border-steel-400'}"
                >
                  POR MODELO
                </button>
              </div>
            </div>

            <!-- Selects -->
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// MARCA</label>
                <select
                  value={vehiclePicker.marcaId}
                  on:change={(e) => handleBrandChange((e.currentTarget as HTMLSelectElement).value)}
                  class="input-industrial"
                >
                  <option value="">Selecciona una marca</option>
                  {#each vehicleBrands as brand}
                    <option value={brand.id}>{brand.nombre}</option>
                  {/each}
                </select>
              </div>

              {#if vehiclePicker.granularity === 'modelo'}
                <div>
                  <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// MODELO</label>
                  <select
                    value={vehiclePicker.modeloId}
                    on:change={(e) => vehiclePicker = { ...vehiclePicker, modeloId: (e.currentTarget as HTMLSelectElement).value }}
                    disabled={!vehiclePicker.marcaId || loadingVehicleModels}
                    class="input-industrial disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <option value="">{loadingVehicleModels ? 'CARGANDO...' : 'Selecciona un modelo'}</option>
                    {#each currentBrandModels as model}
                      <option value={model.id}>{model.nombre}</option>
                    {/each}
                  </select>
                </div>
              {/if}

              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NIVEL</label>
                <select
                  value={vehiclePicker.expertiseLevel}
                  on:change={(e) => vehiclePicker = { ...vehiclePicker, expertiseLevel: (e.currentTarget as HTMLSelectElement).value as VehicleExpertiseLevel }}
                  class="input-industrial"
                >
                  {#each expertiseLevelOptions as level}
                    <option value={level.value}>{level.label}</option>
                  {/each}
                </select>
              </div>
            </div>

            <!-- Notas -->
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NOTAS INTERNAS</label>
              <textarea
                rows="3"
                bind:value={vehiclePicker.notes}
                placeholder="Ej: alto volumen de Toyota Corolla, diagnósticos frecuentes de caja CVT..."
                class="input-industrial resize-none"
              ></textarea>
            </div>

            <div class="flex justify-end">
              <button
                type="button"
                on:click={addVehicleExpertise}
                class="bg-rust-600 text-bone hover:bg-rust-700 font-mono text-[10px] uppercase tracking-industrial
                       px-5 py-2.5 transition-colors"
                style="clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)"
              >
                + AGREGAR EXPERTISE
              </button>
            </div>
          </div>

          <!-- Lista de expertise -->
          <div class="divide-y divide-steel-600/15">
            {#each vehicleExpertise as item, index}
              <div class="px-6 py-5 space-y-4">
                <!-- Item header -->
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="flex items-center gap-2 flex-wrap mb-1">
                      <p class="font-mono text-xs text-bone uppercase tracking-widest">
                        {item.label || item.modelo_nombre || item.marca_nombre || 'VEHÍCULO CONFIGURADO'}
                      </p>
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 px-2 py-0.5 text-steel-500">
                        {item.granularity === 'modelo' ? 'MODELO' : 'MARCA'}
                      </span>
                    </div>
                    {#if item.modelo_nombre}
                      <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                        {item.marca_nombre || ''} · {item.modelo_nombre}
                      </p>
                    {:else if item.marca_nombre}
                      <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">{item.marca_nombre}</p>
                    {/if}
                    {#if item.total_jobs}
                      <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mt-1">
                        {item.total_jobs} TRABAJO{item.total_jobs !== 1 ? 'S' : ''} REGISTRADO{item.total_jobs !== 1 ? 'S' : ''}
                      </p>
                    {/if}
                  </div>
                  <button
                    type="button"
                    on:click={() => removeVehicleExpertise(index)}
                    class="border border-rust-600/40 text-rust-400 hover:border-rust-500 hover:text-rust-300
                           font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 transition-colors shrink-0"
                  >
                    ✕ QUITAR
                  </button>
                </div>

                <!-- Nivel + notas -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NIVEL DE EXPERTISE</label>
                    <select
                      value={item.expertise_level}
                      on:change={(e) => updateVehicleExpertise(index, { expertise_level: (e.currentTarget as HTMLSelectElement).value as VehicleExpertiseLevel })}
                      class="input-industrial"
                    >
                      {#each expertiseLevelOptions as level}
                        <option value={level.value}>{level.label}</option>
                      {/each}
                    </select>
                  </div>
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NOTAS INTERNAS</label>
                    <textarea
                      rows="2"
                      value={item.notes}
                      on:input={(e) => updateVehicleExpertise(index, { notes: (e.currentTarget as HTMLTextAreaElement).value })}
                      class="input-industrial resize-none"
                    ></textarea>
                  </div>
                </div>
              </div>
            {/each}

            {#if !vehicleExpertise.length}
              <div class="px-6 py-10 text-center">
                <p class="font-mono text-xs text-steel-700 uppercase tracking-widest">SIN EXPERTISE VEHICULAR CONFIGURADO</p>
                <p class="font-mono text-[9px] text-steel-700 uppercase tracking-widest mt-1">
                  Agrega marcas o modelos para reforzar la propuesta comercial
                </p>
              </div>
            {/if}
          </div>
        </div>

      </div>

      <!-- ═══════════════════════════════
           SIDEBAR DERECHA
      ═══════════════════════════════ -->
      <aside class="space-y-6 xl:sticky xl:top-20">

        <!-- Panel resumen -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// RESUMEN DEL CATÁLOGO</p>
          </div>
          <div class="p-6 space-y-5">
            <div>
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">TALLER</p>
              <p class="font-display text-2xl text-bone uppercase leading-none">
                {customer?.company_name || customer?.full_name || 'TU TALLER'}
              </p>
            </div>

            <div class="grid grid-cols-2 gap-3 border-t border-steel-600/20 pt-5">
              <div class="border border-steel-600/25 p-3">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ACTIVOS</p>
                <p class="font-display text-2xl text-bone leading-none">{activeServices}</p>
              </div>
              <div class="border border-steel-600/25 p-3">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">CON GARANTÍA</p>
                <p class="font-display text-2xl text-bone leading-none">{warrantyServices}</p>
              </div>
            </div>

            <!-- Categorías cubiertas -->
            <div class="border-t border-steel-600/20 pt-5">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-3">CATEGORÍAS CUBIERTAS</p>
              {#if selectedCategoryNames.length}
                <div class="flex flex-wrap gap-2">
                  {#each selectedCategoryNames as name}
                    <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 px-2 py-1 text-steel-400">
                      {name}
                    </span>
                  {/each}
                </div>
              {:else}
                <p class="font-mono text-[9px] text-steel-700 uppercase tracking-widest">SIN SERVICIOS AÚN</p>
              {/if}
            </div>

            <!-- Foco vehicular -->
            <div class="border-t border-steel-600/20 pt-5">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-3">FOCO VEHICULAR</p>
              {#if vehicleExpertise.length}
                <div class="space-y-2">
                  {#each vehicleExpertise.slice(0, 5) as item}
                    <div class="flex items-center justify-between gap-2">
                      <span class="font-mono text-[10px] text-steel-400 uppercase truncate">
                        {item.label || item.modelo_nombre || item.marca_nombre || '—'}
                      </span>
                      <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 px-2 py-0.5 text-steel-500 shrink-0">
                        {item.expertise_level}
                      </span>
                    </div>
                  {/each}
                  {#if vehicleExpertise.length > 5}
                    <p class="font-mono text-[9px] text-steel-700 uppercase tracking-widest">
                      +{vehicleExpertise.length - 5} MÁS
                    </p>
                  {/if}
                </div>
              {:else}
                <p class="font-mono text-[9px] text-steel-700 uppercase tracking-widest">SIN FOCO VEHICULAR AÚN</p>
              {/if}
            </div>
          </div>
        </div>

        <!-- Panel módulos conectados -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// MÓDULOS CONECTADOS</p>
          </div>
          <div class="p-6 space-y-3">
            {#each [
              'Selector base desde ServiceCategory y Service',
              'Persistencia directa sobre WorkshopService',
              'Especialidad vehicular sobre WorkshopVehicleExpertise',
            ] as item}
              <div class="flex items-start gap-3">
                <span class="font-mono text-xs text-green-500 mt-0.5 flex-shrink-0">✓</span>
                <p class="font-mono text-[10px] text-steel-400 uppercase tracking-widest leading-relaxed">{item}</p>
              </div>
            {/each}
          </div>
        </div>

        <!-- Mensajes de estado -->
        {#if message}
          <div class="border border-green-700/50 bg-green-600/10 px-5 py-4 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
            <p class="font-mono text-[10px] text-green-400 uppercase tracking-widest leading-relaxed">{message}</p>
          </div>
        {/if}
        {#if error && !accessDenied}
          <div class="border border-rust-700/50 bg-rust-600/10 px-5 py-4 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
            <p class="font-mono text-[10px] text-rust-400 uppercase tracking-widest leading-relaxed">{error}</p>
          </div>
        {/if}

      </aside>
    </div>
  {/if}
</div>