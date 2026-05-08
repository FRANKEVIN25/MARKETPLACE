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
        pickup_delivery: form.pickupDelivery,
        emergency_service: form.emergencyService,
        courtesy_inspection: form.courtesyInspection,
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
  <title>Perfil de Taller — ECOMPARTS</title>
  <meta name="description" content="Configura la presencia comercial de tu taller: sedes, horarios y datos de contacto." />
</svelte:head>

<div class="container-responsive py-10">

  <!-- ── Header ── -->
  <div class="border-b border-steel-600/25 pb-6 mb-8 flex items-start justify-between gap-4 flex-wrap">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// MI TALLER / PERFIL</p>
      <h1 class="font-display text-5xl text-bone uppercase leading-none">PERFIL DE TALLER</h1>
      <p class="font-mono text-xs text-steel-500 mt-2 uppercase tracking-widest">Información comercial, sedes y horarios de atención</p>
    </div>
    <div class="flex flex-wrap gap-3 shrink-0 mt-1">
      <a href="/servicios" class="btn-ghost">VER SERVICIOS</a>
      <a href="/taller/servicios" class="btn-outline">CATÁLOGO →</a>
    </div>
  </div>

  {#if loading}
    <!-- Loading -->
    <div class="bg-iron-900 border border-steel-600/25 p-16 text-center">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO PERFIL DEL TALLER...</p>
    </div>

  {:else if accessDenied}
    <!-- Access denied -->
    <div class="border border-rust-700/50 bg-rust-600/10 p-8"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// ACCESO NO HABILITADO</p>
      <h2 class="font-display text-3xl text-bone uppercase mb-3">MÓDULO NO DISPONIBLE</h2>
      <p class="font-mono text-xs text-steel-500 leading-relaxed mb-6 max-w-xl">
        Este módulo se activa únicamente para empresas cuya actividad económica sea Taller mecánico.
        Cambia la actividad en tu perfil de cliente para habilitarlo.
      </p>
      <a href="/cliente/perfil" class="btn-outline">← VOLVER A MI PERFIL</a>
    </div>

  {:else}
    <div class="grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-6">

      <!-- ════════════════════════════════
           COLUMNA IZQUIERDA — Formulario
      ════════════════════════════════ -->
      <div class="space-y-6">

        <!-- Datos del cliente (solo lectura) -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS DEL CLIENTE</p>
          </div>
          <div class="grid grid-cols-2 divide-x divide-steel-600/20">
            <div class="px-6 py-5">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ID CLIENTE</p>
              <p class="font-mono text-sm text-bone">{customer?.customer_id || '—'}</p>
            </div>
            <div class="px-6 py-5">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">DOCUMENTO</p>
              <p class="font-mono text-sm text-bone">{customer?.document_type || 'RUC'} · {customer?.document_number || 'Sin completar'}</p>
            </div>
          </div>
        </div>

        <!-- Datos comerciales -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS COMERCIALES</p>
          </div>
          <div class="p-6 space-y-5">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="workshopName">
                  // NOMBRE COMERCIAL
                </label>
                <input id="workshopName" bind:value={form.workshopName} class="input-industrial" />
              </div>
              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="phone">
                  // TELÉFONO PRINCIPAL
                </label>
                <input id="phone" type="tel" bind:value={form.phone} class="input-industrial" />
              </div>
              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="whatsapp">
                  // WHATSAPP
                </label>
                <input id="whatsapp" type="tel" bind:value={form.whatsapp} class="input-industrial" />
              </div>
              <div>
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="website">
                  // SITIO WEB
                </label>
                <input id="website" type="url" bind:value={form.website} placeholder="https://..." class="input-industrial" />
              </div>
              <div class="md:col-span-2">
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="headline">
                  // TITULAR COMERCIAL
                </label>
                <input id="headline" bind:value={form.headline} class="input-industrial" />
              </div>
              <div class="md:col-span-2">
                <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="description">
                  // DESCRIPCIÓN
                </label>
                <textarea
                  id="description"
                  bind:value={form.description}
                  rows="4"
                  class="input-industrial resize-none"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- Sedes del taller -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between gap-4">
            <div>
              <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SEDES DEL TALLER</p>
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mt-0.5">Sede principal y sucursales</p>
            </div>
            <button
              type="button"
              on:click={addLocation}
              class="btn-ghost"
            >
              + AGREGAR SEDE
            </button>
          </div>

          <datalist id="department-options">
            {#each departmentOptions as department}
              <option value={department}></option>
            {/each}
          </datalist>

          <div class="divide-y divide-steel-600/20">
            {#each locations as location, index}
              <div class="p-6 space-y-5">

                <!-- Sede header -->
                <div class="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <p class="font-mono text-xs text-bone uppercase tracking-widest">
                      {location.name || `SEDE ${index + 1}`}
                    </p>
                    <p class="font-mono text-[9px] mt-0.5 uppercase tracking-widest {location.is_main ? 'text-rust-600' : 'text-steel-600'}">
                      {location.is_main ? '★ UBICACIÓN PRINCIPAL' : 'SUCURSAL ADICIONAL'}
                    </p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    {#if !location.is_main}
                      <button
                        type="button"
                        on:click={() => setMainLocation(index)}
                        class="btn-ghost"
                      >
                        MARCAR PRINCIPAL
                      </button>
                    {/if}
                    {#if locations.length > 1}
                      <button
                        type="button"
                        on:click={() => removeLocation(index)}
                        class="font-mono text-[10px] uppercase tracking-widest text-rust-600 hover:text-rust-400
                               border border-rust-700/50 px-3 py-2 hover:border-rust-500 transition-colors"
                      >
                        ELIMINAR
                      </button>
                    {/if}
                  </div>
                </div>

                <!-- Sede fields -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for={`location-name-${index}`}>
                      // NOMBRE DE SEDE
                    </label>
                    <input
                      id={`location-name-${index}`}
                      bind:value={location.name}
                      placeholder="Ej: Sede San Luis"
                      class="input-industrial"
                    />
                  </div>
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for={`department-${index}`}>
                      // DEPARTAMENTO
                    </label>
                    <input
                      id={`department-${index}`}
                      list="department-options"
                      bind:value={location.department}
                      on:change={() => handleDepartmentChange(index, location.department)}
                      placeholder="Ej: Lima"
                      class="input-industrial"
                    />
                  </div>
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for={`province-${index}`}>
                      // PROVINCIA
                    </label>
                    <input
                      id={`province-${index}`}
                      list={`province-options-${index}`}
                      bind:value={location.province}
                      on:change={() => handleProvinceChange(index, location.province)}
                      placeholder="Ej: Lima"
                      class="input-industrial"
                    />
                    <datalist id={`province-options-${index}`}>
                      {#each location.provinceOptions as province}
                        <option value={province}></option>
                      {/each}
                    </datalist>
                  </div>
                  <div>
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for={`district-${index}`}>
                      // DISTRITO
                    </label>
                    <input
                      id={`district-${index}`}
                      list={`district-options-${index}`}
                      bind:value={location.district}
                      placeholder="Ej: San Luis"
                      class="input-industrial"
                    />
                    <datalist id={`district-options-${index}`}>
                      {#each location.districtOptions as district}
                        <option value={district}></option>
                      {/each}
                    </datalist>
                  </div>
                  <div class="md:col-span-2">
                    <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for={`address-${index}`}>
                      // DIRECCIÓN
                    </label>
                    <input
                      id={`address-${index}`}
                      bind:value={location.address}
                      placeholder="Av., calle, lote o referencia principal"
                      class="input-industrial"
                    />
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Horarios de atención -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// HORARIOS DE ATENCIÓN</p>
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mt-0.5">Horario semanal base · WorkshopSchedule</p>
          </div>
          <div class="px-6 py-4 divide-y divide-steel-600/15">
            {#each schedules as schedule, index}
              <div class="grid grid-cols-1 md:grid-cols-[140px,auto,1fr,1fr] gap-4 items-center py-4">

                <!-- Día -->
                <div>
                  <p class="font-mono text-xs text-bone uppercase tracking-widest">{schedule.day_label}</p>
                  <p class="font-mono text-[9px] uppercase tracking-widest mt-0.5 {schedule.is_active ? 'text-green-500' : 'text-steel-600'}">
                    {schedule.is_active ? 'ATENCIÓN ACTIVA' : 'SIN ATENCIÓN'}
                  </p>
                </div>

                <!-- Toggle abierto -->
                <label class="flex items-center gap-2 cursor-pointer group">
                  <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                              {schedule.is_active ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                    <input
                      type="checkbox"
                      checked={schedule.is_active}
                      on:change={(e) => updateSchedule(index, { is_active: (e.currentTarget as HTMLInputElement).checked })}
                      class="sr-only"
                    />
                    {#if schedule.is_active}
                      <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    {/if}
                  </div>
                  <span class="font-mono text-[10px] uppercase tracking-widest text-steel-500 group-hover:text-bone transition-colors">ABIERTO</span>
                </label>

                <!-- Apertura -->
                <div>
                  <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1.5" for={`start-${index}`}>APERTURA</label>
                  <input
                    id={`start-${index}`}
                    type="time"
                    value={schedule.start_time}
                    disabled={!schedule.is_active}
                    on:change={(e) => updateSchedule(index, { start_time: (e.currentTarget as HTMLInputElement).value })}
                    class="input-industrial disabled:opacity-40 disabled:cursor-not-allowed"
                  />
                </div>

                <!-- Cierre -->
                <div>
                  <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1.5" for={`end-${index}`}>CIERRE</label>
                  <input
                    id={`end-${index}`}
                    type="time"
                    value={schedule.end_time}
                    disabled={!schedule.is_active}
                    on:change={(e) => updateSchedule(index, { end_time: (e.currentTarget as HTMLInputElement).value })}
                    class="input-industrial disabled:opacity-40 disabled:cursor-not-allowed"
                  />
                </div>

              </div>
            {/each}
          </div>
        </div>

        <!-- Opciones de servicio -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// OPCIONES DE SERVICIO</p>
          </div>
          <div class="p-6 space-y-3">
            <label class="flex items-center gap-3 cursor-pointer group">
              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                          {form.pickupDelivery ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                <input type="checkbox" bind:checked={form.pickupDelivery} class="sr-only" />
                {#if form.pickupDelivery}
                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </div>
              <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
                RECOJO Y ENTREGA COORDINADA
              </span>
            </label>
            <label class="flex items-center gap-3 cursor-pointer group">
              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                          {form.courtesyInspection ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                <input type="checkbox" bind:checked={form.courtesyInspection} class="sr-only" />
                {#if form.courtesyInspection}
                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </div>
              <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
                INSPECCIÓN DE CORTESÍA EN DIAGNÓSTICO
              </span>
            </label>
            <label class="flex items-center gap-3 cursor-pointer group">
              <div class="relative w-4 h-4 border flex items-center justify-center transition-colors
                          {form.emergencyService ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                <input type="checkbox" bind:checked={form.emergencyService} class="sr-only" />
                {#if form.emergencyService}
                  <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                {/if}
              </div>
              <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
                ATENCIÓN PRIORITARIA / EMERGENCIAS
              </span>
            </label>
          </div>
        </div>

        <!-- Mensajes de estado -->
        {#if message}
          <div class="border border-green-700/50 bg-green-600/10 px-5 py-4 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
            <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{message}</p>
          </div>
        {/if}
        {#if error && !accessDenied}
          <div class="border border-rust-700/50 bg-rust-600/10 px-5 py-4 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
            <p class="font-mono text-xs text-rust-400">{error}</p>
          </div>
        {/if}

        <!-- Botón guardar -->
        <button
          type="button"
          on:click={saveTemplate}
          disabled={saving}
          class="btn-rust w-full text-center disabled:opacity-50 disabled:cursor-not-allowed"
          style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)"
        >
          {saving ? 'GUARDANDO...' : 'GUARDAR PLANTILLA DEL TALLER →'}
        </button>

      </div>

      <!-- ════════════════════════════════
           COLUMNA DERECHA — Sidebar
      ════════════════════════════════ -->
      <aside class="space-y-6">

        <!-- Vista previa -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// VISTA PREVIA</p>
          </div>
          <div class="p-6 space-y-5">
            <div>
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">NOMBRE COMERCIAL</p>
              <p class="font-display text-3xl text-bone uppercase leading-none">{form.workshopName || 'TU TALLER'}</p>
            </div>
            {#if form.headline}
              <p class="font-mono text-xs text-steel-400 leading-relaxed">{form.headline}</p>
            {/if}
            <div class="grid grid-cols-2 gap-3 border-t border-steel-600/20 pt-5">
              <div class="border border-steel-600/25 p-4">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">SEDES</p>
                <p class="font-display text-3xl text-bone leading-none">{locations.length}</p>
              </div>
              <div class="border border-steel-600/25 p-4">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">DÍAS ACTIVOS</p>
                <p class="font-display text-3xl text-bone leading-none">{activeDays}</p>
              </div>
            </div>
            {#if mainLocation}
              <div class="border-l-2 border-rust-600 pl-4 py-1">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">SEDE PRINCIPAL</p>
                <p class="font-mono text-xs text-bone uppercase tracking-widest">{mainLocation.name || 'Sede principal'}</p>
                {#if mainLocation.address}
                  <p class="font-mono text-[10px] text-steel-500 mt-1">{mainLocation.address}</p>
                {/if}
                {#if mainLocation.district || mainLocation.province || mainLocation.department}
                  <p class="font-mono text-[10px] text-steel-600 mt-0.5 uppercase">
                    {[mainLocation.district, mainLocation.province, mainLocation.department].filter(Boolean).join(' · ')}
                  </p>
                {/if}
              </div>
            {/if}
          </div>
        </div>

        <!-- Módulos conectados -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// MÓDULOS CONECTADOS</p>
          </div>
          <div class="p-6 space-y-3">
            {#each [
              'Sincronización de Workshop con customer empresarial',
              'Registro de múltiples sedes con WorkshopLocation',
              'Horario semanal base con WorkshopSchedule',
            ] as item}
              <div class="flex items-start gap-3">
                <span class="font-mono text-xs text-green-500 mt-0.5 flex-shrink-0">✓</span>
                <p class="font-mono text-[10px] text-steel-400 uppercase tracking-widest leading-relaxed">{item}</p>
              </div>
            {/each}
            {#if additionalLocations > 0}
              <div class="border border-steel-600/25 p-4 mt-2">
                <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                  {additionalLocations} SEDE{additionalLocations !== 1 ? 'S' : ''} ADICIONAL{additionalLocations !== 1 ? 'ES' : ''} REGISTRADA{additionalLocations !== 1 ? 'S' : ''}
                </p>
              </div>
            {/if}
          </div>
          <div class="border-t border-steel-600/25 px-6 py-4">
            <a href="/taller/servicios"
               class="font-mono text-[10px] text-rust-500 hover:text-rust-400 uppercase tracking-widest transition-colors">
              CONTINUAR CON CATÁLOGO DE SERVICIOS →
            </a>
          </div>
        </div>

      </aside>
    </div>
  {/if}
</div>