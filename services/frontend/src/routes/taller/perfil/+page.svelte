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
  <title>Perfil de Taller — ECOMPARTS</title>
  <meta name="description" content="Configura la presencia comercial de tu taller a partir del perfil empresa del customer." />
</svelte:head>

<div class="container-responsive py-10 max-w-6xl">

  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// TALLER / PERFIL COMERCIAL</p>
      <h1 class="font-display text-5xl text-bone uppercase leading-none mb-2">PERFIL DE TALLER</h1>
      <p class="font-mono text-xs text-steel-500 max-w-2xl leading-relaxed">
        Extiende tu perfil de empresa y configura los bloques que se conectarán con Workshop, horarios y expertise vehicular.
      </p>
    </div>
    <div class="flex flex-wrap gap-3 mt-1">
      <a href="/servicios" class="btn-ghost">VER SERVICIOS</a>
      <a href="/taller/servicios" class="btn-rust">CONFIGURAR CATÁLOGO →</a>
    </div>
  </div>

  {#if loading}
    <div class="bg-iron-900 border border-steel-600/25 p-12 text-center">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO PERFIL...</p>
    </div>

  {:else if accessDenied}
    <div class="border border-steel-600/30 bg-iron-900 p-8"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-3">// ACCESO NO HABILITADO</p>
      <h2 class="font-display text-3xl text-bone uppercase mb-3">MÓDULO RESTRINGIDO</h2>
      <p class="font-mono text-xs text-steel-400 mb-6 leading-relaxed">
        Este espacio se activa solo para empresas cuya actividad económica sea <span class="text-bone">Taller mecánico</span>.
      </p>
      <a href="/cliente/perfil" class="btn-outline">← VOLVER A MI PERFIL</a>
    </div>

  {:else}
    <div class="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-6">

      <!-- Formulario principal -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">

        <!-- Datos de cuenta (readonly) -->
        <div class="border-b border-steel-600/25 px-6 py-4">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS DE EMPRESA</p>
        </div>
        <div class="grid grid-cols-2 divide-x divide-steel-600/20 border-b border-steel-600/25">
          <div class="px-6 py-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ID CUSTOMER</p>
            <p class="font-mono text-sm text-bone">{customer?.customer_id || 'Pendiente'}</p>
          </div>
          <div class="px-6 py-4">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">DOCUMENTO</p>
            <p class="font-mono text-sm text-bone">{customer?.document_type || 'RUC'} · {customer?.document_number || 'Sin completar'}</p>
          </div>
        </div>

        <!-- Datos editables -->
        <div class="border-b border-steel-600/25 px-6 py-4">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS DEL TALLER</p>
        </div>
        <div class="p-6 space-y-5">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
              <input id="phone" bind:value={form.phone} class="input-industrial" />
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
              <textarea id="description" bind:value={form.description} rows="4" class="input-industrial resize-none"></textarea>
            </div>
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="district">
                // DISTRITO
              </label>
              <input id="district" bind:value={form.district} class="input-industrial" />
            </div>
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="address">
                // DIRECCIÓN BASE
              </label>
              <input id="address" bind:value={form.address} class="input-industrial" placeholder="Av., calle o referencia" />
            </div>
          </div>

          <!-- Niveles -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5 pt-4 border-t border-steel-600/20">
            <div>
              <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// NIVEL DE SERVICIO</p>
              <div class="grid grid-cols-3 gap-2">
                {#each ['BASIC', 'MANAGED', 'ADVANCED'] as level}
                  <button
                    type="button"
                    onclick={() => form.serviceLevel = level as ServiceLevel}
                    class="font-mono text-[10px] uppercase tracking-widest border py-2 px-2 transition-all duration-150
                      {form.serviceLevel === level
                        ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                        : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                  >
                    {level}
                  </button>
                {/each}
              </div>
            </div>
            <div>
              <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// RELACIÓN CON AUTOPARTES</p>
              <div class="grid grid-cols-1 gap-2">
                {#each ['BUYER', 'B2B_BUYER', 'SELLER'] as level}
                  <button
                    type="button"
                    onclick={() => form.commerceLevel = level as CommerceLevel}
                    class="font-mono text-[10px] uppercase tracking-widest border py-2 px-3 text-left transition-all duration-150
                      {form.commerceLevel === level
                        ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                        : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                  >
                    {level}
                  </button>
                {/each}
              </div>
            </div>
          </div>

          <!-- Especialidades -->
          <div class="pt-4 border-t border-steel-600/20">
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// ESPECIALIDADES</p>
            <div class="flex flex-wrap gap-2">
              {#each specialtyOptions as specialty}
                <button
                  type="button"
                  onclick={() => form.specialties = toggleSelection(form.specialties, specialty)}
                  class="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 transition-all duration-150
                    {form.specialties.includes(specialty)
                      ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                      : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                >
                  {specialty}
                </button>
              {/each}
            </div>
          </div>

          <!-- Vehículos foco -->
          <div class="pt-4 border-t border-steel-600/20">
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// VEHÍCULOS FOCO</p>
            <div class="flex flex-wrap gap-2">
              {#each vehicleFocusOptions as brand}
                <button
                  type="button"
                  onclick={() => form.vehicleFocus = toggleSelection(form.vehicleFocus, brand)}
                  class="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 transition-all duration-150
                    {form.vehicleFocus.includes(brand)
                      ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                      : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                >
                  {brand}
                </button>
              {/each}
            </div>
          </div>

          <!-- Opciones de servicio -->
          <div class="pt-4 border-t border-steel-600/20 space-y-3">
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">// SERVICIOS ADICIONALES</p>
            {#each [
              { key: 'pickupDelivery', label: 'RECOJO Y ENTREGA COORDINADA' },
              { key: 'courtesyInspection', label: 'INSPECCIÓN DE CORTESÍA EN DIAGNÓSTICO' },
              { key: 'emergencyService', label: 'ATENCIÓN PRIORITARIA / EMERGENCIAS' },
            ] as opt}
              <label class="flex items-center gap-3 cursor-pointer group">
                <div class="relative w-4 h-4 border border-steel-600/50 flex items-center justify-center
                            {(form as any)[opt.key] ? 'border-rust-600 bg-rust-600/20' : 'hover:border-steel-400'}">
                  <input type="checkbox" bind:checked={(form as any)[opt.key]} class="sr-only" />
                  {#if (form as any)[opt.key]}
                    <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                  {/if}
                </div>
                <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">{opt.label}</span>
              </label>
            {/each}
          </div>

          <!-- Mensajes -->
          {#if message}
            <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
              <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{message}</p>
            </div>
          {/if}
          {#if error}
            <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
              <p class="font-mono text-xs text-rust-400">{error}</p>
            </div>
          {/if}

          <button
            type="button"
            onclick={saveTemplate}
            disabled={saving}
            class="btn-rust disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'GUARDANDO...' : 'GUARDAR PLANTILLA DEL TALLER'}
          </button>
        </div>
      </div>

      <!-- Sidebar: preview + próximos pasos -->
      <aside class="space-y-5">

        <!-- Preview del taller -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-5 py-3">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PREVIEW PÚBLICO</p>
          </div>
          <div class="p-5 space-y-4">
            <div>
              <h2 class="font-display text-2xl text-bone uppercase leading-none mb-1">
                {form.workshopName || 'TU TALLER'}
              </h2>
              <p class="font-mono text-xs text-steel-400 leading-relaxed">{form.headline}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              {#each form.specialties as specialty}
                <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">
                  {specialty}
                </span>
              {/each}
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-iron-800 border border-steel-600/20 p-3">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">SERVICE LVL</p>
                <p class="font-display text-lg text-bone">{form.serviceLevel}</p>
              </div>
              <div class="bg-iron-800 border border-steel-600/20 p-3">
                <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">COMMERCE</p>
                <p class="font-display text-lg text-bone">{form.commerceLevel}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Próximos pasos -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-5 py-3">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PRÓXIMOS PASOS</p>
          </div>
          <div class="p-5 space-y-3">
            {#each [
              'Configuración de Workshop y customer empresarial.',
              'Especialidades por ServiceCategory plana.',
              'Preparación para horarios y expertise vehicular.',
            ] as item}
              <div class="flex items-start gap-2.5">
                <span class="text-green-400 font-mono text-xs flex-shrink-0 mt-0.5">✓</span>
                <p class="font-mono text-[10px] text-steel-400 leading-relaxed">{item}</p>
              </div>
            {/each}
            <div class="border-t border-steel-600/20 pt-3">
              <a href="/taller/servicios"
                 class="font-mono text-[10px] uppercase tracking-widest text-rust-500 hover:text-rust-400 transition-colors">
                CONTINUAR CON CATÁLOGO DE SERVICIOS →
              </a>
            </div>
          </div>
        </div>

      </aside>
    </div>
  {/if}
</div>
