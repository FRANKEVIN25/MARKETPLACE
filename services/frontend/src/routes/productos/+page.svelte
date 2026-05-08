<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { api } from '$lib/api/client';
  import { auth } from '$lib/store/auth';
  import type { Customer, CustomerSelectedVehicle } from '$lib/api/types';

  export let data: PageData;

  // Estado de filtros hidratado desde el load
  const fi: any = data.filtrosIniciales;
  let filtros = {
    marca_id: fi.marca_id ?? '',
    modelo_id: fi.modelo_id ?? '',
    variante_id: fi.variante_id ?? '',
    q: fi.q ?? '',
    ordering: fi.ordering ?? '-created_at',
    page: fi.page ?? 1,
    category_id: fi.category_id ?? '',
    provider_id: fi.provider_id ?? '',
    es_universal: fi.es_universal ?? null,
  };

  let modelos: { id: number; nombre: string }[] = [];
  let variantes: { id: number; display_name: string }[] = [];

  let cargandoModelos = false;
  let cargandoVariantes = false;
  let sincronizandoVehiculo = false;
  let persistenciaVehiculoInicializada = false;
  let ultimaClavePersistidaVehiculo = '';

  const isAuthenticated = auth.isAuthenticated;

  // Categorías cargadas desde el load (tipadas de forma flexible)
  const categorias: any[] = (data as any).categories ?? [];

  async function cargarModelos(marcaId: string | number | null) {
    modelos = [];
    variantes = [];
    if (!marcaId) return;

    cargandoModelos = true;
    try {
      const lista = await api.publicVehicles.modelos(Number(marcaId));
      modelos = lista.map((m) => ({ id: m.id, nombre: m.nombre }));
    } catch (e) {
      console.error('Error cargando modelos', e);
    } finally {
      cargandoModelos = false;
    }
  }

  async function cargarVariantes(modeloId: string | number | null) {
    variantes = [];
    if (!modeloId) return;

    cargandoVariantes = true;
    try {
      const lista = await api.publicVehicles.variantes(Number(modeloId));
      variantes = lista.map((v) => ({ id: v.id, display_name: v.display_name }));
    } catch (e) {
      console.error('Error cargando variantes', e);
    } finally {
      cargandoVariantes = false;
    }
  }

  function obtenerPayloadVehiculo() {
    return {
      selected_vehicle_variante_id: filtros.variante_id ? Number(filtros.variante_id) : null,
    };
  }

  function obtenerClaveVehiculo(payload = obtenerPayloadVehiculo()) {
    return JSON.stringify(payload);
  }

  async function cargarCustomerActual(): Promise<Customer | null> {
    const token = auth.getAccessToken();
    if (!token) return null;

    const customerActual = get(auth.customer);
    if (customerActual) return customerActual;

    try {
      const customer = await api.customer.getProfile(token);
      auth.customer.set(customer);
      return customer;
    } catch (error) {
      console.error('Error cargando customer actual', error);
      return null;
    }
  }

  async function persistirSeleccionVehiculo(force = false) {
    if (!persistenciaVehiculoInicializada) return;

    const token = auth.getAccessToken();
    if (!token) return;

    const payload = obtenerPayloadVehiculo();
    const clave = obtenerClaveVehiculo(payload);
    if (!force && clave === ultimaClavePersistidaVehiculo) return;

    sincronizandoVehiculo = true;
    try {
      const customerActualizado = await api.customer.updateProfile(token, payload);
      auth.customer.set(customerActualizado);
      ultimaClavePersistidaVehiculo = clave;
    } catch (error) {
      console.error('Error persistiendo selección de vehículo', error);
    } finally {
      sincronizandoVehiculo = false;
    }
  }

  async function aplicarVehiculoGuardado(selectedVehicle: CustomerSelectedVehicle) {
    filtros.marca_id = selectedVehicle.marca_id ? String(selectedVehicle.marca_id) : '';
    filtros.modelo_id = selectedVehicle.modelo_id ? String(selectedVehicle.modelo_id) : '';
    filtros.variante_id = selectedVehicle.variante_id ? String(selectedVehicle.variante_id) : '';
    filtros.page = 1;

    if (filtros.marca_id) {
      await cargarModelos(filtros.marca_id);
    }
    if (filtros.modelo_id) {
      await cargarVariantes(filtros.modelo_id);
    }
  }

  async function hidratarVehiculoDesdePerfil() {
    if (filtros.marca_id || filtros.modelo_id || filtros.variante_id) {
      persistenciaVehiculoInicializada = true;
      ultimaClavePersistidaVehiculo = obtenerClaveVehiculo();
      return;
    }

    const customer = await cargarCustomerActual();
    if (!customer?.selected_vehicle) {
      persistenciaVehiculoInicializada = true;
      ultimaClavePersistidaVehiculo = obtenerClaveVehiculo();
      return;
    }

    await aplicarVehiculoGuardado(customer.selected_vehicle);
    persistenciaVehiculoInicializada = true;
    ultimaClavePersistidaVehiculo = obtenerClaveVehiculo();
    actualizarURL();
  }

  // Helper para actualizar la URL con los filtros actuales
  function actualizarURL() {
    const params = new URLSearchParams();

    if (filtros.marca_id) params.set('marca_id', String(filtros.marca_id));
    if (filtros.modelo_id) params.set('modelo_id', String(filtros.modelo_id));
    if (filtros.variante_id) params.set('variante_id', String(filtros.variante_id));
    if (filtros.q) params.set('q', filtros.q);
    if (filtros.category_id) params.set('category_id', String(filtros.category_id));
    if (filtros.es_universal !== null && filtros.es_universal !== undefined) {
      params.set('es_universal', filtros.es_universal ? 'true' : 'false');
    }
    if (filtros.ordering && filtros.ordering !== '-created_at') {
      params.set('ordering', filtros.ordering);
    }
    if (filtros.page && filtros.page > 1) {
      params.set('page', String(filtros.page));
    }

    const query = params.toString();
    goto(query ? `/productos?${query}` : '/productos');
  }

  onMount(async () => {
    if (filtros.marca_id) {
      await cargarModelos(filtros.marca_id);
    }
    if (filtros.modelo_id) {
      await cargarVariantes(filtros.modelo_id);
    }

    await hidratarVehiculoDesdePerfil();
  });

  $: marcaSeleccionada = data.marcas.find(
    (m) => String(m.id) === String(filtros.marca_id || '')
  );
  $: modeloSeleccionado = modelos.find(
    (m) => String(m.id) === String(filtros.modelo_id || '')
  );
  $: varianteSeleccionada = variantes.find(
    (v) => String(v.id) === String(filtros.variante_id || '')
  );
