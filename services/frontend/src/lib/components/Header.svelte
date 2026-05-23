<script lang="ts">
  import { page } from '$app/stores';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';
  import { isWorkshopBusinessActivity } from '$lib/constants/customer';
  import { derived } from 'svelte/store';

  const cartCount = derived(cart, $cart => $cart.reduce((acc, item) => acc + item.cantidad, 0));
  const isAuthenticated = auth.isAuthenticated;
  const customer = auth.customer;

  let userMenuOpen = false;
  let mobileMenuOpen = false;
  let vendorMenuOpen = false;

  function toggleUserMenu()  { userMenuOpen  = !userMenuOpen;  vendorMenuOpen = false; }
  function toggleVendorMenu(){ vendorMenuOpen = !vendorMenuOpen; userMenuOpen  = false; }
  function toggleMobileMenu(){ mobileMenuOpen = !mobileMenuOpen; }

  function logout() {
    auth.clearTokens();
    userMenuOpen = false;
    window.location.href = '/';
  }

  const navigation = [
    { name: 'INICIO',    href: '/' },
    { name: 'PRODUCTOS', href: '/productos' },
    { name: 'SERVICIOS', href: '/servicios' },
  ];

  $: showWorkshopLinks = !!($customer?.is_workshop || isWorkshopBusinessActivity($customer?.business_activity));
</script>

<!-- Top accent stripe -->
<div class="h-0.5 bg-gradient-to-r from-rust-700 via-rust-600 to-rust-700 w-full"></div>

