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
  <title>Servicios del Taller | ECOMPARTS</title>
  <meta name="description" content="Configura el catalogo real del taller por categorias, servicios publicados y expertise vehicular." />
</svelte:head>

<div class="max-w-7xl mx-auto px-4 py-12 space-y-8">
  {#if loading}
    <div class="rounded-3xl bg-white p-8 shadow text-gray-500">Cargando configuracion del catalogo...</div>
  {:else if accessDenied}
    <div class="rounded-3xl bg-amber-50 border border-amber-200 p-8 text-amber-900 space-y-4">
      <div>
        <h1 class="text-2xl font-bold">Acceso no habilitado</h1>
        <p class="mt-2 text-sm">{error}</p>
      </div>
      <a href="/cliente/perfil" class="inline-flex items-center rounded-xl bg-white border border-amber-300 px-5 py-2 font-semibold hover:bg-amber-100 transition">
        Volver a mi perfil
      </a>
    </div>
  {:else}
    <section class="rounded-[2rem] bg-[linear-gradient(135deg,#0f172a_0%,#1e293b_40%,#1d4ed8_100%)] text-white shadow-xl overflow-hidden">
      <div class="px-8 py-10 md:px-10 md:py-12 grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-8 items-start">
        <div class="space-y-5">
          <div class="space-y-2">
            <p class="text-sm font-semibold uppercase tracking-[0.28em] text-sky-200">Catalogo operativo del taller</p>
            <h1 class="text-3xl md:text-5xl font-black leading-tight">Define que hace tu taller, cuanto tarda y en que vehiculos es fuerte.</h1>
            <p class="text-slate-200 max-w-3xl text-sm md:text-base">
              Esta pantalla ya trabaja con categorias, servicios y expertise vehicular del backend. Selecciona solo lo que realmente ofreces y deja la propuesta lista para publicar.
            </p>
          </div>

          <div class="flex flex-wrap gap-3">
            <a href="/taller/perfil" class="inline-flex items-center rounded-xl border border-white/20 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10 transition">
              Volver al perfil
            </a>
            <button
              type="button"
              onclick={saveCatalog}
              disabled={saving}
              class="inline-flex items-center rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-100 disabled:opacity-60 transition"
            >
              {saving ? 'Guardando...' : 'Guardar configuracion'}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="rounded-2xl bg-white/10 p-4 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-wide text-sky-200">Servicios seleccionados</p>
            <p class="mt-2 text-3xl font-black">{workshopServices.length}</p>
            <p class="mt-1 text-sm text-slate-200">{activeServices} visibles al cliente</p>
          </div>
          <div class="rounded-2xl bg-white/10 p-4 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-wide text-sky-200">Cobertura actual</p>
            <p class="mt-2 text-3xl font-black">{serviceCoverage}%</p>
            <p class="mt-1 text-sm text-slate-200">{configuredCategories.length} categorias trabajadas</p>
          </div>
          <div class="rounded-2xl bg-white/10 p-4 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-wide text-sky-200">Especializados</p>
            <p class="mt-2 text-3xl font-black">{specializedServices}</p>
            <p class="mt-1 text-sm text-slate-200">Servicios diferenciales del taller</p>
          </div>
          <div class="rounded-2xl bg-white/10 p-4 backdrop-blur-sm">
            <p class="text-xs uppercase tracking-wide text-sky-200">Expertise vehicular</p>
            <p class="mt-2 text-3xl font-black">{vehicleExpertise.length}</p>
            <p class="mt-1 text-sm text-slate-200">{publishedVehicleExpertise} con nivel pro o experto</p>
          </div>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-6 items-start">
      <div class="space-y-6">
        <section class="bg-white rounded-[2rem] shadow p-6 md:p-8 space-y-6">
          <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <p class="text-sm font-semibold uppercase tracking-wide text-blue-700">Servicios por categoria</p>
              <h2 class="text-2xl font-black text-slate-900 mt-1">Arma el catalogo real del taller</h2>
              <p class="text-sm text-slate-600 mt-2 max-w-3xl">
                Cada servicio que actives crea o actualiza un registro en WorkshopService. Aqui defines disponibilidad, rango de precio, tiempo estimado y garantia.
              </p>
            </div>
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {configuredCategories.length} de {categories.length} categorias ya tienen al menos un servicio seleccionado.
            </div>
          </div>

          <div class="space-y-5">
            {#each categories as category}
              <article class="rounded-[1.75rem] border border-slate-200 overflow-hidden bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)]">
                <div class="px-5 py-5 border-b border-slate-200 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                  <div>
                    <h3 class="text-lg font-black text-slate-900">{category.name}</h3>
                    <p class="text-sm text-slate-600 mt-1">{category.description || 'Categoria operativa disponible para el catalogo del taller.'}</p>
                  </div>
                  <div class="flex items-center gap-2 text-xs font-semibold">
                    <span class="rounded-full bg-slate-100 px-3 py-1 text-slate-700">{category.services.length} servicios base</span>
                    <span class="rounded-full bg-blue-100 px-3 py-1 text-blue-700">
                      {category.services.filter((service) => getSelectedService(service.id)).length} seleccionados
                    </span>
                  </div>
                </div>

                <div class="p-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {#each category.services as service}
                    {@const selected = getSelectedService(service.id)}
                    <div class={`rounded-[1.5rem] border p-5 transition ${selected ? 'border-blue-300 bg-blue-50/60 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                      <div class="flex flex-col gap-4 h-full">
                        <div class="flex items-start justify-between gap-3">
                          <div>
                            <div class="flex flex-wrap items-center gap-2 mb-2">
                              <h4 class="text-base font-bold text-slate-900">{service.name}</h4>
                              <span class={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${selected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'}`}>
                                {selected ? 'En catalogo' : 'Disponible'}
                              </span>
                            </div>
                            <p class="text-sm text-slate-600">{service.description || 'Servicio disponible en el catalogo base del sistema.'}</p>
                          </div>
                          <button
                            type="button"
                            onclick={() => toggleService(category, service)}
                            class={`rounded-xl px-4 py-2 text-sm font-semibold transition ${selected ? 'border border-red-200 text-red-700 hover:bg-red-50' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                          >
                            {selected ? 'Quitar' : 'Agregar'}
                          </button>
                        </div>

                        <div class="flex flex-wrap gap-2 text-xs font-semibold">
                          <span class="rounded-full bg-white border border-slate-200 px-3 py-1 text-slate-700">{serviceTypeLabels[service.service_type] || service.service_type}</span>
                          <span class="rounded-full bg-white border border-slate-200 px-3 py-1 text-slate-700">Complejidad {complexityLabels[service.complexity] || service.complexity}</span>
                        </div>

                        {#if selected}
                          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-blue-200/70">
                            <label class="text-sm text-slate-700">
                              <span class="block mb-1 font-medium">Precio minimo</span>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={selected.min_price ?? ''}
                                oninput={(event) => updatePrice(service.id, 'min_price', (event.currentTarget as HTMLInputElement).value)}
                                class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="120.00"
                              />
                            </label>
                            <label class="text-sm text-slate-700">
                              <span class="block mb-1 font-medium">Precio maximo</span>
                              <input
                                type="number"
                                min="0"
                                step="0.01"
                                value={selected.max_price ?? ''}
                                oninput={(event) => updatePrice(service.id, 'max_price', (event.currentTarget as HTMLInputElement).value)}
                                class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="180.00"
                              />
                            </label>
                            <label class="text-sm text-slate-700">
                              <span class="block mb-1 font-medium">Duracion estimada</span>
                              <input
                                type="number"
                                min="15"
                                step="15"
                                value={selected.estimated_time_min}
                                oninput={(event) => updateWorkshopService(service.id, { estimated_time_min: Number((event.currentTarget as HTMLInputElement).value) || 15 })}
                                class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                              />
                            </label>
                            <label class="text-sm text-slate-700">
                              <span class="block mb-1 font-medium">Moneda</span>
                              <input
                                value={selected.currency}
                                maxlength="10"
                                oninput={(event) => updateWorkshopService(service.id, { currency: (event.currentTarget as HTMLInputElement).value.toUpperCase() || 'PEN' })}
                                class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                              />
                            </label>
                          </div>

                          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-sm text-slate-700">
                            <label class="flex items-center gap-3 rounded-2xl border border-white/80 bg-white px-4 py-3 cursor-pointer">
                              <input type="checkbox" checked={selected.available} onchange={(event) => updateWorkshopService(service.id, { available: (event.currentTarget as HTMLInputElement).checked })} class="w-4 h-4 text-blue-600 rounded" />
                              <span>Visible al cliente</span>
                            </label>
                            <label class="flex items-center gap-3 rounded-2xl border border-white/80 bg-white px-4 py-3 cursor-pointer">
                              <input type="checkbox" checked={selected.is_specialized} onchange={(event) => updateWorkshopService(service.id, { is_specialized: (event.currentTarget as HTMLInputElement).checked })} class="w-4 h-4 text-blue-600 rounded" />
                              <span>Servicio diferencial</span>
                            </label>
                          </div>

                          <div class="rounded-2xl border border-white/80 bg-white p-4 space-y-3">
                            <label class="flex items-center gap-3 text-sm text-slate-700 cursor-pointer">
                              <input type="checkbox" checked={selected.has_warranty} onchange={(event) => updateWorkshopService(service.id, { has_warranty: (event.currentTarget as HTMLInputElement).checked })} class="w-4 h-4 text-blue-600 rounded" />
                              <span>Este servicio incluye garantia</span>
                            </label>

                            {#if selected.has_warranty}
                              <label class="text-sm text-slate-700 block">
                                <span class="block mb-1 font-medium">Dias de garantia</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="1"
                                  value={selected.warranty_days}
                                  oninput={(event) => updateWorkshopService(service.id, { warranty_days: Number((event.currentTarget as HTMLInputElement).value) || 0 })}
                                  class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </label>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </article>
            {/each}
          </div>
        </section>

        <section class="bg-white rounded-[2rem] shadow p-6 md:p-8 space-y-6">
          <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
            <div>
              <p class="text-sm font-semibold uppercase tracking-wide text-emerald-700">Expertise vehicular</p>
              <h2 class="text-2xl font-black text-slate-900 mt-1">Define en que marcas o modelos eres fuerte</h2>
              <p class="text-sm text-slate-600 mt-2 max-w-3xl">
                Esta configuracion alimenta WorkshopVehicleExpertise. Puedes trabajar a nivel de marca o bajar a modelo cuando quieras comunicar especializacion real.
              </p>
            </div>
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              {vehicleExpertise.length} focos vehiculares registrados
            </div>
          </div>

          <div class="rounded-[1.75rem] border border-emerald-200 bg-emerald-50/70 p-5 space-y-4">
            <div class="flex flex-wrap gap-3">
              <button
                type="button"
                onclick={() => void handleGranularityChange('marca')}
                class={`rounded-xl px-4 py-2 text-sm font-semibold transition ${vehiclePicker.granularity === 'marca' ? 'bg-emerald-700 text-white' : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'}`}
              >
                Expertise por marca
              </button>
              <button
                type="button"
                onclick={() => void handleGranularityChange('modelo')}
                class={`rounded-xl px-4 py-2 text-sm font-semibold transition ${vehiclePicker.granularity === 'modelo' ? 'bg-emerald-700 text-white' : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'}`}
              >
                Expertise por modelo
              </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-[1fr,1fr,0.8fr] gap-4">
              <label class="text-sm text-slate-700">
                <span class="block mb-1 font-medium">Marca</span>
                <select
                  value={vehiclePicker.marcaId}
                  onchange={(event) => void handleBrandChange((event.currentTarget as HTMLSelectElement).value)}
                  class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Selecciona una marca</option>
                  {#each vehicleBrands as brand}
                    <option value={brand.id}>{brand.nombre}</option>
                  {/each}
                </select>
              </label>

              {#if vehiclePicker.granularity === 'modelo'}
                <label class="text-sm text-slate-700">
                  <span class="block mb-1 font-medium">Modelo</span>
                  <select
                    value={vehiclePicker.modeloId}
                    onchange={(event) => vehiclePicker = { ...vehiclePicker, modeloId: (event.currentTarget as HTMLSelectElement).value }}
                    disabled={!vehiclePicker.marcaId || loadingVehicleModels}
                    class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 disabled:bg-slate-100 disabled:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="">{loadingVehicleModels ? 'Cargando modelos...' : 'Selecciona un modelo'}</option>
                    {#each currentBrandModels as model}
                      <option value={model.id}>{model.nombre}</option>
                    {/each}
                  </select>
                </label>
              {/if}

              <label class="text-sm text-slate-700">
                <span class="block mb-1 font-medium">Nivel</span>
                <select
                  value={vehiclePicker.expertiseLevel}
                  onchange={(event) => vehiclePicker = { ...vehiclePicker, expertiseLevel: (event.currentTarget as HTMLSelectElement).value as VehicleExpertiseLevel }}
                  class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {#each expertiseLevelOptions as level}
                    <option value={level.value}>{level.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <label class="text-sm text-slate-700 block">
              <span class="block mb-1 font-medium">Notas internas</span>
              <textarea
                rows="3"
                bind:value={vehiclePicker.notes}
                class="w-full rounded-2xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Ej: alto volumen de Toyota Corolla, diagnosticos frecuentes de caja CVT, etc."
              ></textarea>
            </label>

            <div class="flex justify-end">
              <button type="button" onclick={addVehicleExpertise} class="rounded-xl bg-emerald-700 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800 transition">
                Agregar expertise
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {#each vehicleExpertise as item, index}
              <div class="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5 space-y-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <div class="flex flex-wrap items-center gap-2">
                      <h3 class="text-base font-black text-slate-900">{item.label || item.modelo_nombre || item.marca_nombre || 'Vehiculo configurado'}</h3>
                      <span class="rounded-full bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-semibold text-slate-600">{item.granularity === 'modelo' ? 'Modelo' : 'Marca'}</span>
                    </div>
                    <p class="text-sm text-slate-600 mt-1">{item.modelo_nombre ? `${item.marca_nombre || ''} ${item.modelo_nombre}`.trim() : item.marca_nombre || 'Expertise vehicular del taller.'}</p>
                  </div>
                  <button type="button" onclick={() => removeVehicleExpertise(index)} class="rounded-xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 transition">
                    Quitar
                  </button>
                </div>

                <label class="text-sm text-slate-700 block">
                  <span class="block mb-1 font-medium">Nivel de expertise</span>
                  <select
                    value={item.expertise_level}
                    onchange={(event) => updateVehicleExpertise(index, { expertise_level: (event.currentTarget as HTMLSelectElement).value as VehicleExpertiseLevel })}
                    class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  >
                    {#each expertiseLevelOptions as level}
                      <option value={level.value}>{level.label}</option>
                    {/each}
                  </select>
                </label>

                <label class="text-sm text-slate-700 block">
                  <span class="block mb-1 font-medium">Notas internas</span>
                  <textarea
                    rows="3"
                    value={item.notes}
                    oninput={(event) => updateVehicleExpertise(index, { notes: (event.currentTarget as HTMLTextAreaElement).value })}
                    class="w-full rounded-2xl border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  ></textarea>
                </label>

                {#if item.total_jobs}
                  <div class="rounded-2xl bg-white border border-slate-200 px-4 py-3 text-sm text-slate-600">
                    {item.total_jobs} trabajos registrados en este foco vehicular.
                  </div>
                {/if}
              </div>
            {/each}

            {#if !vehicleExpertise.length}
              <div class="lg:col-span-2 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-sm text-slate-500">
                Aun no has configurado expertise vehicular. Agrega marcas o modelos para reforzar la propuesta comercial del taller.
              </div>
            {/if}
          </div>
        </section>
      </div>

      <aside class="space-y-6 xl:sticky xl:top-6">
        <section class="rounded-[2rem] bg-[#0f172a] text-white p-6 shadow space-y-5">
          <div>
            <p class="text-sm font-semibold uppercase tracking-wide text-cyan-300">Resumen listo para publicar</p>
            <h2 class="text-2xl font-black mt-2">{customer?.company_name || customer?.full_name || 'Tu taller'}</h2>
            <p class="text-sm text-slate-300 mt-2">Selecciona solo lo que el taller puede cumplir bien. Menos volumen y mejor precision suele convertir mejor.</p>
          </div>

          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-2xl bg-white/10 p-4">
              <p class="text-slate-300">Activos</p>
              <p class="mt-1 text-2xl font-black">{activeServices}</p>
            </div>
            <div class="rounded-2xl bg-white/10 p-4">
              <p class="text-slate-300">Garantia</p>
              <p class="mt-1 text-2xl font-black">{warrantyServices}</p>
            </div>
          </div>

          <div class="rounded-2xl bg-white/10 p-4 space-y-3">
            <p class="text-sm font-semibold text-white">Categorias cubiertas</p>
            {#if selectedCategoryNames.length}
              <div class="flex flex-wrap gap-2">
                {#each selectedCategoryNames as categoryName}
                  <span class="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-slate-100">{categoryName}</span>
                {/each}
              </div>
            {:else}
              <p class="text-sm text-slate-300">Todavia no has agregado servicios al catalogo.</p>
            {/if}
          </div>

          <div class="rounded-2xl bg-white/10 p-4 space-y-3">
            <p class="text-sm font-semibold text-white">Foco vehicular</p>
            {#if vehicleExpertise.length}
              <div class="space-y-2">
                {#each vehicleExpertise.slice(0, 5) as item}
                  <div class="flex items-center justify-between gap-3 text-sm">
                    <span class="text-slate-100">{item.label || item.modelo_nombre || item.marca_nombre}</span>
                    <span class="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-200">{item.expertise_level}</span>
                  </div>
                {/each}
              </div>
            {:else}
              <p class="text-sm text-slate-300">Agrega al menos una marca o modelo para reforzar la propuesta del taller.</p>
            {/if}
          </div>
        </section>

        <section class="bg-white rounded-[2rem] p-6 shadow space-y-4">
          <div>
            <h2 class="text-lg font-black text-slate-900">Como queda conectado</h2>
            <p class="text-sm text-slate-600 mt-2">Esta pantalla ya no es plantilla visual. Guarda sobre modelos reales del backend:</p>
          </div>
          <ul class="space-y-3 text-sm text-slate-700">
            <li class="flex gap-3"><span class="text-emerald-600">✓</span><span>Selector base desde ServiceCategory y Service.</span></li>
            <li class="flex gap-3"><span class="text-emerald-600">✓</span><span>Persistencia directa sobre WorkshopService.</span></li>
            <li class="flex gap-3"><span class="text-emerald-600">✓</span><span>Especialidad vehicular sobre WorkshopVehicleExpertise.</span></li>
          </ul>
        </section>

        {#if message}
          <div class="bg-green-50 text-green-700 rounded-[1.5rem] p-4 text-sm shadow-sm">{message}</div>
        {/if}
        {#if error}
          <div class="bg-red-50 text-red-700 rounded-[1.5rem] p-4 text-sm shadow-sm">{error}</div>
        {/if}
      </aside>
    </div>
  {/if}
</div>