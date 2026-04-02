<script lang="ts">
  import { page } from '$app/stores';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';
  import { derived } from 'svelte/store';

  // Contador reactivo del carrito
  const cartCount = derived(cart, $cart => $cart.reduce((acc, item) => acc + item.cantidad, 0));

  // Extraer isAuthenticated como store independiente para usar con $
  const isAuthenticated = auth.isAuthenticated;
  const customer = auth.customer;

  let userMenuOpen = false;

  function toggleUserMenu() {
    userMenuOpen = !userMenuOpen;
  }

  function logout() {
    auth.clearTokens();
    userMenuOpen = false;
    window.location.href = '/';
  }

  const navigation = [
    { name: 'Inicio', href: '/' },
    { name: 'Productos', href: '/productos' },
    { name: 'Servicios', href: '/servicios' },
  ];
  
  let mobileMenuOpen = false;
  let vendorMenuOpen = false;
  
  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
  }
  
  function toggleVendorMenu() {
    vendorMenuOpen = !vendorMenuOpen;
  }

  $: showWorkshopLinks = !!($customer?.is_workshop || isWorkshopBusinessActivity($customer?.business_activity));
</script>

<header class="bg-white shadow-sm sticky top-0 z-50">
  <nav class="container-responsive">
    <div class="flex justify-between items-center h-16">
      <a href="/" class="flex items-center space-x-2">
        <div class="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
          <span class="text-white font-bold text-xl">E</span>
        </div>
        <span class="text-xl font-bold text-gray-900">ECOMPARTS</span>
      </a>
      
      <div class="hidden md:flex items-center space-x-8">
        {#each navigation as item}
          <a
            href={item.href}
            class="text-gray-700 hover:text-primary-600 transition-colors duration-200 {$page.url.pathname === item.href ? 'text-primary-600 font-semibold' : ''}"
          >
            {item.name}
          </a>
        {/each}
        
        <!-- Icono carrito -->
        <a href="/carrito" class="relative flex items-center" aria-label="Carrito de compras">
          <svg class="w-7 h-7 text-gray-700 hover:text-primary-600 transition-colors duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13l-1.4 5h11.8M7 13H5.4M9 21a1 1 0 100-2 1 1 0 000 2zm10 0a1 1 0 100-2 1 1 0 000 2z" />
          </svg>
          {#if $cartCount > 0}
            <span class="absolute -top-2 -right-2 bg-primary-600 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
              {$cartCount > 99 ? '99+' : $cartCount}
            </span>
          {/if}
        </a>

        <!-- Icono usuario -->
        <div class="relative">
          {#if $isAuthenticated}
            <button on:click={toggleUserMenu} class="flex items-center gap-1.5 text-gray-700 hover:text-primary-600 transition-colors duration-200" aria-label="Mi cuenta">
              <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {#if userMenuOpen}
              <div class="absolute right-0 mt-2 w-52 bg-white rounded-lg shadow-lg py-2 border border-gray-200 z-50">
                <a href="/cliente/perfil" class="block px-4 py-2 text-gray-700 hover:bg-gray-50 text-sm"
                  on:click={() => userMenuOpen = false}>
                  👤 Mi Perfil
                </a>
                <a href="/cliente/direcciones" class="block px-4 py-2 text-gray-700 hover:bg-gray-50 text-sm"
                  on:click={() => userMenuOpen = false}>
                  📍 Mis Direcciones
                </a>
                <a href="/cliente/historial-compras" class="block px-4 py-2 text-gray-700 hover:bg-gray-50 text-sm"
                  on:click={() => userMenuOpen = false}>
                  📦 Mis Compras
                </a>
                {#if showWorkshopLinks}
                  <a href="/taller/perfil" class="block px-4 py-2 text-gray-700 hover:bg-gray-50 text-sm"
                    on:click={() => userMenuOpen = false}>
                    🔧 Mi Taller
                  </a>
                  <a href="/taller/servicios" class="block px-4 py-2 text-gray-700 hover:bg-gray-50 text-sm"
                    on:click={() => userMenuOpen = false}>
                    🧰 Mis Servicios
                  </a>
                {/if}
                <div class="border-t border-gray-200 my-1"></div>
                <button on:click={logout} class="w-full text-left block px-4 py-2 text-red-600 hover:bg-red-50 text-sm">
                  🚪 Cerrar Sesión
                </button>
              </div>
            {/if}
          {:else}
            <a href="/login" class="flex items-center gap-1 text-gray-700 hover:text-primary-600 transition-colors duration-200" aria-label="Iniciar sesión">
              <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A8 8 0 1118.88 17.804M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </a>
          {/if}
        </div>

        <div class="relative">
          <button
            on:click={toggleVendorMenu}
            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors duration-200 font-medium flex items-center gap-2"
          >
            Para Vendors
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          
          {#if vendorMenuOpen}
            <div class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg py-2 border border-gray-200">
              <a
                href="/vendedor"
                class="block px-4 py-2 text-gray-700 hover:bg-gray-50"
                on:click={() => vendorMenuOpen = false}
              >
                📊 Ver planes y precios
              </a>
              <a
                href="/vendedor#como-funciona"
                class="block px-4 py-2 text-gray-700 hover:bg-gray-50"
                on:click={() => vendorMenuOpen = false}
              >
                ❓ Cómo funciona
              </a>
              <div class="border-t border-gray-200 my-2"></div>
              <a
                href="/vendedor/registro"
                class="block px-4 py-2 text-primary-600 font-medium hover:bg-primary-50"
                on:click={() => vendorMenuOpen = false}
              >
                🚀 Registrarme ahora
              </a>
            </div>
          {/if}
        </div>
      </div>
      
      <button
        class="md:hidden p-2 rounded-lg hover:bg-gray-100"
        on:click={toggleMobileMenu}
        aria-label="Toggle menu"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {#if mobileMenuOpen}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          {:else}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          {/if}
        </svg>
      </button>
    </div>
    
    {#if mobileMenuOpen}
      <div class="md:hidden py-4 space-y-2">
        {#each navigation as item}
          <a
            href={item.href}
            class="block px-4 py-2 rounded-lg hover:bg-gray-100 {$page.url.pathname === item.href ? 'bg-primary-50 text-primary-600 font-semibold' : 'text-gray-700'}"
            on:click={() => { mobileMenuOpen = false }}
          >
            {item.name}
          </a>
        {/each}
        
        <div class="border-t border-gray-200 mt-2 pt-2">
          <p class="px-4 py-2 text-xs font-semibold text-gray-500">PARA VENDORS</p>
          <a
            href="/vendedor"
            class="block px-4 py-2 text-gray-700 hover:bg-gray-100"
            on:click={() => { mobileMenuOpen = false }}
          >
            📊 Ver planes
          </a>
          <a
            href="/vendedor/registro"
            class="block mx-4 mt-2 px-4 py-2 bg-primary-600 text-white rounded-lg text-center font-medium"
            on:click={() => { mobileMenuOpen = false }}
          >
            Registrarme
          </a>
        </div>
      </div>
    {/if}
  </nav>
</header>