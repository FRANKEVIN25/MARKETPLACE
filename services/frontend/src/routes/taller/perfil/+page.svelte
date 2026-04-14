<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import type { Customer } from '$lib/api/types';
  import {
    getBusinessActivityLabel,
    isWorkshopBusinessActivity,
  } from '$lib/constants/customer';

  type ServiceLevel = 'BASIC' | 'MANAGED' | 'ADVANCED';
  type CommerceLevel = 'BUYER' | 'B2B_BUYER' | 'SELLER';

  let customer: Customer | null = null;
  let loading = true;
  let saving = false;
  let accessDenied = false;
  let message = '';
  let error = '';

  const specialtyOptions = [
    'Mantenimiento preventivo',
    'Frenos y suspensión',
    'Diagnóstico electrónico',
    'Aire acondicionado',
    'Motor y transmisión',
    'Planchado y pintura',
  ];

  const vehicleFocusOptions = ['Toyota', 'Hyundai', 'Kia', 'Chevrolet', 'Nissan', 'Multimarca'];

  let form = {
    workshopName: '',
    headline: '',
    description: '',
    phone: '',
    district: 'Lima',
    address: '',
    serviceLevel: 'BASIC' as ServiceLevel,
    commerceLevel: 'BUYER' as CommerceLevel,
    specialties: ['Mantenimiento preventivo', 'Diagnóstico electrónico'],
    vehicleFocus: ['Toyota', 'Multimarca'],
    pickupDelivery: true,
    emergencyService: false,
    courtesyInspection: true,
  };

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

      form = {
        ...form,
        workshopName: customer.company_name || customer.full_name || '',
        phone: customer.phone || '',
        headline: customer.company_name
          ? `${customer.company_name} especializado en atención confiable y rápida.`
          : 'Taller especializado en servicios automotrices de confianza.',
        description: `Base del negocio: ${getBusinessActivityLabel(customer.business_activity)}. Configura aquí la propuesta comercial inicial de tu taller.`,
      };
    } catch (e) {
      error = 'No se pudo cargar la base del perfil empresa.';
    } finally {
      loading = false;
    }
  });

  function toggleSelection(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  }

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

      if (customer) {
        customer = await api.customer.updateProfile(token, {
          phone: form.phone,
          company_name: form.workshopName,
          document_type: customer.document_type,
          document_number: customer.document_number,
        });
        auth.customer.set(customer);
      }

      message = 'Plantilla de taller guardada. Los bloques operativos ya quedaron listos para conectarse a la API de services.';
    } catch (e) {
      error = 'No se pudo guardar la plantilla base del taller.';
    } finally {
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Perfil de Taller | ECOMPARTS</title>
  <meta name="description" content="Configura la presencia comercial de tu taller a partir del perfil empresa del customer." />
</svelte:head>

<div class="max-w-6xl mx-auto px-4 py-12 space-y-8">
  <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
    <div>
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-600">Plantilla inicial</p>
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900">Perfil de taller</h1>
      <p class="text-gray-600 mt-2 max-w-3xl">
        Esta vista extiende el perfil del cliente empresa y agrega los bloques que luego se conectarán con `Workshop`, `WorkshopSchedule` y `WorkshopVehicleExpertise`.
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
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="headline">Titular comercial</label>
            <input id="headline" bind:value={form.headline} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="description">Descripción</label>
            <textarea id="description" bind:value={form.description} rows="4" class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="district">Distrito principal</label>
            <input id="district" bind:value={form.district} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="address">Dirección base</label>
            <input id="address" bind:value={form.address} class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="Av., calle o referencia" />
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
          <div>
            <p class="text-sm font-medium text-gray-700 mb-2">Nivel de servicio</p>
            <div class="grid grid-cols-3 gap-2">
              {#each ['BASIC', 'MANAGED', 'ADVANCED'] as level}
                <button
                  type="button"
                  onclick={() => form.serviceLevel = level as ServiceLevel}
                  class={`rounded-lg border px-3 py-2 text-sm font-medium transition ${form.serviceLevel === level ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}
                >
                  {level}
                </button>
              {/each}
            </div>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-700 mb-2">Relación con autopartes</p>
            <div class="grid grid-cols-1 gap-2">
              {#each ['BUYER', 'B2B_BUYER', 'SELLER'] as level}
                <button
                  type="button"
                  onclick={() => form.commerceLevel = level as CommerceLevel}
                  class={`rounded-lg border px-3 py-2 text-sm font-medium text-left transition ${form.commerceLevel === level ? 'border-indigo-600 bg-indigo-50 text-indigo-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}
                >
                  {level}
                </button>
              {/each}
            </div>
          </div>
        </div>

        <div class="space-y-4 pt-2 border-t border-gray-100">
          <div>
            <p class="text-sm font-medium text-gray-700 mb-3">Especialidades</p>
            <div class="flex flex-wrap gap-2">
              {#each specialtyOptions as specialty}
                <button
                  type="button"
                  onclick={() => form.specialties = toggleSelection(form.specialties, specialty)}
                  class={`px-4 py-2 rounded-full text-sm border transition ${form.specialties.includes(specialty) ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}`}
                >
                  {specialty}
                </button>
              {/each}
            </div>
          </div>

          <div>
            <p class="text-sm font-medium text-gray-700 mb-3">Vehículos foco</p>
            <div class="flex flex-wrap gap-2">
              {#each vehicleFocusOptions as brand}
                <button
                  type="button"
                  onclick={() => form.vehicleFocus = toggleSelection(form.vehicleFocus, brand)}
                  class={`px-4 py-2 rounded-full text-sm border transition ${form.vehicleFocus.includes(brand) ? 'bg-indigo-600 border-indigo-600 text-white' : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}`}
                >
                  {brand}
                </button>
              {/each}
            </div>
          </div>
        </div>

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
          <div class="flex flex-wrap gap-2 mb-4">
            {#each form.specialties as specialty}
              <span class="px-3 py-1 rounded-full bg-white/10 text-sm">{specialty}</span>
            {/each}
          </div>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-xl bg-white/10 p-3">
              <p class="text-slate-300">Service level</p>
              <p class="font-semibold">{form.serviceLevel}</p>
            </div>
            <div class="rounded-xl bg-white/10 p-3">
              <p class="text-slate-300">Commerce level</p>
              <p class="font-semibold">{form.commerceLevel}</p>
            </div>
          </div>
        </section>

        <section class="bg-white rounded-2xl p-6 shadow space-y-4">
          <div>
            <p class="text-sm font-semibold text-gray-900">Bloques siguientes</p>
            <p class="text-sm text-gray-600">Esta plantilla deja listos los siguientes módulos para conectar:</p>
          </div>
          <ul class="space-y-3 text-sm text-gray-700">
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Configuración de `Workshop` y customer empresarial.</span></li>
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Especialidades por `ServiceCategory` plana.</span></li>
            <li class="flex gap-3"><span class="text-green-600">✓</span><span>Preparación para horarios y expertise vehicular.</span></li>
          </ul>
          <a href="/taller/servicios" class="inline-flex items-center font-semibold text-blue-600 hover:text-blue-700">
            Continuar con catálogo de servicios →
          </a>
        </section>
      </aside>
    </div>
  {/if}
</div>