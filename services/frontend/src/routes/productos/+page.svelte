<script lang="ts">
  import type { PageData } from './$types';
  import ProductCard from '$lib/components/ProductCard.svelte';
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';

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

  // Proveedores disponibles en la página actual (derivados de los productos cargados)
  $: proveedores = Array.from(
    new Map(data.products.map((p) => [p.provider_group, p.provider_name])).entries()
  ).map(([id, name]) => ({ id, name }));

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

  // Helper para actualizar la URL con los filtros actuales
  function actualizarURL() {
    const params = new URLSearchParams();

    if (filtros.marca_id) params.set('marca_id', String(filtros.marca_id));
    if (filtros.modelo_id) params.set('modelo_id', String(filtros.modelo_id));
    if (filtros.variante_id) params.set('variante_id', String(filtros.variante_id));
    if (filtros.q) params.set('q', filtros.q);
    if (filtros.category_id) params.set('category_id', String(filtros.category_id));
    if (filtros.provider_id) params.set('provider_id', String(filtros.provider_id));
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
  <title>Productos - ECOMPARTS</title>
  <meta name="description" content="Catálogo completo de autopartes" />
</svelte:head>

<div class="bg-gray-50 min-h-screen">
  <!-- Header -->
  <div class="bg-white border-b border-gray-200 sticky top-0 z-10">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 class="text-4xl font-bold text-gray-900 mb-4">Catálogo de Productos</h1>
      <p class="text-gray-600">Explora nuestro completo catálogo de autopartes de calidad</p>
    </div>
  </div>

  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Filtros -->
    <div class="bg-white rounded-lg shadow p-6 mb-8 space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Búsqueda -->
        <div>
          <label for="busqueda" class="block text-sm font-medium text-gray-700 mb-2">
            Buscar productos
          </label>
          <input
            id="busqueda"
            type="text"
            placeholder="Ej: Disco de Freno, Bujías..."
            bind:value={filtros.q}
            on:change={() => {
              filtros.page = 1;
              actualizarURL();
            }}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
          />
        </div>

        <!-- Categoría -->
        <div>
          <label for="filtro-categoria" class="block text-sm font-medium text-gray-700 mb-2">
            Categoría
          </label>
          <select
            id="filtro-categoria"
            bind:value={filtros.category_id}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
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
          <label for="filtro-marca" class="block text-sm font-medium text-gray-700 mb-2">
            Marca
          </label>
          <select
            id="filtro-marca"
            bind:value={filtros.marca_id}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            on:change={async () => {
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              await cargarModelos(filtros.marca_id || null);
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
          <label for="filtro-modelo" class="block text-sm font-medium text-gray-700 mb-2">
            Modelo
          </label>
          <select
            id="filtro-modelo"
            bind:value={filtros.modelo_id}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            disabled={!filtros.marca_id}
            on:change={async () => {
              filtros.variante_id = '';
              filtros.page = 1;
              await cargarVariantes(filtros.modelo_id || null);
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
          <label for="filtro-variante" class="block text-sm font-medium text-gray-700 mb-2">
            Variante (motor / año)
          </label>
          <select
            id="filtro-variante"
            bind:value={filtros.variante_id}
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            disabled={!filtros.modelo_id}
            on:change={() => {
              filtros.page = 1;
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

      <!-- Filtros adicionales: Proveedor y Universales -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <!-- Proveedor -->
        <div>
          <label for="filtro-proveedor" class="block text-sm font-medium text-gray-700 mb-2">
            Proveedor
          </label>
          <select
            id="filtro-proveedor"
            bind:value={filtros.provider_id}
            class="w-full mb-6 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            on:change={() => {
              filtros.page = 1;
              actualizarURL();
            }}
          >
            <option value="">Todos los proveedores</option>
            {#each proveedores as prov}
              <option value={prov.id}>{prov.name}</option>
            {/each}
          </select>
        </div>

        <!-- Productos universales -->
        <div class="flex items-center space-x-4 mt-6 md:mt-0">
          <button
            type="button"
            class={`inline-flex items-center px-3 py-2 rounded-full text-sm border ${
              filtros.es_universal === null || filtros.es_universal === undefined
                ? 'bg-blue-50 text-blue-800 border-blue-200'
                : filtros.es_universal
                ? 'bg-green-50 text-green-800 border-green-200'
                : 'bg-red-50 text-red-800 border-red-200'
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
    {#if marcaSeleccionada || modeloSeleccionado || varianteSeleccionada || filtros.category_id || filtros.provider_id || (filtros.es_universal !== null && filtros.es_universal !== undefined)}
      <div class="flex flex-wrap items-center gap-2 mb-6">
        {#if marcaSeleccionada}
          <button
            type="button"
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 hover:bg-blue-200"
            on:click={() => {
              filtros.marca_id = '';
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              modelos = [];
              variantes = [];
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
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 hover:bg-blue-200"
            on:click={() => {
              filtros.modelo_id = '';
              filtros.variante_id = '';
              filtros.page = 1;
              variantes = [];
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
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 hover:bg-blue-200"
            on:click={() => {
              filtros.variante_id = '';
              filtros.page = 1;
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
                  class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-800 hover:bg-purple-200"
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

        {#if filtros.provider_id}
          {#if proveedores.length}
            {#each proveedores as prov}
              {#if String(prov.id) === String(filtros.provider_id)}
                <button
                  type="button"
                  class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-indigo-100 text-indigo-800 hover:bg-indigo-200"
                  on:click={() => {
                    filtros.provider_id = '';
                    filtros.page = 1;
                    actualizarURL();
                  }}
                >
                  Proveedor: {prov.name}
                  <span class="ml-2 text-xs">✕</span>
                </button>
              {/if}
            {/each}
          {/if}
        {/if}

        {#if filtros.es_universal !== null && filtros.es_universal !== undefined}
          <button
            type="button"
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-teal-100 text-teal-800 hover:bg-teal-200"
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
          class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700 hover:bg-gray-200 ml-auto"
          on:click={() => {
            filtros.marca_id = '';
            filtros.modelo_id = '';
            filtros.variante_id = '';
            filtros.category_id = '';
            filtros.provider_id = '';
            filtros.es_universal = null;
            filtros.page = 1;
            modelos = [];
            variantes = [];
            actualizarURL();
          }}
        >
          Limpiar todos los filtros
        </button>
      </div>
    {/if}

    <!-- Resultados -->
    {#if data.error}
      <div class="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 text-center">
        <p class="font-medium">Error al cargar productos</p>
        <p class="text-sm mt-1">{data.error}</p>
      </div>
    {:else if data.products.length === 0}
      <div class="bg-white rounded-lg shadow p-12 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 21l-4.35-4.35m0 0A7.5 7.5 0 103.305 3.305a7.5 7.5 0 0110.345 10.345z" />
        </svg>
        <p class="text-gray-500 mt-4 text-lg">No se encontraron productos</p>
        <p class="text-gray-400 text-sm mt-1">Intenta con otros términos de búsqueda</p>
      </div>
    {:else}
      <div>
        <p class="text-gray-600 mb-6 font-medium">
          Mostrando {data.products.length} de {data.totalCount} productos
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {#each data.products as product (product.id)}
            <ProductCard {product} />
          {/each}
        </div>
      </div>
    {/if}
  </div>
</div>