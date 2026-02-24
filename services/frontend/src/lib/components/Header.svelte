<script lang="ts">
  import { page } from '$app/stores';
  
  const navigation = [
    { name: 'Inicio', href: '/' },
    { name: 'Productos', href: '/productos' },
    { name: 'Categorías', href: '/categorias' },
  ];
  
  let mobileMenuOpen = false;
  let vendorMenuOpen = false;
  
  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
  }
  
  function toggleVendorMenu() {
    vendorMenuOpen = !vendorMenuOpen;
  }
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