<!--
  PÁGINA: /vendedor/+page.svelte
  
  ¿QUÉ HACE?
  Esta es la landing page para vendors (proveedores)
  Muestra información sobre vender en ECOMPARTS y un botón para registrarse
  
  RUTA: http://localhost:5173/vendedor
  
  ESTRUCTURA:
  - Hero section (sección principal con título grande y CTA)
  - Beneficios de vender en la plataforma
  - Cómo funciona (3 pasos)
  - Botón para ir al formulario de registro
-->

<script lang="ts">
  /**
   * IMPORTS
   */
  import { goto } from '$app/navigation';  // Para navegar a otras páginas
  
  /**
   * Función para ir a la página de registro
   */
  function goToRegistration(): void {
    goto('/vendedor/registro');
  }
</script>

<!--
  ==========================================
  HERO SECTION
  ==========================================
  Sección principal con título grande y call-to-action
-->
<div class="bg-gradient-to-r from-blue-600 to-blue-800 text-white">
  <div class="max-w-6xl mx-auto px-6 py-20 text-center">
    <h1 class="text-5xl font-bold mb-6">
      Vende tus autopartes en ECOMPARTS
    </h1>
    <p class="text-xl mb-8 text-blue-100">
      Llega a miles de clientes en todo el Perú
    </p>
    <button
      onclick={goToRegistration}
      class="bg-white text-blue-600 px-8 py-3 rounded-lg font-bold text-lg hover:bg-blue-50 transition-colors"
    >
      Registrarme ahora
    </button>
  </div>
</div>

<!--
  ==========================================
  BENEFICIOS
  ==========================================
  Por qué vender en ECOMPARTS
-->
<section class="max-w-6xl mx-auto px-6 py-16">
  <h2 class="text-3xl font-bold text-center mb-12">
    ¿Por qué vender con nosotros?
  </h2>
  
  <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
    <!-- Beneficio 1 -->
    <div class="text-center">
      <div class="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
      <h3 class="text-xl font-bold mb-2">Miles de clientes</h3>
      <p class="text-gray-600">
        Accede a una base de clientes en constante crecimiento
      </p>
    </div>
    
    <!-- Beneficio 2 -->
    <div class="text-center">
      <div class="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
      </div>
      <h3 class="text-xl font-bold mb-2">Gestión fácil</h3>
      <p class="text-gray-600">
        Sistema ERP integrado (Odoo) para gestionar tu inventario
      </p>
    </div>
    
    <!-- Beneficio 3 -->
    <div class="text-center">
      <div class="bg-blue-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <h3 class="text-xl font-bold mb-2">Pagos seguros</h3>
      <p class="text-gray-600">
        Recibe tus pagos de forma segura y puntual
      </p>
    </div>
  </div>
</section>

<!--
  ==========================================
  CÓMO FUNCIONA
  ==========================================
  3 pasos simples para empezar a vender
-->
<section class="bg-gray-50 py-16">
  <div class="max-w-6xl mx-auto px-6">
    <h2 class="text-3xl font-bold text-center mb-12">
      Cómo funciona
    </h2>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- Paso 1 -->
      <div class="relative">
        <div class="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mb-4">
          1
        </div>
        <h3 class="text-xl font-bold mb-2">Regístrate</h3>
        <p class="text-gray-600">
          Crea tu cuenta en menos de 5 minutos. Es gratis y sin compromiso.
        </p>
      </div>
      
      <!-- Paso 2 -->
      <div class="relative">
        <div class="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mb-4">
          2
        </div>
        <h3 class="text-xl font-bold mb-2">Carga tus productos</h3>
        <p class="text-gray-600">
          Agrega tu catálogo de productos desde el sistema Odoo integrado.
        </p>
      </div>
      
      <!-- Paso 3 -->
      <div class="relative">
        <div class="bg-blue-600 text-white w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold mb-4">
          3
        </div>
        <h3 class="text-xl font-bold mb-2">Empieza a vender</h3>
        <p class="text-gray-600">
          Recibe pedidos y gestiona tu negocio desde un solo lugar.
        </p>
      </div>
    </div>
  </div>
</section>

<!--
  ==========================================
  PLANES
  ==========================================
  Breve mención de los planes (sin detalle)
-->
<section class="max-w-6xl mx-auto px-6 py-16">
  <h2 class="text-3xl font-bold text-center mb-8">
    Planes para todos los tamaños de negocio
  </h2>
  <p class="text-center text-gray-600 mb-8">
    Desde emprendedores hasta grandes distribuidoras
  </p>
  
  <div class="flex justify-center gap-4">
    <div class="bg-gray-50 px-6 py-3 rounded-lg">
      <span class="font-bold">Starter</span> - Gratis
    </div>
    <div class="bg-blue-50 px-6 py-3 rounded-lg border-2 border-blue-500">
      <span class="font-bold">Pro</span> - S/ 99/mes
    </div>
    <div class="bg-gray-50 px-6 py-3 rounded-lg">
      <span class="font-bold">Premium</span> - S/ 299/mes
    </div>
  </div>
</section>

<!--
  ==========================================
  CTA FINAL
  ==========================================
  Llamado final a la acción
-->
<section class="bg-blue-600 text-white py-16">
  <div class="max-w-4xl mx-auto px-6 text-center">
    <h2 class="text-3xl font-bold mb-4">
      ¿Listo para empezar a vender?
    </h2>
    <p class="text-xl mb-8 text-blue-100">
      Únete a los cientos de vendors que confían en ECOMPARTS
    </p>
    <button
      onclick={goToRegistration}
      class="bg-white text-blue-600 px-8 py-3 rounded-lg font-bold text-lg hover:bg-blue-50 transition-colors"
    >
      Crear mi cuenta gratis
    </button>
  </div>
</section>

<!--
  ==========================================
  META TAGS (SEO)
  ==========================================
  Esto mejora el SEO de la página
-->
<svelte:head>
  <title>Vende en ECOMPARTS | Marketplace de Autopartes</title>
  <meta name="description" content="Registra tu negocio y vende autopartes a miles de clientes en todo el Perú. Sistema de gestión integrado, pagos seguros y comisiones competitivas." />
</svelte:head>