<header class="bg-iron-950 border-b border-steel-600/30 sticky top-0 z-50">
  <!-- Main nav row -->
  <nav class="container-responsive">
    <div class="flex justify-between items-center h-14">

      <!-- ── Logo ── -->
      <a href="/" class="flex items-center gap-3 group">
        <img
          src="/logo.png"
          alt="ECOMPARTS"
          class="h-11 w-11 object-contain transition-transform duration-150 group-hover:scale-105"
        />
        <div class="flex flex-col leading-none">
          <span class="font-display text-2xl text-bone tracking-widest leading-none group-hover:text-rust-400 transition-colors">ECOMPARTS</span>
          <span class="font-mono text-[8px] text-steel-500 tracking-widest uppercase">MARKETPLACE · PERÚ</span>
        </div>
      </a>

      <!-- ── Desktop nav ── -->
      <div class="hidden md:flex items-center gap-7">

        {#each navigation as item}
          <a
            href={item.href}
            class="font-mono text-[11px] uppercase tracking-industrial transition-colors duration-150
                   {$page.url.pathname === item.href
                     ? 'text-rust-600 border-b border-rust-600 pb-0.5'
                     : 'text-steel-300 hover:text-bone'}"
          >
            {item.name}
          </a>
        {/each}

        <!-- Separator -->
        <div class="w-px h-5 bg-steel-600/40"></div>

        <!-- Cart icon -->
        <a href="/carrito" class="relative flex items-center text-steel-300 hover:text-bone transition-colors" aria-label="Carrito de compras">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13l-1.4 5h11.8M7 13H5.4M9 21a1 1 0 100-2 1 1 0 000 2zm10 0a1 1 0 100-2 1 1 0 000 2z" />
          </svg>
          {#if $cartCount > 0}
            <span class="absolute -top-2 -right-2 bg-rust-600 text-bone text-[9px] font-mono font-bold
                         w-4 h-4 flex items-center justify-center leading-none">
              {$cartCount > 99 ? '99+' : $cartCount}
            </span>
          {/if}
        </a>

        <!-- User menu -->
        <div class="relative">
          {#if $isAuthenticated}
            <button
              on:click={toggleUserMenu}
              class="flex items-center gap-1.5 text-steel-300 hover:text-bone transition-colors font-mono text-[11px] uppercase tracking-industrial"
              aria-label="Mi cuenta"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <svg class="w-3 h-3 transition-transform {userMenuOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {#if userMenuOpen}
              <div class="absolute right-0 mt-2 w-56 bg-iron-900 border border-steel-600/40 z-50 shadow-2xl shadow-black/60">
                <div class="px-4 py-2 border-b border-steel-600/30">
                  <p class="font-mono text-[9px] text-steel-500 uppercase tracking-widest">MI CUENTA</p>
                </div>
                <a href="/cliente/perfil" on:click={() => userMenuOpen = false}
                   class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                  <span class="text-steel-500">—</span> PERFIL
                </a>
                <a href="/cliente/direcciones" on:click={() => userMenuOpen = false}
                   class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                  <span class="text-steel-500">—</span> DIRECCIONES
                </a>
                <a href="/cliente/historial-compras" on:click={() => userMenuOpen = false}
                   class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                  <span class="text-steel-500">—</span> MIS COMPRAS
                </a>
                {#if showWorkshopLinks}
                  <div class="border-t border-steel-600/30 my-1"></div>
                  <a href="/taller/perfil" on:click={() => userMenuOpen = false}
                     class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                    <span class="text-rust-600">—</span> MI TALLER
                  </a>
                  <a href="/taller/servicios" on:click={() => userMenuOpen = false}
                     class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                    <span class="text-rust-600">—</span> MIS SERVICIOS
                  </a>
                {/if}
                <div class="border-t border-steel-600/30 my-1"></div>
                <button on:click={logout}
                        class="w-full text-left flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-rust-500 hover:text-rust-400 hover:bg-iron-800 transition-colors uppercase tracking-wide">
                  <span>—</span> CERRAR SESIÓN
                </button>
              </div>
            {/if}

          {:else}
            <a href="/login"
               class="font-mono text-[11px] uppercase tracking-industrial text-steel-300 hover:text-bone transition-colors flex items-center gap-1.5">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M5.121 17.804A8 8 0 1118.88 17.804M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              INGRESAR
            </a>
          {/if}
        </div>

        <!-- Vendor CTA -->
        <div class="relative">
          <button
            on:click={toggleVendorMenu}
            class="flex items-center gap-2 bg-rust-600 hover:bg-rust-700 text-bone font-mono text-[11px] uppercase tracking-industrial px-4 py-2 transition-colors border border-rust-600 hover:border-rust-500"
            style="clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)"
          >
            PARA VENDORS
            <svg class="w-3 h-3 transition-transform {vendorMenuOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {#if vendorMenuOpen}
            <div class="absolute right-0 mt-2 w-56 bg-iron-900 border border-steel-600/40 z-50 shadow-2xl shadow-black/60">
              <a href="/vendedor" on:click={() => vendorMenuOpen = false}
                 class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                <span class="text-steel-500">—</span> VER PLANES Y PRECIOS
              </a>
              <a href="/vendedor#como-funciona" on:click={() => vendorMenuOpen = false}
                 class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors uppercase tracking-wide">
                <span class="text-steel-500">—</span> CÓMO FUNCIONA
              </a>
              <div class="border-t border-steel-600/30 my-1"></div>
              <a href="/vendedor/registro" on:click={() => vendorMenuOpen = false}
                 class="flex items-center gap-2 px-4 py-2.5 font-mono text-xs text-rust-500 hover:text-rust-400 hover:bg-iron-800 transition-colors uppercase tracking-wide font-bold">
                <span>→</span> REGISTRARME AHORA
              </a>
            </div>
          {/if}
        </div>
      </div>

      <!-- ── Mobile hamburger ── -->
      <button
        class="md:hidden p-2 text-steel-300 hover:text-bone transition-colors"
        on:click={toggleMobileMenu}
        aria-label="Toggle menu"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {#if mobileMenuOpen}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          {:else}
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          {/if}
        </svg>
      </button>
    </div>
  </nav>

  <!-- ── Mobile menu ── -->
  {#if mobileMenuOpen}
    <div class="md:hidden border-t border-steel-600/30 bg-iron-900">
      <div class="container-responsive py-4 space-y-1">
        {#each navigation as item}
          <a
            href={item.href}
            on:click={() => mobileMenuOpen = false}
            class="block px-4 py-3 font-mono text-xs uppercase tracking-industrial transition-colors
                   {$page.url.pathname === item.href
                     ? 'text-rust-600 bg-iron-800 border-l-2 border-rust-600'
                     : 'text-steel-300 hover:text-bone hover:bg-iron-800'}"
          >
            {item.name}
          </a>
        {/each}

        <div class="border-t border-steel-600/30 pt-4 mt-4 space-y-2">
          <p class="px-4 font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">PARA VENDORS</p>
          <a href="/vendedor" on:click={() => mobileMenuOpen = false}
             class="block px-4 py-3 font-mono text-xs uppercase tracking-industrial text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors">
            VER PLANES
          </a>
          <a href="/vendedor/registro" on:click={() => mobileMenuOpen = false}
             class="block mx-4 mt-2 bg-rust-600 text-bone font-mono text-xs uppercase tracking-industrial py-3 text-center hover:bg-rust-700 transition-colors">
            REGISTRARME AHORA →
          </a>
        </div>

        {#if $isAuthenticated}
          <div class="border-t border-steel-600/30 pt-4 mt-4 space-y-1">
            <p class="px-4 font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">MI CUENTA</p>
            <a href="/cliente/perfil" on:click={() => mobileMenuOpen = false}
               class="block px-4 py-2.5 font-mono text-xs uppercase tracking-wide text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors">
              PERFIL
            </a>
            <a href="/cliente/historial-compras" on:click={() => mobileMenuOpen = false}
               class="block px-4 py-2.5 font-mono text-xs uppercase tracking-wide text-steel-300 hover:text-bone hover:bg-iron-800 transition-colors">
              MIS COMPRAS
            </a>
            <button on:click={logout}
                    class="w-full text-left block px-4 py-2.5 font-mono text-xs uppercase tracking-wide text-rust-500 hover:text-rust-400 hover:bg-iron-800 transition-colors">
              CERRAR SESIÓN
            </button>
          </div>
        {:else}
          <div class="border-t border-steel-600/30 pt-4 mt-4">
            <a href="/login" on:click={() => mobileMenuOpen = false}
               class="block mx-4 border border-steel-600 text-bone font-mono text-xs uppercase tracking-industrial py-3 text-center hover:border-steel-400 transition-colors">
              INGRESAR
            </a>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</header>
