<!--
  PÁGINA: /vendedor/registro/exitoso/+page.svelte
  
  ¿QUÉ HACE?
  Se muestra después de que el usuario se registra exitosamente
  Muestra un mensaje de éxito y el estado de la configuración de Odoo
  
  RUTA: http://localhost:5173/vendedor/registro/exitoso?task_id=xxx
  
  FLUJO:
  1. Usuario se registra
  2. Redirige aquí con task_id en URL
  3. Consultamos el estado cada 3 segundos
  4. Cuando termina, mostramos las credenciales
-->

<script lang="ts">
  /**
   * IMPORTS
   */
  import { onMount, onDestroy } from 'svelte';  // Ciclo de vida del componente
  import { page } from '$app/stores';  // Para leer parámetros de URL
  import { goto } from '$app/navigation';  // Para redirigir
  import { getRegistrationStatus } from '$lib/api/vendors';  // API
  import type { RegistrationStatusResponse } from '$lib/api/types';
  
  /**
   * ==========================================
   * ESTADO DEL COMPONENTE
   * ==========================================
   */
  
  // Obtener task_id de la URL (?task_id=xxx)
  const taskId = $page.url.searchParams.get('task_id');
  
  // Estado de la tarea
  let status = $state<RegistrationStatusResponse | null>(null);
  let isLoading = $state(true);
  let error = $state('');
  
  // Interval para consultar el estado cada 3 segundos
  let intervalId: number | null = null;
  
  /**
   * ==========================================
   * FUNCIONES
   * ==========================================
   */
  
  /**
   * Consultar el estado de la tarea
   */
  async function checkStatus(): Promise<void> {
    // Si no hay task_id, no podemos consultar
    if (!taskId) {
      error = 'No se encontró el ID de registro';
      isLoading = false;
      return;
    }
    
    try {
      // Llamar a la API
      const response = await getRegistrationStatus(taskId);
      status = response;
      
      // Si ya terminó (SUCCESS o FAILURE), detener el polling
      if (response.state === 'SUCCESS' || response.state === 'FAILURE') {
        isLoading = false;
        // Detener el interval
        if (intervalId !== null) {
          clearInterval(intervalId);
        }
      }
      
    } catch (err: any) {
      console.error('Error al consultar estado:', err);
      error = 'Error al consultar el estado';
      isLoading = false;
      
      // Detener el interval
      if (intervalId !== null) {
        clearInterval(intervalId);
      }
    }
  }
  
  /**
   * ==========================================
   * CICLO DE VIDA DEL COMPONENTE
   * ==========================================
   */
  
  // onMount se ejecuta cuando el componente se monta (aparece en pantalla)
  onMount(() => {
    // Consultar inmediatamente
    checkStatus();
    
    // Luego consultar cada 3 segundos
    intervalId = setInterval(() => {
      checkStatus();
    }, 3000);
  });
  
  // onDestroy se ejecuta cuando el componente se desmonta (desaparece)
  onDestroy(() => {
    // Limpiar el interval para no tener memory leaks
    if (intervalId !== null) {
      clearInterval(intervalId);
    }
  });
  
  /**
   * Ir al login
   */
  function goToLogin(): void {
    goto('/login');  // Ajusta la ruta según tu app
  }
</script>

<!--
  ==========================================
  HTML DEL COMPONENTE
  ==========================================
-->

