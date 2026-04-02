<script lang="ts">
  import { onMount } from 'svelte';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';

  type WorkshopServiceItem = {
    id: number;
    name: string;
    category: string;
    duration: string;
    priceFrom: string;
    specialized: boolean;
    warranty: boolean;
    active: boolean;
  };

  let message = '';
  let loading = true;
  let accessDenied = false;
  let error = '';

  let services: WorkshopServiceItem[] = [
    {
      id: 1,
      name: 'Cambio de aceite y filtros',
      category: 'Mantenimiento preventivo',
      duration: '45 min',
      priceFrom: 'S/ 120',
      specialized: true,
      warranty: true,
      active: true,
    },
    {
      id: 2,
      name: 'Diagnóstico por scanner',
      category: 'Diagnóstico electrónico',
      duration: '30 min',
      priceFrom: 'S/ 90',
      specialized: true,
      warranty: false,
      active: true,
    },
    {
      id: 3,
      name: 'Servicio de frenos delanteros',
      category: 'Frenos y suspensión',
      duration: '90 min',
      priceFrom: 'S/ 180',
      specialized: false,
      warranty: true,
      active: true,
    },
    {
      id: 4,
      name: 'Recarga de aire acondicionado',
      category: 'Aire acondicionado',
      duration: '60 min',
      priceFrom: 'S/ 150',
      specialized: false,
      warranty: true,
      active: false,
    },
  ];

  function saveCatalog(): void {
    message = 'Catálogo de servicios guardado como plantilla visual. Ya está listo para conectarse a `WorkshopService`.';
  }

  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }

    try {
      const customer = await api.customer.getProfile(token);
      auth.customer.set(customer);

      if (customer.customer_type !== 'company' || !isWorkshopBusinessActivity(customer.business_activity)) {
        accessDenied = true;
        error = 'Este catálogo solo está disponible para empresas configuradas como taller mecánico.';
      }
    } catch (e) {
      error = 'No se pudo validar el acceso al catálogo de servicios.';
    } finally {
      loading = false;
    }
  });

  $: activeServices = services.filter((service) => service.active).length;
  $: specializedServices = services.filter((service) => service.specialized).length;
</script>

<svelte:head>
  <title>Servicios del Taller | ECOMPARTS</title>
  <meta name="description" content="Define el catálogo operativo del taller: precios, tiempos, garantía y servicios destacados." />
</svelte:head>

<div class="max-w-6xl mx-auto px-4 py-12 space-y-8">
  {#if loading}
    <div class="rounded-2xl bg-white p-8 shadow text-gray-500">Validando acceso al catálogo...</div>
  {:else if accessDenied}
    <div class="rounded-2xl bg-amber-50 border border-amber-200 p-8 text-amber-900 space-y-4">
      <div>
        <h1 class="text-2xl font-bold">Acceso no habilitado</h1>
        <p class="mt-2 text-sm">{error}</p>
      </div>
      <a href="/cliente/perfil" class="inline-flex items-center rounded-lg bg-white border border-amber-300 px-5 py-2 font-semibold hover:bg-amber-100 transition">
        Volver a mi perfil
      </a>
    </div>
  {:else}
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-indigo-600">Plantilla de catálogo</p>
        <h1 class="text-3xl md:text-4xl font-bold text-gray-900">Configuración de servicios</h1>
        <p class="text-gray-600 mt-2 max-w-3xl">
          Esta vista baja la propuesta del taller a una tabla operativa: servicios activos, precio desde, tiempo promedio, garantía y diferenciadores.
        </p>
      </div>
      <div class="flex flex-wrap gap-3">
        <a href="/taller/perfil" class="px-5 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition">Volver al perfil</a>
        <button onclick={saveCatalog} class="px-5 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition">Guardar catálogo</button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[1.15fr,0.85fr] gap-6">
      <section class="bg-white rounded-2xl shadow overflow-hidden">
      <div class="p-6 border-b border-gray-100 flex items-center justify-between gap-4">
        <div>
          <h2 class="text-xl font-bold text-gray-900">Servicios publicados</h2>
          <p class="text-sm text-gray-600">Base inicial pensada para `WorkshopService` y `WorkshopServiceHistory`.</p>
        </div>
        <span class="text-sm font-semibold text-gray-500">{activeServices} activos</span>
      </div>

      <div class="divide-y divide-gray-100">
        {#each services as service}
          <div class="p-6 grid grid-cols-1 md:grid-cols-[1.25fr,0.9fr,0.8fr] gap-4 items-start">
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-2">
                <h3 class="text-lg font-semibold text-gray-900">{service.name}</h3>
                <span class={`px-2.5 py-1 rounded-full text-xs font-semibold ${service.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                  {service.active ? 'Activo' : 'Borrador'}
                </span>
              </div>
              <p class="text-sm text-gray-600">{service.category}</p>
            </div>

            <div class="grid grid-cols-2 gap-3 text-sm">
              <label>
                <span class="block text-gray-500 mb-1">Duración</span>
                <input bind:value={service.duration} class="w-full border border-gray-300 rounded-lg px-3 py-2" />
              </label>
              <label>
                <span class="block text-gray-500 mb-1">Precio desde</span>
                <input bind:value={service.priceFrom} class="w-full border border-gray-300 rounded-lg px-3 py-2" />
              </label>
            </div>

            <div class="space-y-3 text-sm text-gray-700">
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" bind:checked={service.specialized} class="w-4 h-4 text-indigo-600 rounded" />
                <span>Servicio destacado</span>
              </label>
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" bind:checked={service.warranty} class="w-4 h-4 text-indigo-600 rounded" />
                <span>Incluye garantía</span>
              </label>
              <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" bind:checked={service.active} class="w-4 h-4 text-indigo-600 rounded" />
                <span>Visible al cliente</span>
              </label>
            </div>
          </div>
        {/each}
      </div>
      </section>

      <aside class="space-y-6">
        <section class="rounded-2xl bg-indigo-600 text-white p-6 shadow">
        <p class="text-sm font-semibold uppercase tracking-wide text-indigo-100 mb-2">Resumen del catálogo</p>
        <div class="grid grid-cols-2 gap-4">
          <div class="rounded-xl bg-white/10 p-4">
            <p class="text-indigo-100 text-sm">Servicios activos</p>
            <p class="text-3xl font-bold">{activeServices}</p>
          </div>
          <div class="rounded-xl bg-white/10 p-4">
            <p class="text-indigo-100 text-sm">Especializados</p>
            <p class="text-3xl font-bold">{specializedServices}</p>
          </div>
        </div>
        </section>

        <section class="bg-white rounded-2xl p-6 shadow space-y-4">
        <div>
          <h2 class="text-lg font-bold text-gray-900">Qué conecta después</h2>
          <p class="text-sm text-gray-600">El siguiente paso natural es exponer datos reales del backend:</p>
        </div>
        <ul class="space-y-3 text-sm text-gray-700">
          <li class="flex gap-3"><span class="text-green-600">✓</span><span>`ServiceCategory` plana como origen del selector.</span></li>
          <li class="flex gap-3"><span class="text-green-600">✓</span><span>`WorkshopService` para activar precios y tiempos.</span></li>
          <li class="flex gap-3"><span class="text-green-600">✓</span><span>`WorkshopServiceHistory` para mostrar reputación y experiencia.</span></li>
        </ul>
        </section>

        {#if message}
          <div class="bg-green-50 text-green-700 rounded-2xl p-4 text-sm shadow-sm">{message}</div>
        {/if}
      </aside>
    </div>
  {/if}
</div>