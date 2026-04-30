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
  <title>Mi Perfil — ECOMPARTS</title>
</svelte:head>

<div class="container-responsive py-10 max-w-3xl">

  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// MI CUENTA</p>
    <h1 class="font-display text-5xl text-bone uppercase leading-none">MI PERFIL</h1>
  </div>

  {#if loading}
    <div class="bg-iron-900 border border-steel-600/25 p-16 text-center">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO PERFIL...</p>
    </div>

  {:else if error && !customer}
    <div class="border border-rust-700/50 bg-rust-600/10 px-5 py-4 flex items-center gap-3">
      <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
      <p class="font-mono text-xs text-rust-400">{error}</p>
    </div>

  {:else if customer}

    <!-- Info de solo lectura -->
    <div class="bg-iron-900 border border-steel-600/25 mb-6"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS DE CUENTA</p>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 divide-x divide-steel-600/20 p-0">
        <div class="px-6 py-5">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ID CLIENTE</p>
          <p class="font-mono text-sm text-bone">{customer.customer_id}</p>
        </div>
        <div class="px-6 py-5">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">USUARIO</p>
          <p class="font-mono text-sm text-bone">{customer.username}</p>
        </div>
        <div class="px-6 py-5">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">EMAIL</p>
          <p class="font-mono text-sm text-bone truncate">{customer.email}</p>
        </div>
        <div class="px-6 py-5">
          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">TIPO</p>
          <span class="font-mono text-[10px] uppercase tracking-widest border px-2 py-0.5
            {customer.customer_type === 'company'
              ? 'border-rust-600/50 text-rust-500'
              : 'border-steel-600/40 text-steel-300'}">
            {customer.customer_type === 'company' ? 'EMPRESA' : 'INDIVIDUAL'}
          </span>
        </div>
      </div>
    </div>

    <!-- Formulario editable -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// DATOS EDITABLES</p>
      </div>

      <form on:submit|preventDefault={guardarPerfil} class="p-6 space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="phone">
              // TELÉFONO
            </label>
            <input id="phone" type="tel" bind:value={form.phone} class="input-industrial" />
          </div>

          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="document_type">
              // TIPO DE DOCUMENTO
            </label>
            <select id="document_type" bind:value={form.document_type} class="input-industrial">
              <option value="DNI">DNI</option>
              <option value="RUC">RUC</option>
              <option value="CE">Carnet de Extranjería</option>
              <option value="PASSPORT">Pasaporte</option>
            </select>
          </div>

          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="document_number">
              // NÚMERO DE DOCUMENTO
            </label>
            <input id="document_number" type="text" bind:value={form.document_number} class="input-industrial" />
          </div>

          {#if customer.customer_type === 'company'}
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="company_name">
                // RAZÓN SOCIAL
              </label>
              <input id="company_name" type="text" bind:value={form.company_name} class="input-industrial" />
            </div>
            <div class="md:col-span-2">
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="business_activity">
                // ACTIVIDAD ECONÓMICA
              </label>
              <select id="business_activity" bind:value={form.business_activity} class="input-industrial">
                <option value="">Selecciona el tipo de empresa</option>
                {#each BUSINESS_ACTIVITY_OPTIONS as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
              <p class="font-mono text-[9px] text-steel-600 mt-1 uppercase tracking-widest">
                EL MÓDULO DE TALLER SE HABILITA SOLO PARA TALLERES MECÁNICOS
              </p>
            </div>
          {/if}
        </div>

        <!-- Preferencias de comunicación -->
        <div class="border-t border-steel-600/20 pt-5 space-y-3">
          <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">// PREFERENCIAS DE COMUNICACIÓN</p>
          <label class="flex items-center gap-3 cursor-pointer group">
            <div class="relative w-4 h-4 border border-steel-600/50 flex items-center justify-center
                        {form.receive_newsletter ? 'border-rust-600 bg-rust-600/20' : 'hover:border-steel-400'}">
              <input type="checkbox" bind:checked={form.receive_newsletter} class="sr-only" />
              {#if form.receive_newsletter}
                <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              {/if}
            </div>
            <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
              RECIBIR NEWSLETTER
            </span>
          </label>
          <label class="flex items-center gap-3 cursor-pointer group">
            <div class="relative w-4 h-4 border border-steel-600/50 flex items-center justify-center
                        {form.receive_promotions ? 'border-rust-600 bg-rust-600/20' : 'hover:border-steel-400'}">
              <input type="checkbox" bind:checked={form.receive_promotions} class="sr-only" />
              {#if form.receive_promotions}
                <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              {/if}
            </div>
            <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
              RECIBIR PROMOCIONES
            </span>
          </label>
        </div>

        <!-- Mensajes -->
        {#if mensaje}
          <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
            <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{mensaje}</p>
          </div>
        {/if}
        {#if error}
          <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
            <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
            <p class="font-mono text-xs text-rust-400">{error}</p>
          </div>
        {/if}

        <!-- Acciones -->
        <div class="flex flex-wrap gap-3 pt-2 border-t border-steel-600/20">
          <button type="submit" disabled={guardando}
            class="btn-rust disabled:opacity-50 disabled:cursor-not-allowed">
            {guardando ? 'GUARDANDO...' : 'GUARDAR CAMBIOS'}
          </button>
          {#if isWorkshopCompany}
            <a href="/taller/perfil" class="btn-outline">CONFIGURAR TALLER</a>
            <a href="/taller/servicios" class="btn-ghost">MIS SERVICIOS</a>
          {/if}
          <a href="/cliente/direcciones" class="btn-ghost">DIRECCIONES</a>
          <a href="/cliente/historial-compras" class="btn-ghost">MIS COMPRAS</a>
        </div>
      </form>
    </div>

    <!-- Módulos especializados (si no es taller) -->
    {#if customer.customer_type === 'company' && !isWorkshopCompany}
      <div class="mt-6 bg-iron-900 border border-steel-600/25 p-6"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-3">// MÓDULOS ESPECIALIZADOS</p>
        <h2 class="font-display text-2xl text-bone uppercase mb-2">MÓDULO DE TALLER</h2>
        <p class="font-mono text-xs text-steel-500 leading-relaxed mb-4">
          Tu empresa aún no tiene habilitado el módulo de taller. Si operas como taller mecánico, cambia la actividad económica y guarda el perfil para activar estas configuraciones.
        </p>
        <a href="/servicios" class="font-mono text-xs text-rust-500 hover:text-rust-400 uppercase tracking-widest transition-colors">
          VER PROPUESTA DE SERVICIOS →
        </a>
      </div>
    {/if}

    <!-- Panel de taller activo -->
    {#if isWorkshopCompany}
      <div class="mt-6 bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PANEL DE TALLER</p>
          <a href="/servicios" class="font-mono text-[10px] text-rust-500 hover:text-rust-400 uppercase tracking-widest transition-colors">
            VER SERVICIOS →
          </a>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 divide-x divide-steel-600/20">
          <a href="/taller/perfil"
             class="px-6 py-5 hover:bg-iron-800 transition-colors group">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MÓDULO 01</p>
            <p class="font-display text-lg text-bone uppercase group-hover:text-rust-400 transition-colors">PERFIL COMERCIAL</p>
            <p class="font-mono text-[10px] text-steel-500 mt-1">Marca, especialidades y cobertura.</p>
          </a>
          <a href="/taller/servicios"
             class="px-6 py-5 hover:bg-iron-800 transition-colors group">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MÓDULO 02</p>
            <p class="font-display text-lg text-bone uppercase group-hover:text-rust-400 transition-colors">CATÁLOGO DE SERVICIOS</p>
            <p class="font-mono text-[10px] text-steel-500 mt-1">Precios, tiempos y garantía.</p>
          </a>
          <a href="/cliente/historial-compras"
             class="px-6 py-5 hover:bg-iron-800 transition-colors group">
            <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MÓDULO 03</p>
            <p class="font-display text-lg text-bone uppercase group-hover:text-rust-400 transition-colors">HISTORIAL</p>
            <p class="font-mono text-[10px] text-steel-500 mt-1">Compras y beneficios del marketplace.</p>
          </a>
        </div>
      </div>
    {/if}

  {/if}
</div>
