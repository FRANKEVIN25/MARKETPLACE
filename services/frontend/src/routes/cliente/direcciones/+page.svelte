<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { onMount } from 'svelte';
  import type { Address } from '$lib/api/types';

  let addresses: Address[] = [];
  let loading = true;
  let error = '';
  let mostrarFormulario = false;
  let editandoId: number | null = null;
  let guardando = false;
  let mensaje = '';

  const formVacio: {
    address_type: 'shipping' | 'agency' | 'business';
    contact_name: string;
    contact_phone: string;
    street: string;
    street_number: string;
    apartment: string;
    district: string;
    city: string;
    state: string;
    postal_code: string;
    country: string;
    agency_name: string;
    is_default: boolean;
    reference: string;
  } = {
    address_type: 'shipping',
    contact_name: '',
    contact_phone: '',
    street: '',
    street_number: '',
    apartment: '',
    district: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'Perú',
    agency_name: '',
    is_default: false,
    reference: '',
  };

  let form = { ...formVacio };

  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) { window.location.href = '/login'; return; }
    try {
      addresses = await api.customer.getAddresses(token);
    } catch (e) {
      error = 'No se pudieron cargar las direcciones.';
    } finally {
      loading = false;
    }
  });

  function abrirFormulario(addr?: Address) {
    if (addr) {
      editandoId = addr.id;
      form = {
        address_type: addr.address_type as 'shipping' | 'agency' | 'business',
        contact_name: addr.contact_name,
        contact_phone: addr.contact_phone,
        street: addr.street,
        street_number: addr.street_number || '',
        apartment: addr.apartment || '',
        district: addr.district,
        city: addr.city,
        state: addr.state,
        postal_code: addr.postal_code || '',
        country: addr.country,
        agency_name: addr.agency_name || '',
        is_default: addr.is_default,
        reference: addr.reference || '',
      };
    } else {
      editandoId = null;
      form = { ...formVacio };
    }
    mostrarFormulario = true;
    mensaje = '';
    error = '';
  }

  function cancelar() {
    mostrarFormulario = false;
    editandoId = null;
    form = { ...formVacio };
  }

  async function guardar() {
    guardando = true;
    mensaje = '';
    error = '';
    const token = auth.getAccessToken();
    if (!token) return;
    try {
      if (editandoId) {
        const updated = await api.customer.updateAddress(token, editandoId, form);
        addresses = addresses.map(a => a.id === editandoId ? updated : a);
      } else {
        const nueva = await api.customer.createAddress(token, form);
        addresses = [...addresses, nueva];
      }
      mensaje = editandoId ? 'Dirección actualizada.' : 'Dirección agregada.';
      mostrarFormulario = false;
      editandoId = null;
    } catch (e) {
      error = 'Error al guardar la dirección.';
    } finally {
      guardando = false;
    }
  }

  async function eliminar(id: number) {
    if (!confirm('¿Eliminar esta dirección?')) return;
    const token = auth.getAccessToken();
    if (!token) return;
    try {
      await api.customer.deleteAddress(token, id);
      addresses = addresses.filter(a => a.id !== id);
    } catch (e) {
      error = 'Error al eliminar la dirección.';
    }
  }

  const tipoLabel: Record<string, string> = {
    shipping: 'ENVÍO',
    agency: 'AGENCIA',
    business: 'NEGOCIO',
  };
</script>

<svelte:head>
  <title>Mis Direcciones — ECOMPARTS</title>
</svelte:head>

