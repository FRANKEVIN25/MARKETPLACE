<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { onMount } from 'svelte';
  import type { Customer } from '$lib/api/types';
  import {
    BUSINESS_ACTIVITY_OPTIONS,
    isWorkshopBusinessActivity,
    normalizeBusinessActivity,
    type BusinessActivity,
  } from '$lib/constants/customer';

  let customer: Customer | null = null;
  let loading = true;
  let guardando = false;
  let mensaje = '';
  let error = '';

  // Formulario editable
  let form: {
    phone: string;
    document_type: 'DNI' | 'RUC' | 'CE' | 'PASSPORT';
    document_number: string;
    company_name: string;
    business_activity: BusinessActivity | '';
    receive_newsletter: boolean;
    receive_promotions: boolean;
  } = {
    phone: '',
    document_type: 'DNI',
    document_number: '',
    company_name: '',
    business_activity: '',
    receive_newsletter: true,
    receive_promotions: true,
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
      form = {
        phone: customer.phone || '',
        document_type: (customer.document_type as 'DNI' | 'RUC' | 'CE' | 'PASSPORT') || 'DNI',
        document_number: customer.document_number || '',
        company_name: customer.company_name || '',
        business_activity: normalizeBusinessActivity(customer.business_activity),
        receive_newsletter: customer.receive_newsletter,
        receive_promotions: customer.receive_promotions,
      };
    } catch (e) {
      error = 'No se pudo cargar el perfil.';
    } finally {
      loading = false;
    }
  });

  async function guardarPerfil() {
    guardando = true;
    mensaje = '';
    error = '';
    const token = auth.getAccessToken();
    if (!token) return;
    try {
      customer = await api.customer.updateProfile(token, form);
      auth.customer.set(customer);
      mensaje = 'Perfil actualizado correctamente.';
    } catch (e) {
      error = 'Error al actualizar el perfil.';
    } finally {
      guardando = false;
    }
  }

  $: isWorkshopCompany = !!(
    customer?.customer_type === 'company' &&
    (customer?.is_workshop || isWorkshopBusinessActivity(customer?.business_activity))
  );
</script>

<svelte:head>
  <title>Mi Perfil - ECOMPARTS</title>
</svelte:head>