</script>

<svelte:head>
  <title>Catálogo — ECOMPARTS · Autopartes Perú</title>
  <meta name="description" content="Catálogo completo de autopartes de calidad en Perú" />
</svelte:head>

<div class="bg-iron-950 min-h-screen">
  <!-- Header industrial -->
  <div class="bg-iron-900 border-b border-steel-600/30 sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div class="flex items-end gap-6">
        <div>
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// CATÁLOGO</p>
          <h1 class="font-display text-5xl text-bone uppercase leading-none">CATÁLOGO DE PRODUCTOS</h1>
        </div>
        {#if data.count !== undefined}
          <span class="font-mono text-xs text-steel-500 uppercase tracking-widest mb-1 hidden sm:block">
            {data.count} REFERENCIAS DISPONIBLES
          </span>
        {/if}
      </div>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Filtros industriales -->
    <div class="bg-iron-900 border border-steel-600/25 p-6 mb-8 space-y-6"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Búsqueda -->
        <div>
          <label for="busqueda" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
            // BUSCAR PRODUCTO
          </label>
          <input
            id="busqueda"
            type="text"
            placeholder="Ej: Disco de Freno, Bujías, SKU..."
            bind:value={filtros.q}
            on:change={() => {
              filtros.page = 1;
              actualizarURL();
            }}
            class="input-industrial"
          />
        </div>

        <!-- Categoría -->
        <div>
          <label for="filtro-categoria" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
            // CATEGORÍA
          </label>
          <select
            id="filtro-categoria"
            bind:value={filtros.category_id}
            class="input-industrial"
            on:change={() => {
              filtros.page = 1;
              actualizarURL();
            }}
          >
            <option value="">Todas las categorías</option>
            {#each categorias as category}
              <option value={category.id}>{category.name}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Filtros de vehículo: Marca / Modelo / Variante -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <!-- Marca -->
        <div>
          <label for="filtro-marca" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
            // MARCA
          </label>
          <select
            id="filtro-marca"
            bind:value={filtros.marca_id}
            class="input-industrial"
            on:change={async () => {
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              await cargarModelos(filtros.marca_id || null);
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            <option value="">Todas las marcas</option>
            {#each data.marcas as marca}
              <option value={marca.id}>{marca.nombre}</option>
            {/each}
          </select>
        </div>

        <!-- Modelo -->
        <div>
          <label for="filtro-modelo" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
            // MODELO
          </label>
          <select
            id="filtro-modelo"
            bind:value={filtros.modelo_id}
            class="input-industrial disabled:opacity-40"
            disabled={!filtros.marca_id}
            on:change={async () => {
              filtros.variante_id = '';
              filtros.page = 1;
              await cargarVariantes(filtros.modelo_id || null);
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            <option value="">Todos los modelos</option>
            {#each modelos as modelo}
              <option value={modelo.id}>{modelo.nombre}</option>
            {/each}
          </select>
        </div>

        <!-- Variante -->
        <div>
          <label for="filtro-variante" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
            // VARIANTE (MOTOR / AÑO)
          </label>
          <select
            id="filtro-variante"
            bind:value={filtros.variante_id}
            class="input-industrial disabled:opacity-40"
            disabled={!filtros.modelo_id}
            on:change={async () => {
              filtros.page = 1;
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            <option value="">Todas las variantes</option>
            {#each variantes as variante}
              <option value={variante.id}>{variante.display_name}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest border border-steel-600/30 px-3 py-1.5">
          El vehículo activo filtra el catálogo y se conserva en tu cuenta.
        </span>
        {#if $isAuthenticated}
          <span class="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 {sincronizandoVehiculo ? 'border-amber-600/40 text-amber-500' : 'border-green-600/40 text-green-500'}">
            {sincronizandoVehiculo ? '⟳ GUARDANDO VEHÍCULO...' : '✓ VEHÍCULO SINCRONIZADO'}
          </span>
        {/if}
      </div>

      <!-- Filtros adicionales: Universales -->
      <div class="mt-4">
        <div class="flex items-center space-x-4">
          <button
            type="button"
            class={`inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-2 border transition-colors ${
              filtros.es_universal === null || filtros.es_universal === undefined
                ? 'bg-iron-800 text-steel-400 border-steel-600/50'
                : filtros.es_universal
                ? 'bg-iron-800 text-green-500 border-green-600/50'
                : 'bg-iron-800 text-rust-500 border-rust-600/50'
            }`}
            on:click={() => {
              // Ciclo de estados: null (ambos) -> true (solo universales) -> false (sin universales) -> null
              if (filtros.es_universal === null || filtros.es_universal === undefined) {
                filtros.es_universal = true;
              } else if (filtros.es_universal === true) {
                filtros.es_universal = false;
              } else {
                filtros.es_universal = null;
              }
              filtros.page = 1;
              actualizarURL();
            }}
          >
            {#if filtros.es_universal === null || filtros.es_universal === undefined}
              Universales: incluidos
            {:else if filtros.es_universal}
              Solo productos universales
            {:else}
              Sin productos universales
            {/if}
          </button>
        </div>
      </div>
    </div>

    <!-- Filtros aplicados (chips) -->
    {#if marcaSeleccionada || modeloSeleccionado || varianteSeleccionada || filtros.category_id || (filtros.es_universal !== null && filtros.es_universal !== undefined)}
      <div class="flex flex-wrap items-center gap-2 mb-6">
        {#if marcaSeleccionada}
          <button
            type="button"
            class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-steel-300 border border-steel-600/40 hover:border-rust-600/60 hover:text-rust-500 transition-colors"
            on:click={async () => {
              filtros.marca_id = '';
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              modelos = [];
              variantes = [];
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            Marca: {marcaSeleccionada.nombre}
            <span class="ml-2 text-xs">✕</span>
          </button>
        {/if}

        {#if modeloSeleccionado}
          <button
            type="button"
            class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-steel-300 border border-steel-600/40 hover:border-rust-600/60 hover:text-rust-500 transition-colors"
            on:click={async () => {
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              variantes = [];
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            Modelo: {modeloSeleccionado.nombre}
            <span class="ml-2 text-xs">✕</span>
          </button>
        {/if}

        {#if varianteSeleccionada}
          <button
            type="button"
            class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-steel-300 border border-steel-600/40 hover:border-rust-600/60 hover:text-rust-500 transition-colors"
            on:click={async () => {
              filtros.variante_id = '';
              filtros.page = 1;
              await persistirSeleccionVehiculo();
              actualizarURL();
            }}
          >
            Variante: {varianteSeleccionada.display_name}
            <span class="ml-2 text-xs">✕</span>
          </button>
        {/if}
        {#if filtros.category_id}
          {#if categorias}
            {#each categorias as category}
              {#if String(category.id) === String(filtros.category_id)}
                <button
                  type="button"
                  class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-steel-300 border border-steel-600/40 hover:border-rust-600/60 hover:text-rust-500 transition-colors"
                  on:click={() => {
                    filtros.category_id = '';
                    filtros.page = 1;
                    actualizarURL();
                  }}
                >
                  Categoría: {category.name}
                  <span class="ml-2 text-xs">✕</span>
                </button>
              {/if}
            {/each}
          {/if}
        {/if}

        {#if filtros.es_universal !== null && filtros.es_universal !== undefined}
          <button
            type="button"
            class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-steel-300 border border-steel-600/40 hover:border-rust-600/60 hover:text-rust-500 transition-colors"
            on:click={() => {
              filtros.es_universal = null;
              filtros.page = 1;
              actualizarURL();
            }}
          >
            {#if filtros.es_universal}
              Solo universales
            {:else}
              Sin universales
            {/if}
            <span class="ml-2 text-xs">✕</span>
          </button>
        {/if}

        <button
          type="button"
          class="inline-flex items-center font-mono text-[10px] uppercase tracking-widest px-3 py-1 bg-iron-800 text-rust-500 border border-rust-600/40 hover:bg-rust-600/10 transition-colors ml-auto"
          on:click={async () => {
            filtros.marca_id = '';
            filtros.modelo_id = '';
            filtros.variante_id = '';
            filtros.category_id = '';
            filtros.provider_id = '';
            filtros.es_universal = null;
            filtros.page = 1;
            modelos = [];
            variantes = [];
            await persistirSeleccionVehiculo();
            actualizarURL();
          }}
        >
          Limpiar todos los filtros
        </button>
      </div>
    {/if}

    <!-- Resultados -->
    {#if data.error}
      <div class="border border-rust-700/50 bg-iron-900 p-8"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <p class="font-mono text-xs text-rust-500 uppercase tracking-widest mb-1">// ERROR AL CARGAR PRODUCTOS</p>
        <p class="font-mono text-sm text-steel-400">{data.error}</p>
      </div>
    {:else if data.products.length === 0}
      <div class="border border-steel-600/25 bg-iron-900 p-16 text-center"
           style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
        <svg class="mx-auto h-14 w-14 text-steel-700 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <p class="font-display text-3xl text-steel-600 uppercase mb-2">SIN RESULTADOS</p>
        <p class="font-mono text-xs text-steel-700 uppercase tracking-widest">INTENTA CON OTROS TÉRMINOS DE BÚSQUEDA</p>
      </div>
    {:else}
      <div>
        <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest mb-6">
          MOSTRANDO {data.products.length} DE {data.totalCount} PRODUCTOS
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {#each data.products as product (product.id)}
            <ProductCard {product} />
          {/each}
        </div>

        <!-- ── Paginación ── -->
        {#if data.totalCount > data.products.length || filtros.page > 1}
          {@const pageSize = 20}
          {@const totalPages = Math.ceil(data.totalCount / pageSize)}
          <div class="flex items-center justify-between mt-10 pt-6 border-t border-steel-600/25">

            <!-- Info de página -->
            <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">
              PÁGINA {filtros.page} DE {totalPages}
            </p>

            <!-- Controles -->
            <div class="flex items-center gap-0">
              <button
                type="button"
                disabled={filtros.page <= 1}
                on:click={() => {
                  filtros.page = filtros.page - 1;
                  actualizarURL();
                }}
                class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest px-5 py-3
                       border border-steel-600/40 text-steel-400 transition-colors
                       hover:border-rust-600 hover:text-rust-500
                       disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:border-steel-600/40 disabled:hover:text-steel-400"
              >
                ← ANTERIOR
              </button>

              <!-- Número de página actual -->
              <div class="px-5 py-3 border-y border-steel-600/40 font-mono text-[10px] text-bone uppercase tracking-widest">
                {filtros.page}
              </div>

              <button
                type="button"
                disabled={filtros.page >= totalPages}
                on:click={() => {
                  filtros.page = filtros.page + 1;
                  actualizarURL();
                }}
                class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest px-5 py-3
                       border border-steel-600/40 text-steel-400 transition-colors
                       hover:border-rust-600 hover:text-rust-500
                       disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:border-steel-600/40 disabled:hover:text-steel-400"
              >
                SIGUIENTE →
              </button>
            </div>

          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>