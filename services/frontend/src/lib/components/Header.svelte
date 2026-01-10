<script lang="ts">
  import { page } from '$app/stores';

  const navigation = [
    { name: 'Inicio', href: '/' },
    { name: 'Productos', href: '/productos' },
    { name: 'Categorías', href: '/categorias' },
  ];

  let mobileMenuOpen = false;

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
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
      </div>
    {/if}
  </nav>
</header>