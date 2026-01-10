<script lang="ts">
  import type { LayoutData } from './$types';
  import Header from '$lib/components/Header.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import '../app.css';

  export let data: LayoutData;
</script>

<div class="flex flex-col min-h-screen">
  <Header />
  
  <main class="flex-grow">
    <slot />
  </main>
  
  <Footer />
</div>