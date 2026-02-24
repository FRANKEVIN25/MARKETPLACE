<script lang="ts">
  export let product: {
    id: number;
    nombre?: string;
    name?: string;
    slug?: string;
    proveedor?: string;
    supplier?: string;
    provider_name?: string;
    categoria?: string;
    category?: string;
    category_name?: string;
    precio?: number;
    price?: number | string;
    imagen?: string;
    image?: string;
  };

  let esFavorito = false;

  // Mapear propiedades según la estructura de la API
  $: nombre = product.nombre || product.name || 'Sin nombre';
  $: proveedor = product.proveedor || product.supplier || product.provider_name || 'Sin proveedor';
  $: categoria = product.categoria || product.category || product.category_name || 'Sin categoría';
  $: precio = product.precio || product.price || 0;
  $: imagen = product.imagen || product.image;

  const toggleFavorito = () => {
    esFavorito = !esFavorito;
  };
</script>

<div class="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300 overflow-hidden">
  <!-- Imagen placeholder con gradiente -->
  <div class="relative bg-gradient-to-br from-blue-400 to-blue-600 h-48 flex items-center justify-center overflow-hidden group">
    {#if imagen}
      <img 
        src={imagen} 
        alt={nombre}
        class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
      />
    {:else}
      <div class="text-white text-center">
        <svg class="w-16 h-16 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2m6 0a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5z" />
        </svg>
        <p class="text-sm opacity-75">Sin imagen</p>
      </div>
    {/if}
    
    <!-- Badge de categoría -->
    <div class="absolute top-2 right-2 bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
      {categoria}
    </div>

    <!-- Botón favorito -->
    <button
      on:click={toggleFavorito}
      class="absolute top-2 left-2 bg-white rounded-full p-2 hover:bg-gray-100 transition-colors"
      aria-label="Agregar a favoritos"
    >
      <svg
        class="w-5 h-5 {esFavorito ? 'fill-red-500 text-red-500' : 'text-gray-400'}"
        fill={esFavorito ? 'currentColor' : 'none'}
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
      </svg>
    </button>
  </div>

  <!-- Contenido -->
  <div class="p-4">
    <!-- Nombre del producto -->
    <h3 class="text-lg font-semibold text-gray-900 mb-1 truncate" title={nombre}>
      {nombre}
    </h3>

    <!-- Proveedor -->
    <p class="text-sm text-gray-500 mb-3">
      {proveedor}
    </p>

    <!-- Precio -->
    <div class="mb-4">
      <p class="text-2xl font-bold text-blue-600">
        S/. {precio ? parseFloat(precio.toString()).toFixed(2) : '0.00'}
      </p>
    </div>

    <!-- Botón de acción -->
    <a
      href={`/productos/${product.id}`}
      class="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors duration-200 text-center block"
    >
      Ver Detalles
    </a>
  </div>
</div>