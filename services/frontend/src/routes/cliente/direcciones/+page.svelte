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
    shipping: '🚚 Envío',
    agency: '🏢 Agencia',
    business: '🏬 Negocio',
  };
</script>

<svelte:head>
  <title>Mis Direcciones - ECOMPARTS</title>
</svelte:head>

<div class="max-w-3xl mx-auto py-12 px-4">
  <div class="flex justify-between items-center mb-8">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Mis Direcciones</h1>
      <a href="/cliente/perfil" class="text-sm text-blue-600 hover:underline">← Volver al perfil</a>
    </div>
    <button on:click={() => abrirFormulario()}
      class="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-lg transition">
      + Nueva Dirección
    </button>
  </div>

  {#if mensaje}
    <div class="bg-green-50 text-green-700 rounded-lg p-3 mb-4 text-sm">{mensaje}</div>
  {/if}
  {#if error}
    <div class="bg-red-50 text-red-700 rounded-lg p-3 mb-4 text-sm">{error}</div>
  {/if}

  {#if loading}
    <div class="text-gray-500 text-center py-12">Cargando direcciones...</div>
  {:else if addresses.length === 0 && !mostrarFormulario}
    <div class="bg-white rounded-xl shadow p-8 text-center text-gray-500">
      No tienes direcciones registradas.
    </div>
  {:else}
    <div class="space-y-4 mb-6">
      {#each addresses as addr}
        <div class="bg-white rounded-xl shadow p-5 flex justify-between items-start">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="text-sm font-semibold text-gray-700">{tipoLabel[addr.address_type] || addr.address_type}</span>
              {#if addr.is_default}
                <span class="bg-blue-100 text-blue-700 text-xs px-2 py-0.5 rounded-full font-medium">Predeterminada</span>
              {/if}
            </div>
            <p class="text-gray-900 font-medium">{addr.contact_name} · {addr.contact_phone}</p>
            <p class="text-gray-600 text-sm">{addr.full_address}</p>
            {#if addr.reference}
              <p class="text-gray-400 text-xs mt-1">Ref: {addr.reference}</p>
            {/if}
          </div>
          <div class="flex gap-2 ml-4 shrink-0">
            <button on:click={() => abrirFormulario(addr)}
              class="text-blue-600 hover:text-blue-800 text-sm font-medium">Editar</button>
            <button on:click={() => eliminar(addr.id)}
              class="text-red-500 hover:text-red-700 text-sm font-medium">Eliminar</button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Formulario -->
  {#if mostrarFormulario}
    <div class="bg-white rounded-xl shadow p-6 mt-4">
      <h2 class="text-lg font-semibold text-gray-800 mb-5">
        {editandoId ? 'Editar Dirección' : 'Nueva Dirección'}
      </h2>
      <form on:submit|preventDefault={guardar} class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="address_type">Tipo</label>
            <select id="address_type" bind:value={form.address_type}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="shipping">Envío</option>
              <option value="agency">Agencia</option>
              <option value="business">Negocio</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="contact_name">Nombre de Contacto</label>
            <input id="contact_name" type="text" bind:value={form.contact_name} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="contact_phone">Teléfono</label>
            <input id="contact_phone" type="tel" bind:value={form.contact_phone} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          {#if form.address_type === 'agency'}
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="agency_name">Nombre de Agencia</label>
              <input id="agency_name" type="text" bind:value={form.agency_name}
                class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          {/if}
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="street">Calle / Avenida</label>
            <input id="street" type="text" bind:value={form.street} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="street_number">Número</label>
            <input id="street_number" type="text" bind:value={form.street_number}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="apartment">Dpto / Oficina</label>
            <input id="apartment" type="text" bind:value={form.apartment}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="district">Distrito</label>
            <input id="district" type="text" bind:value={form.district} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="city">Ciudad / Provincia</label>
            <input id="city" type="text" bind:value={form.city} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="state">Departamento</label>
            <input id="state" type="text" bind:value={form.state} required
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="postal_code">Código Postal</label>
            <input id="postal_code" type="text" bind:value={form.postal_code}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="md:col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="reference">Referencia</label>
            <input id="reference" type="text" bind:value={form.reference}
              placeholder="Ej: Frente al parque, portón negro..."
              class="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" bind:checked={form.is_default} class="w-4 h-4 text-blue-600 rounded" />
          <span class="text-sm text-gray-700">Establecer como dirección predeterminada</span>
        </label>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={guardando}
            class="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold px-6 py-2 rounded-lg transition">
            {guardando ? 'Guardando...' : 'Guardar'}
          </button>
          <button type="button" on:click={cancelar}
            class="border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium px-6 py-2 rounded-lg transition">
            Cancelar
          </button>
        </div>
      </form>
    </div>
  {/if}
</div>
