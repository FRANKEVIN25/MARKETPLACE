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

<div class="container-responsive py-10 space-y-8">

  {#if loading}
    <div class="bg-iron-900 border border-steel-600/25 p-8 text-center">
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">VALIDANDO ACCESO AL CATÁLOGO...</p>
    </div>

  {:else if accessDenied}
    <div class="bg-iron-900 border border-yellow-700/50 p-8">
      <p class="font-mono text-[10px] text-yellow-600 uppercase tracking-widest mb-2">// ACCESO RESTRINGIDO</p>
      <h1 class="font-display text-4xl text-bone uppercase leading-none mb-3">ACCESO NO HABILITADO</h1>
      <p class="font-mono text-xs text-steel-400 mb-6">{error}</p>
      <a href="/cliente/perfil" class="btn-outline">← VOLVER A MI PERFIL</a>
    </div>

  {:else}
    <!-- Header -->
    <div class="border-b border-steel-600/25 pb-6 flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
      <div>
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// TALLER / CATÁLOGO DE SERVICIOS</p>
        <h1 class="font-display text-5xl text-bone uppercase leading-none">CONFIGURACIÓN DE SERVICIOS</h1>
        <p class="font-mono text-xs text-steel-500 mt-2 max-w-2xl">
          Esta vista baja la propuesta del taller a una tabla operativa: servicios activos, precio desde, tiempo promedio, garantía y diferenciadores.
        </p>
      </div>
      <div class="flex flex-wrap gap-3 shrink-0 mt-1">
        <a href="/taller/perfil" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">← PERFIL</a>
        <button on:click={saveCatalog} class="btn-rust">GUARDAR CATÁLOGO</button>
      </div>
    </div>

    {#if message}
      <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-center gap-3">
        <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
        <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{message}</p>
      </div>
    {/if}

    <div class="grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-6">

      <!-- Catálogo de servicios -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// CATÁLOGO ACTIVO</p>
            <h2 class="font-display text-2xl text-bone uppercase leading-none">SERVICIOS PUBLICADOS</h2>
          </div>
          <span class="font-mono text-[10px] text-steel-500 uppercase tracking-widest border border-steel-600/40 px-2 py-1">
            {activeServices} ACTIVOS
          </span>
        </div>

        <div class="divide-y divide-steel-600/20">
          {#each services as service}
            <div class="p-6 grid grid-cols-1 md:grid-cols-[1.25fr_0.9fr_0.8fr] gap-5 items-start">

              <!-- Info del servicio -->
              <div>
                <div class="flex flex-wrap items-center gap-2 mb-2">
                  <h3 class="font-display text-xl text-bone uppercase leading-none">{service.name}</h3>
                  <span class="font-mono text-[9px] uppercase tracking-widest border px-2 py-0.5
                    {service.active ? 'border-green-700/50 text-green-400' : 'border-steel-600/40 text-steel-600'}">
                    {service.active ? 'ACTIVO' : 'BORRADOR'}
                  </span>
                </div>
                <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">{service.category}</p>
              </div>

              <!-- Campos editables -->
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">
                    // DURACIÓN
                  </label>
                  <input bind:value={service.duration} class="input-industrial text-sm" />
                </div>
                <div>
                  <label class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">
                    // PRECIO DESDE
                  </label>
                  <input bind:value={service.priceFrom} class="input-industrial text-sm" />
                </div>
              </div>

              <!-- Checkboxes -->
              <div class="space-y-3">
                {#each [
                  { key: 'specialized', label: 'SERVICIO DESTACADO' },
                  { key: 'warranty',    label: 'INCLUYE GARANTÍA' },
                  { key: 'active',      label: 'VISIBLE AL CLIENTE' },
                ] as opt}
                  <label class="flex items-center gap-3 cursor-pointer group">
                    <div class="relative w-4 h-4 border flex items-center justify-center flex-shrink-0
                                {service[opt.key as keyof WorkshopServiceItem] ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
                      <input type="checkbox" bind:checked={service[opt.key as keyof WorkshopServiceItem] as boolean} class="sr-only" />
                      {#if service[opt.key as keyof WorkshopServiceItem]}
                        <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                        </svg>
                      {/if}
                    </div>
                    <span class="font-mono text-[10px] text-steel-500 uppercase tracking-widest group-hover:text-bone transition-colors">
                      {opt.label}
                    </span>
                  </label>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-5">

        <!-- Resumen del catálogo -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-5 py-3">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// RESUMEN DEL CATÁLOGO</p>
          </div>
          <div class="grid grid-cols-2 divide-x divide-steel-600/20">
            <div class="px-5 py-4">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">SERVICIOS ACTIVOS</p>
              <p class="font-display text-4xl text-rust-600 leading-none">{activeServices}</p>
            </div>
            <div class="px-5 py-4">
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">ESPECIALIZADOS</p>
              <p class="font-display text-4xl text-rust-600 leading-none">{specializedServices}</p>
            </div>
          </div>
        </div>

        <!-- Qué conecta después -->
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-5 py-3">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PRÓXIMOS PASOS</p>
          </div>
          <div class="p-5 space-y-2">
            {#each [
              '`ServiceCategory` plana como origen del selector.',
              '`WorkshopService` para activar precios y tiempos.',
              '`WorkshopServiceHistory` para mostrar reputación.',
            ] as step}
              <div class="flex items-start gap-3 border border-steel-600/20 bg-iron-800/50 p-3">
                <span class="text-green-400 font-mono text-xs flex-shrink-0">✓</span>
                <p class="font-mono text-[10px] text-steel-400 leading-relaxed">{step}</p>
              </div>
            {/each}
          </div>
        </div>

      </div>
    </div>
  {/if}
</div>