<div class="max-w-3xl mx-auto py-12 px-4">
  <h1 class="text-3xl font-bold text-gray-900 mb-8">Mi Perfil</h1>

  {#if loading}
    <div class="text-gray-500 text-center py-12">Cargando perfil...</div>
  {:else if error && !customer}
    <div class="bg-red-50 text-red-700 rounded-lg p-4">{error}</div>
  {:else if customer}
    <div class="bg-white rounded-xl shadow p-8 space-y-6">

      <!-- Info de solo lectura -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pb-6 border-b border-gray-100">
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide">ID Cliente</p>
          <p class="font-mono font-semibold text-gray-800">{customer.customer_id}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide">Usuario</p>
          <p class="font-semibold text-gray-800">{customer.username}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide">Email</p>
          <p class="font-semibold text-gray-800">{customer.email}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 uppercase tracking-wide">Tipo de Cliente</p>
          <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium">
            {customer.customer_type === 'company' ? 'Empresa' : 'Individual'}
          </span>
        </div>
      </div>

      <!-- Formulario editable -->
      <form on:submit|preventDefault={guardarPerfil} class="space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="phone">Teléfono</label>
            <input id="phone" type="tel" bind:value={form.phone}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="document_type">Tipo de Documento</label>
            <select id="document_type" bind:value={form.document_type}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="DNI">DNI</option>
              <option value="RUC">RUC</option>
              <option value="CE">Carnet de Extranjería</option>
              <option value="PASSPORT">Pasaporte</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="document_number">Número de Documento</label>
            <input id="document_number" type="text" bind:value={form.document_number}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          {#if customer.customer_type === 'company'}
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="company_name">Razón Social</label>
              <input id="company_name" type="text" bind:value={form.company_name}
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div class="md:col-span-2">
              <label class="block text-sm font-medium text-gray-700 mb-1" for="business_activity">Actividad Económica</label>
              <select id="business_activity" bind:value={form.business_activity}
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">Selecciona el tipo de empresa</option>
                {#each BUSINESS_ACTIVITY_OPTIONS as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
              <p class="text-xs text-gray-500 mt-1">La configuración de taller se habilita solo cuando la actividad económica es Taller mecánico.</p>
            </div>
          {/if}
        </div>

        <!-- Preferencias -->
        <div class="pt-4 border-t border-gray-100 space-y-3">
          <p class="text-sm font-medium text-gray-700">Preferencias de comunicación</p>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.receive_newsletter}
              class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm text-gray-700">Recibir Newsletter</span>
          </label>
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.receive_promotions}
              class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm text-gray-700">Recibir Promociones</span>
          </label>
        </div>

        {#if mensaje}
          <div class="bg-green-50 text-green-700 rounded-lg p-3 text-sm">{mensaje}</div>
        {/if}
        {#if error}
          <div class="bg-red-50 text-red-700 rounded-lg p-3 text-sm">{error}</div>
        {/if}

        <div class="flex gap-4 pt-2">
          <button type="submit" disabled={guardando}
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-6 py-2 rounded-lg transition">
            {guardando ? 'Guardando...' : 'Guardar Cambios'}
          </button>
          {#if isWorkshopCompany}
            <a href="/taller/perfil"
              class="border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium px-6 py-2 rounded-lg transition">
              Configurar taller
            </a>
            <a href="/taller/servicios"
              class="border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium px-6 py-2 rounded-lg transition">
              Configurar servicios
            </a>
          {/if}
          <a href="/cliente/direcciones"
            class="border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium px-6 py-2 rounded-lg transition">
            Mis Direcciones
          </a>
          <a href="/cliente/historial-compras"
            class="border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium px-6 py-2 rounded-lg transition">
            Mis compras
          </a>
        </div>
      </form>

      {#if customer.customer_type === 'company' && !isWorkshopCompany}
        <section class="pt-6 border-t border-gray-100 space-y-3">
          <h2 class="text-xl font-bold text-gray-900">Módulos especializados</h2>
          <p class="text-sm text-gray-600">
            Tu empresa todavía no tiene habilitado el módulo de taller. Si operas como taller mecánico, cambia la actividad económica y guarda el perfil para activar esas configuraciones.
          </p>
          <a href="/servicios" class="inline-flex items-center text-sm font-semibold text-blue-600 hover:text-blue-700">
            Ver propuesta de servicios →
          </a>
        </section>
      {/if}

      {#if isWorkshopCompany}
        <section class="pt-6 border-t border-gray-100 space-y-4">
          <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h2 class="text-xl font-bold text-gray-900">Panel de taller</h2>
              <p class="text-sm text-gray-600">
                Usa tus datos de empresa como base y completa la configuración operativa de tu taller.
              </p>
            </div>
            <a href="/servicios"
              class="text-sm font-semibold text-blue-600 hover:text-blue-700">
              Ver propuesta de servicios →
            </a>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <a href="/taller/perfil" class="rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition">
              <p class="text-sm font-semibold text-gray-900 mb-1">Perfil comercial</p>
              <p class="text-sm text-gray-600">Marca del taller, especialidades, cobertura y propuesta de valor.</p>
            </a>
            <a href="/taller/servicios" class="rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition">
              <p class="text-sm font-semibold text-gray-900 mb-1">Catálogo de servicios</p>
              <p class="text-sm text-gray-600">Precios base, tiempos estimados, garantía y servicios destacados.</p>
            </a>
            <a href="/cliente/historial-compras" class="rounded-xl border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition">
              <p class="text-sm font-semibold text-gray-900 mb-1">Historial conservado</p>
              <p class="text-sm text-gray-600">Tus compras y beneficios del marketplace siguen ligados al mismo usuario.</p>
            </a>
          </div>
        </section>
      {/if}
    </div>
  {/if}
</div>
