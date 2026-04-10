<script lang="ts">
  import type { LayoutData } from './$types';
  import { onMount } from 'svelte';
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import { cart } from '$lib/store/cart';
  import '../app.css';

  onMount(() => {
    // Limpiar el carrito provisional de localStorage si existía
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('ecomparts_cart');
    }
    cart.refresh();
  });
</script>

<div class="flex flex-col min-h-screen">
  <Header />
  
  <main class="flex-grow">
    <slot />
  </main>
  
  <Footer />
</div>