<div class="max-w-3xl mx-auto px-6 py-16">
  
  <!-- ========================================== -->
  <!-- HEADER DE ÉXITO -->
  <!-- ========================================== -->
  <div class="text-center mb-8">
    <!-- Icono de check verde -->
    <div class="bg-green-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
      <svg class="w-12 h-12 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
    </div>
    
    <h1 class="text-3xl font-bold text-gray-900 mb-2">
      ¡Registro exitoso!
    </h1>
    <p class="text-gray-600">
      Tu cuenta ha sido creada correctamente
    </p>
  </div>
  
  <!-- ========================================== -->
  <!-- ESTADO DE LA CONFIGURACIÓN -->
  <!-- ========================================== -->
  <div class="bg-white rounded-lg border-2 border-gray-200 p-6 mb-6">
    <h2 class="text-xl font-bold mb-4">Estado de configuración</h2>
    
    {#if error}
      <!-- Error -->
      <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        <p>{error}</p>
      </div>
      
    {:else if isLoading || status?.state === 'PENDING'}
      <!-- Loading -->
      <div class="flex items-center">
        <!-- Spinner -->
        <svg class="animate-spin h-6 w-6 text-blue-600 mr-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <div>
          <p class="font-medium text-gray-900">Configurando tu cuenta...</p>
          <p class="text-sm text-gray-600">
            Estamos creando tu Company y usuario en Odoo. Esto puede tardar 30-60 segundos.
          </p>
        </div>
      </div>
      
    {:else if status?.state === 'SUCCESS'}
      <!-- Éxito -->
      <div class="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded mb-4">
        <p class="font-medium">✅ Configuración completada</p>
        <p class="text-sm">Tu acceso a Odoo está listo</p>
      </div>
      
      <!-- Información de acceso -->
      <div class="bg-blue-50 border border-blue-200 rounded p-4 mb-4">
        <h3 class="font-bold text-gray-900 mb-2">📋 Tus credenciales de acceso:</h3>
        <div class="space-y-2 text-sm">
          <div>
            <span class="font-medium">URL Odoo:</span>
            <span class="ml-2 font-mono bg-white px-2 py-1 rounded">http://localhost:8070</span>
          </div>
          <div>
            <span class="font-medium">Usuario:</span>
            <span class="ml-2 font-mono bg-white px-2 py-1 rounded">
              {status.result?.odoo_username || 'Tu email de negocio'}
            </span>
          </div>
          <div>
            <span class="font-medium">Contraseña:</span>
            <span class="ml-2">La contraseña de Odoo que elegiste</span>
          </div>
        </div>
      </div>
      
      <div class="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded text-sm">
        <p>
          ⚠️ <strong>Importante:</strong> Tu cuenta está pendiente de aprobación por parte de nuestro equipo.
          Recibirás un email cuando sea aprobada (usualmente en 24-48 horas).
        </p>
      </div>
      
    {:else if status?.state === 'FAILURE'}
      <!-- Error en configuración -->
      <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        <p class="font-medium">❌ Error en la configuración</p>
        <p class="text-sm mt-1">
          {status.error || 'Ocurrió un error al configurar tu cuenta'}
        </p>
        <p class="text-sm mt-2">
          Por favor contacta a soporte: soporte@ecomparts.pe
        </p>
      </div>
    {/if}
  </div>
  
  <!-- ========================================== -->
  <!-- PRÓXIMOS PASOS -->
  <!-- ========================================== -->
  {#if status?.state === 'SUCCESS'}
    <div class="bg-white rounded-lg border-2 border-gray-200 p-6 mb-6">
      <h2 class="text-xl font-bold mb-4">Próximos pasos</h2>
      
      <ol class="space-y-4">
        <li class="flex items-start">
          <span class="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3 font-bold">
            1
          </span>
          <div>
            <p class="font-medium">Revisa tu email</p>
            <p class="text-sm text-gray-600">
              Te enviamos un email de confirmación con todos los detalles
            </p>
          </div>
        </li>
        
        <li class="flex items-start">
          <span class="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3 font-bold">
            2
          </span>
          <div>
            <p class="font-medium">Accede a Odoo</p>
            <p class="text-sm text-gray-600">
              Empieza a cargar tus productos desde el sistema ERP
            </p>
            <a 
              href="http://localhost:8070" 
              target="_blank"
              class="text-blue-600 hover:underline text-sm mt-1 inline-block"
            >
              Abrir Odoo →
            </a>
          </div>
        </li>
        
        <li class="flex items-start">
          <span class="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3 font-bold">
            3
          </span>
          <div>
            <p class="font-medium">Espera la aprobación</p>
            <p class="text-sm text-gray-600">
              Nuestro equipo revisará tu cuenta en 24-48 horas
            </p>
          </div>
        </li>
        
        <li class="flex items-start">
          <span class="bg-blue-600 text-white w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mr-3 font-bold">
            4
          </span>
          <div>
            <p class="font-medium">¡Empieza a vender!</p>
            <p class="text-sm text-gray-600">
              Una vez aprobado, tus productos estarán visibles en el marketplace
            </p>
          </div>
        </li>
      </ol>
    </div>
    
    <!-- Botones -->
    <div class="flex justify-center gap-4">
      <a
        href="http://localhost:8070"
        target="_blank"
        class="bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
      >
        Acceder a Odoo
      </a>
      <a
        href="/"
        class="bg-gray-100 text-gray-700 px-6 py-3 rounded-lg font-medium hover:bg-gray-200 transition-colors"
      >
        Volver al inicio
      </a>
    </div>
  {/if}
</div>

<!--
  META TAGS
-->
<svelte:head>
  <title>Registro Exitoso | ECOMPARTS</title>
</svelte:head>