<!--
  PÁGINA: /vendedor/registro/+page.svelte
  
  ¿QUÉ HACE?
  Muestra el formulario de registro completo
  
  RUTA: http://localhost:5173/vendedor/registro
  
  Esta página simplemente renderiza el componente VendorRegistrationForm
-->

<script lang="ts">
  /**
   * Importamos el componente del formulario
   */
  import VendorRegistrationForm from '$lib/components/VendorRegistrationForm.svelte';
</script>

<!--
  Simplemente mostramos el componente del formulario
  Todo la lógica está en VendorRegistrationForm.svelte
-->
<VendorRegistrationForm />

<!--
  META TAGS para SEO
-->
<svelte:head>
  <title>Registro de Vendor | ECOMPARTS</title>
  <meta name="description" content="Completa tu registro y empieza a vender en ECOMPARTS" />
</svelte:head>