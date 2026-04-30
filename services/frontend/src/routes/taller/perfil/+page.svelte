<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import type {
    Customer,
    WorkshopProfile,
    WorkshopProfileLocation,
    WorkshopProfileSchedule,
  } from '$lib/api/types';
  import {
    getBusinessActivityLabel,
    isWorkshopBusinessActivity,
  } from '$lib/constants/customer';

  type LocationFormItem = WorkshopProfileLocation & {
    provinceOptions: string[];
    districtOptions: string[];
  };

  type ScheduleFormItem = WorkshopProfileSchedule & {
    day_label: string;
  };

  const WEEK_DAYS = [
    { value: 0, label: 'Lunes' },
    { value: 1, label: 'Martes' },
    { value: 2, label: 'Miércoles' },
    { value: 3, label: 'Jueves' },
    { value: 4, label: 'Viernes' },
    { value: 5, label: 'Sábado' },
    { value: 6, label: 'Domingo' },
  ];

  let customer: Customer | null = null;
  let workshopProfile: WorkshopProfile | null = null;
  let loading = true;
  let saving = false;
  let accessDenied = false;
  let message = '';
  let error = '';

  let departmentOptions: string[] = [];
  let locations: LocationFormItem[] = [createEmptyLocation(true)];
  let schedules: ScheduleFormItem[] = createDefaultSchedules();

  let form = {
    workshopName: '',
    headline: '',
    description: '',
    phone: '',
    whatsapp: '',
    website: '',
    pickupDelivery: true,
    emergencyService: false,
    courtesyInspection: true,
  };

  function createEmptyLocation(isMain = false): LocationFormItem {
    return {
      name: isMain ? 'Sede principal' : '',
      address: '',
      district: '',
      province: '',
      department: '',
      latitude: '0.000000',
      longitude: '0.000000',
      is_main: isMain,
      provinceOptions: [],
      districtOptions: [],
    };
  }

  function createDefaultSchedules(): ScheduleFormItem[] {
    return WEEK_DAYS.map((day) => ({
      day_of_week: day.value,
      day_label: day.label,
      start_time: day.value === 6 ? '09:00' : '08:00',
      end_time: day.value === 5 ? '13:00' : '18:00',
      is_active: day.value !== 6,
    }));
  }

  function buildLocations(profile: WorkshopProfile): LocationFormItem[] {
    if (!profile.locations.length) {
      return [createEmptyLocation(true)];
    }

    return profile.locations.map((location, index) => ({
      ...location,
      name: location.name || (location.is_main && index === 0 ? 'Sede principal' : ''),
      latitude: location.latitude ?? '0.000000',
      longitude: location.longitude ?? '0.000000',
      provinceOptions: [],
      districtOptions: [],
    }));
  }

  function buildSchedules(profile: WorkshopProfile): ScheduleFormItem[] {
    const firstScheduleByDay = new Map<number, WorkshopProfileSchedule>();

    for (const schedule of profile.schedules) {
      if (!firstScheduleByDay.has(schedule.day_of_week)) {
        firstScheduleByDay.set(schedule.day_of_week, schedule);
      }
    }

    return WEEK_DAYS.map((day) => {
      const schedule = firstScheduleByDay.get(day.value);
      return {
        day_of_week: day.value,
        day_label: day.label,
        start_time: schedule?.start_time || (day.value === 6 ? '09:00' : '08:00'),
        end_time: schedule?.end_time || (day.value === 5 ? '13:00' : '18:00'),
        is_active: schedule?.is_active ?? day.value !== 6,
      };
    });
  }

  async function hydrateLocationOptions(index: number) {
    const location = locations[index];
    if (!location) {
      return;
    }

    try {
      const options = await api.services.locationOptions(
        location.department || undefined,
        location.province || undefined,
      );

      locations = locations.map((item, itemIndex) => itemIndex === index
        ? {
            ...item,
            provinceOptions: options.provinces,
            districtOptions: options.districts,
          }
        : item);
    } catch (e) {
      locations = locations.map((item, itemIndex) => itemIndex === index
        ? { ...item, provinceOptions: [], districtOptions: [] }
        : item);
    }
  }

  async function hydrateAllLocationOptions() {
    await Promise.all(locations.map((_, index) => hydrateLocationOptions(index)));
  }

  function setMainLocation(index: number) {
    locations = locations.map((location, locationIndex) => ({
      ...location,
      is_main: locationIndex === index,
      name: locationIndex === index && !location.name ? 'Sede principal' : location.name,
    }));
  }

  function addLocation() {
    locations = [...locations, createEmptyLocation(false)];
  }

  function removeLocation(index: number) {
    const nextLocations = locations.filter((_, locationIndex) => locationIndex !== index);

    if (!nextLocations.length) {
      locations = [createEmptyLocation(true)];
      return;
    }

    if (!nextLocations.some((location) => location.is_main)) {
      nextLocations[0] = {
        ...nextLocations[0],
        is_main: true,
        name: nextLocations[0].name || 'Sede principal',
      };
    }

    locations = nextLocations;
  }

  async function handleDepartmentChange(index: number, department: string) {
    locations = locations.map((location, locationIndex) => locationIndex === index
      ? {
          ...location,
          department,
          province: '',
          district: '',
          provinceOptions: [],
          districtOptions: [],
        }
      : location);

    await hydrateLocationOptions(index);
  }

  async function handleProvinceChange(index: number, province: string) {
    locations = locations.map((location, locationIndex) => locationIndex === index
      ? {
          ...location,
          province,
          district: '',
          districtOptions: [],
        }
      : location);

    await hydrateLocationOptions(index);
  }

  function updateSchedule(index: number, patch: Partial<ScheduleFormItem>) {
    schedules = schedules.map((schedule, scheduleIndex) => scheduleIndex === index
      ? { ...schedule, ...patch }
      : schedule);
  }

  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }

    try {
      customer = await api.customer.getProfile(token);
      auth.customer.set(customer);

      if (customer.customer_type !== 'company' || !isWorkshopBusinessActivity(customer.business_activity)) {
        accessDenied = true;
        error = 'Este módulo solo está disponible para empresas con actividad económica de taller mecánico.';
        return;
      }

      const [locationSeed, profile] = await Promise.all([
        api.services.locationOptions(),
        api.services.getWorkshopProfile(token),
      ]);

      departmentOptions = locationSeed.departments;
      workshopProfile = profile;
      locations = buildLocations(profile);
      schedules = buildSchedules(profile);
      await hydrateAllLocationOptions();

      form = {
        ...form,
        workshopName: profile.name || customer.company_name || customer.full_name || '',
        phone: profile.phone || customer.phone || '',
        whatsapp: profile.whatsapp || '',
        website: profile.website || '',
        headline: profile.description || (customer.company_name
          ? `${customer.company_name} especializado en atención confiable y rápida.`
          : 'Taller especializado en servicios automotrices de confianza.'),
        description: profile.large_description || `Base del negocio: ${getBusinessActivityLabel(customer.business_activity)}. Configura aquí la propuesta comercial inicial de tu taller.`,
      };
    } catch (e) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        accessDenied = true;
        error = 'Este módulo solo está disponible para empresas con actividad económica de taller mecánico.';
      } else {
        error = 'No se pudo cargar la base del perfil empresa.';
      }
    } finally {
      loading = false;
    }
  });

  async function saveTemplate() {
    saving = true;
    message = '';
    error = '';

    try {
      const token = auth.getAccessToken();
      if (!token) {
        window.location.href = '/login';
        return;
      }

      const payload: Partial<WorkshopProfile> = {
        name: form.workshopName,
        phone: form.phone,
        whatsapp: form.whatsapp,
        website: form.website,
        description: form.headline,
        large_description: form.description,
        locations: locations.map(({ provinceOptions, districtOptions, ...location }) => ({
          ...location,
          latitude: location.latitude || '0.000000',
          longitude: location.longitude || '0.000000',
        })),
        schedules: schedules.map(({ day_label, ...schedule }) => schedule),
      };

      workshopProfile = await api.services.updateWorkshopProfile(token, payload);
      locations = buildLocations(workshopProfile);
      schedules = buildSchedules(workshopProfile);
      await hydrateAllLocationOptions();

      if (customer) {
        customer = {
          ...customer,
          company_name: workshopProfile.name,
          phone: workshopProfile.phone,
        };
        auth.customer.set(customer);
      }

      message = 'Perfil del taller guardado. Las sedes y horarios ya quedaron sincronizados con el backend.';
    } catch (e) {
      error = 'No se pudo guardar el perfil del taller.';
    } finally {
      saving = false;
    }
  }

  $: mainLocation = locations.find((location) => location.is_main) || locations[0] || null;
  $: activeDays = schedules.filter((schedule) => schedule.is_active).length;
  $: additionalLocations = Math.max(locations.length - 1, 0);