<div class="container-responsive py-10 max-w-3xl">

  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8 flex items-start justify-between gap-4">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// MI CUENTA / DIRECCIONES</p>
      <h1 class="font-display text-5xl text-bone uppercase leading-none">MIS DIRECCIONES</h1>
    </div>
    <div class="flex items-center gap-3 mt-1">
      <a href="/cliente/perfil" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">← PERFIL</a>
      <button on:click={() => abrirFormulario()} class="btn-rust">+ NUEVA</button>
    </div>
  </div>

  <!-- Mensajes -->
  {#if mensaje}
    <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-center gap-3 mb-4">
      <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
      <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{mensaje}</p>
    </div>
  {/if}
  {#if error}
    <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3 mb-4">
      <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
      <p class="font-mono text-xs text-rust-400">{error}</p>
    </div>
  {/if}

  {#if loading}
    <div class="text-center py-16">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO DIRECCIONES...</p>
    </div>
  {:else if addresses.length === 0 && !mostrarFormulario}
    <div class="bg-iron-900 border border-steel-600/25 p-12 text-center"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <p class="font-display text-3xl text-steel-600 uppercase mb-2">SIN DIRECCIONES</p>
      <p class="font-mono text-xs text-steel-700 uppercase tracking-widest mb-6">NO TIENES DIRECCIONES REGISTRADAS</p>
      <button on:click={() => abrirFormulario()} class="btn-rust">AGREGAR DIRECCIÓN →</button>
    </div>
  {:else}
    <div class="space-y-3 mb-6">
      {#each addresses as addr}
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/20 px-5 py-3 flex items-center justify-between gap-3">
            <div class="flex items-center gap-3 flex-wrap">
              <span class="font-mono text-[9px] uppercase tracking-widest border border-steel-600/40 text-steel-400 px-2 py-0.5">
                {tipoLabel[addr.address_type] || addr.address_type}
              </span>
              {#if addr.is_default}
                <span class="font-mono text-[9px] uppercase tracking-widest border border-rust-700/50 text-rust-500 px-2 py-0.5">
                  PREDETERMINADA
                </span>
              {/if}
            </div>
            <div class="flex gap-3">
              <button on:click={() => abrirFormulario(addr)}
                class="font-mono text-[10px] uppercase tracking-widest text-steel-400 hover:text-bone transition-colors">
                EDITAR
              </button>
              <button on:click={() => eliminar(addr.id)}
                class="font-mono text-[10px] uppercase tracking-widest text-rust-600 hover:text-rust-400 transition-colors">
                ELIMINAR
              </button>
            </div>
          </div>
          <div class="px-5 py-4">
            <p class="font-mono text-sm text-bone mb-1">{addr.contact_name} · {addr.contact_phone}</p>
            <p class="font-mono text-xs text-steel-400">{addr.full_address}</p>
            {#if addr.reference}
              <p class="font-mono text-[10px] text-steel-600 mt-1">REF: {addr.reference}</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Formulario -->
  {#if mostrarFormulario}
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">
          // {editandoId ? 'EDITAR DIRECCIÓN' : 'NUEVA DIRECCIÓN'}
        </p>
      </div>
      <form on:submit|preventDefault={guardar} class="p-6 space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="address_type">
              // TIPO
            </label>
            <select id="address_type" bind:value={form.address_type} class="input-industrial">
              <option value="shipping">Envío a domicilio</option>
              <option value="agency">Agencia de transporte</option>
              <option value="business">Local de negocio</option>
            </select>
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="contact_name">
              // NOMBRE DE CONTACTO
            </label>
            <input id="contact_name" type="text" bind:value={form.contact_name} required class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="contact_phone">
              // TELÉFONO
            </label>
            <input id="contact_phone" type="tel" bind:value={form.contact_phone} required class="input-industrial" />
          </div>
          {#if form.address_type === 'agency'}
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="agency_name">
                // NOMBRE DE AGENCIA
              </label>
              <input id="agency_name" type="text" bind:value={form.agency_name} class="input-industrial" />
            </div>
          {/if}
          <div class="md:col-span-2">
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="street">
              // CALLE / AVENIDA
            </label>
            <input id="street" type="text" bind:value={form.street} required class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="street_number">
              // NÚMERO
            </label>
            <input id="street_number" type="text" bind:value={form.street_number} class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="apartment">
              // DPTO / OFICINA
            </label>
            <input id="apartment" type="text" bind:value={form.apartment} class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="district">
              // DISTRITO
            </label>
            <input id="district" type="text" bind:value={form.district} required class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="city">
              // CIUDAD / PROVINCIA
            </label>
            <input id="city" type="text" bind:value={form.city} required class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="state">
              // DEPARTAMENTO
            </label>
            <input id="state" type="text" bind:value={form.state} required class="input-industrial" />
          </div>
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="postal_code">
              // CÓDIGO POSTAL
            </label>
            <input id="postal_code" type="text" bind:value={form.postal_code} class="input-industrial" />
          </div>
          <div class="md:col-span-2">
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="reference">
              // REFERENCIA
            </label>
            <input id="reference" type="text" bind:value={form.reference}
              placeholder="Ej: Frente al parque, portón negro..."
              class="input-industrial" />
          </div>
        </div>

        <!-- Predeterminada -->
        <label class="flex items-center gap-3 cursor-pointer group">
          <div class="relative w-4 h-4 border border-steel-600/50 flex items-center justify-center
                      {form.is_default ? 'border-rust-600 bg-rust-600/20' : 'hover:border-steel-400'}">
            <input type="checkbox" bind:checked={form.is_default} class="sr-only" />
            {#if form.is_default}
              <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            {/if}
          </div>
          <span class="font-mono text-xs text-steel-400 uppercase tracking-widest group-hover:text-bone transition-colors">
            ESTABLECER COMO DIRECCIÓN PREDETERMINADA
          </span>
        </label>

        <div class="flex gap-3 pt-2 border-t border-steel-600/20">
          <button type="submit" disabled={guardando} class="btn-rust disabled:opacity-50 disabled:cursor-not-allowed">
            {guardando ? 'GUARDANDO...' : 'GUARDAR'}
          </button>
          <button type="button" on:click={cancelar} class="btn-outline">CANCELAR</button>
        </div>
      </form>
    </div>
  {/if}
</div>