</script>

<svelte:head>
  <title>Perfil de Taller | ECOMPARTS</title>
  <meta name="description" content="Configura la presencia comercial de tu taller a partir del perfil empresa del customer." />
</svelte:head>

<div class="max-w-6xl mx-auto px-4 py-12 space-y-8">
  <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
    <div>
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900">Perfil de taller</h1>
      <p class="text-gray-600 mt-2 max-w-3xl">
        Completa la información comercial, registra una o varias sedes y define tus horarios de atención para dejar el perfil operativo.
      </p>
    </div>
    <div class="flex flex-wrap gap-3">
      <a href="/servicios" class="px-5 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition">Ver landing de servicios</a>
      <a href="/taller/servicios" class="px-5 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">Configurar catálogo</a>
    </div>
  </div>

  {#if loading}
    <div class="rounded-2xl bg-white p-8 shadow text-gray-500">Cargando base del perfil...</div>
  {:else if accessDenied}
    <div class="rounded-2xl bg-amber-50 border border-amber-200 p-8 text-amber-900 space-y-4">
      <div>
        <h2 class="text-2xl font-bold">Acceso no habilitado</h2>
        <p class="mt-2 text-sm">
          Este espacio se activa solo para empresas cuya actividad económica sea Taller mecánico.
        </p>
      </div>
      <a href="/cliente/perfil" class="inline-flex items-center rounded-lg bg-white border border-amber-300 px-5 py-2 font-semibold hover:bg-amber-100 transition">
        Volver a mi perfil
      </a>
    </div>
  {:else}
    <div class="grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-6">
      <section class="bg-white rounded-2xl shadow p-8 space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pb-6 border-b border-gray-100">
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide">Perfil Customer</p>
            <p class="font-semibold text-gray-900">{customer?.customer_id || 'Pendiente'}</p>
          </div>
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide">Documento</p>
            <p class="font-semibold text-gray-900">{customer?.document_type || 'RUC'} · {customer?.document_number || 'Sin completar'}</p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="workshopName">Nombre comercial</label>
            <input id="workshopName" bind:value={form.workshopName} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="phone">Teléfono principal</label>
            <input id="phone" bind:value={form.phone} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="whatsapp">WhatsApp</label>
            <input id="whatsapp" bind:value={form.whatsapp} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="website">Sitio web</label>
            <input id="website" bind:value={form.website} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="https://..." />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="headline">Titular comercial</label>
            <input id="headline" bind:value={form.headline} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="description">Descripción</label>
            <textarea id="description" bind:value={form.description} rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
          </div>
        </div>

        <section class="space-y-5 pt-2 border-t border-gray-100">
          <div class="flex items-center justify-between gap-4">
            <div>
              <p class="text-sm font-medium text-gray-700">Sedes del taller</p>
              <p class="text-sm text-gray-500">Puedes registrar una sede principal y sucursales con departamento, provincia y distrito.</p>
            </div>
            <button
              type="button"
              onclick={addLocation}
              class="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
            >
              Agregar sede
            </button>
          </div>

          <datalist id="department-options">
            {#each departmentOptions as department}
              <option value={department}></option>
            {/each}
          </datalist>

          <div class="space-y-4">
            {#each locations as location, index}
              <div class="rounded-2xl border border-gray-200 p-5 space-y-4">
                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-gray-900">{location.name || `Sede ${index + 1}`}</p>
                    <p class="text-xs text-gray-500">{location.is_main ? 'Ubicación principal visible para el cliente.' : 'Sucursal adicional del taller.'}</p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onclick={() => setMainLocation(index)}
                      class={`rounded-lg px-3 py-2 text-sm font-medium transition ${location.is_main ? 'bg-blue-600 text-white' : 'border border-gray-300 text-gray-700 hover:bg-gray-50'}`}
                    >
                      {location.is_main ? 'Principal' : 'Marcar principal'}
                    </button>
                    {#if locations.length > 1}
                      <button
                        type="button"
                        onclick={() => removeLocation(index)}
                        class="rounded-lg border border-red-200 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition"
                      >
                        Eliminar
                      </button>
                    {/if}
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1" for={`location-name-${index}`}>Nombre de sede</label>
                    <input id={`location-name-${index}`} bind:value={location.name} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ej: Sede San Luis" />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1" for={`department-${index}`}>Departamento</label>
                    <input
                      id={`department-${index}`}
                      list="department-options"
                      bind:value={location.department}
                      onchange={() => void handleDepartmentChange(index, location.department)}
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Ej: Lima"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1" for={`province-${index}`}>Provincia</label>
                    <input
                      id={`province-${index}`}
                      list={`province-options-${index}`}
                      bind:value={location.province}
                      onchange={() => void handleProvinceChange(index, location.province)}
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Ej: Lima"
                    />
                    <datalist id={`province-options-${index}`}>
                      {#each location.provinceOptions as province}
                        <option value={province}></option>
                      {/each}
                    </datalist>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1" for={`district-${index}`}>Distrito</label>
                    <input
                      id={`district-${index}`}
                      list={`district-options-${index}`}
                      bind:value={location.district}
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="Ej: San Luis"
                    />
                    <datalist id={`district-options-${index}`}>
                      {#each location.districtOptions as district}
                        <option value={district}></option>
                      {/each}
                    </datalist>
                  </div>
                  <div class="md:col-span-2">
                    <label class="block text-sm font-medium text-gray-700 mb-1" for={`address-${index}`}>Dirección</label>
                    <input id={`address-${index}`} bind:value={location.address} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Av., calle, lote o referencia principal" />
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </section>

        <section class="space-y-4 pt-2 border-t border-gray-100">
          <div>
            <p class="text-sm font-medium text-gray-700">Horarios de atención</p>
            <p class="text-sm text-gray-500">Esta configuración se guarda en `WorkshopSchedule` y luego podrá ampliarse con bloques más detallados.</p>
          </div>

          <div class="space-y-3">
            {#each schedules as schedule, index}
              <div class="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr,1fr] gap-3 items-center rounded-xl border border-gray-200 p-4">
                <div>
                  <p class="font-medium text-gray-900">{schedule.day_label}</p>
                  <p class="text-xs text-gray-500">{schedule.is_active ? 'Atención habilitada' : 'Sin atención al público'}</p>
                </div>
                <label class="inline-flex items-center gap-3 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={schedule.is_active}
                    onchange={(event) => updateSchedule(index, { is_active: (event.currentTarget as HTMLInputElement).checked })}
                    class="w-4 h-4 text-blue-600 rounded"
                  />
                  Abierto
                </label>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1" for={`start-${index}`}>Apertura</label>
                  <input
                    id={`start-${index}`}
                    type="time"
                    value={schedule.start_time}
                    disabled={!schedule.is_active}
                    onchange={(event) => updateSchedule(index, { start_time: (event.currentTarget as HTMLInputElement).value })}
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100 disabled:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 mb-1" for={`end-${index}`}>Cierre</label>
                  <input
                    id={`end-${index}`}
                    type="time"
                    value={schedule.end_time}
                    disabled={!schedule.is_active}
                    onchange={(event) => updateSchedule(index, { end_time: (event.currentTarget as HTMLInputElement).value })}
                    class="w-full border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100 disabled:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            {/each}
          </div>
        </section>

        <div class="space-y-3 pt-2 border-t border-gray-100">
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.pickupDelivery} class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm text-gray-700">Recojo y entrega coordinada</span>
          </label>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.courtesyInspection} class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm text-gray-700">Inspección de cortesía en diagnóstico</span>
          </label>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.emergencyService} class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm text-gray-700">Atención prioritaria o emergencias</span>
          </label>
        </div>

        {#if message}
          <div class="bg-green-50 text-green-700 rounded-lg p-3 text-sm">{message}</div>
        {/if}
        {#if error}
          <div class="bg-red-50 text-red-700 rounded-lg p-3 text-sm">{error}</div>
        {/if}

        <button
          type="button"
          onclick={saveTemplate}
          disabled={saving}
          class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-6 py-3 rounded-lg transition"
        >
          {saving ? 'Guardando...' : 'Guardar plantilla del taller'}
        </button>
      </section>

      <aside class="space-y-6">
        <section class="bg-slate-900 text-white rounded-2xl p-6 shadow">
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-200 mb-2">Resumen visible</p>
          <h2 class="text-2xl font-bold mb-2">{form.workshopName || 'Tu taller'}</h2>
          <p class="text-slate-300 text-sm mb-4">{form.headline}</p>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-xl bg-white/10 p-3">
              <p class="text-slate-300">Sedes registradas</p>
              <p class="font-semibold">{locations.length}</p>
            </div>
            <div class="rounded-xl bg-white/10 p-3">
              <p class="text-slate-300">Días activos</p>
              <p class="font-semibold">{activeDays}</p>
            </div>
          </div>
          {#if mainLocation}
            <div class="mt-4 rounded-xl bg-white/10 p-4 text-sm space-y-1">
              <p class="text-slate-300">Sede principal</p>
              <p class="font-semibold">{mainLocation.name || 'Sede principal'}</p>
              <p>{mainLocation.address}</p>
              <p class="text-slate-300">{mainLocation.district}, {mainLocation.province}, {mainLocation.department}</p>
            </div>
          {/if}
        </section>

        <section class="bg-white rounded-2xl p-6 shadow space-y-4">
          <div>
            <p class="text-sm font-semibold text-gray-900">Bloques siguientes</p>
            <p class="text-sm text-gray-600">Esta plantilla deja listos los siguientes módulos para conectar:</p>
          </div>
          <ul class="space-y-3 text-sm text-gray-700">
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Sincronización de `Workshop` con customer empresarial.</span></li>
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Registro de múltiples sedes con `WorkshopLocation`.</span></li>
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Horario semanal base con `WorkshopSchedule`.</span></li>
          </ul>
          {#if additionalLocations > 0}
            <div class="rounded-xl bg-slate-50 p-4 text-sm text-gray-600">
              Además de la sede principal, ya tienes {additionalLocations} {additionalLocations === 1 ? 'sede adicional lista' : 'sedes adicionales listas'} para el perfil público.
            </div>
          {/if}
          <a href="/taller/servicios" class="inline-flex items-center font-semibold text-blue-600 hover:text-blue-700">
            Continuar con catálogo de servicios →
          </a>
        </section>
      </aside>
    </div>
  {/if}
</div>