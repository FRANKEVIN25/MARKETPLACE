<!--
  PÁGINA: /vendedor/registro/exitoso
  Muestra el estado del registro y el setup de Odoo en tiempo real
-->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { getRegistrationStatus } from '$lib/api/vendors';
  import type { RegistrationStatusResponse } from '$lib/api/types';

  // Leer task_id de la URL: /exitoso?task_id=abc-123
  const taskId = $derived($page.url.searchParams.get('task_id') ?? '');

  let status = $state<RegistrationStatusResponse | null>(null);
  let pollInterval: ReturnType<typeof setInterval> | null = null;
  let pollCount = $state(0);
  const MAX_POLLS = 20; // máximo ~40 segundos de polling

  onMount(() => {
    if (taskId) {
      checkStatus(); // primera consulta inmediata
      // Polling cada 2 segundos
      pollInterval = setInterval(() => {
        if (pollCount >= MAX_POLLS || status?.ready) {
          clearInterval(pollInterval!);
          return;
        }
        checkStatus();
      }, 2000);
    }
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  async function checkStatus() {
    try {
      pollCount++;
      status = await getRegistrationStatus(taskId);
      if (status.ready && pollInterval) {
        clearInterval(pollInterval);
      }
    } catch {
      // Silenciar errores de red durante el polling
    }
  }

  // Estado derivado para la UI
  const isSuccess = $derived(status?.ready && status?.result?.success === true);
  const isFailure = $derived(status?.ready && status?.result?.success === false);
  const isProcessing = $derived(!status?.ready);
</script>

<svelte:head>
  <title>Registro exitoso | ECOMPARTS</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-16">
  <div class="max-w-lg w-full">

    <!-- ✅ ÉXITO -->
    {#if isSuccess}
      <div class="bg-white rounded-2xl shadow-lg p-8 text-center">
        <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 mb-2">¡Registro completado!</h1>
        <p class="text-gray-600 mb-6">
          Tu empresa <strong>{status?.result?.provider_name}</strong> ha sido configurada correctamente.
        </p>

        <div class="bg-blue-50 rounded-xl p-4 text-left mb-6 space-y-2 text-sm">
          <p class="font-semibold text-blue-900">Tus credenciales de Odoo (ERP):</p>
          <p class="text-blue-800">
            🔗 <strong>URL:</strong>
            <a href="http://localhost:8070" target="_blank" class="underline">http://localhost:8070</a>
          </p>
          <p class="text-blue-800">
            👤 <strong>Usuario:</strong> {status?.result?.odoo_username}
          </p>
          <p class="text-blue-800">
            🔑 <strong>Contraseña:</strong> la que ingresaste en el registro
          </p>
        </div>

        <div class="bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-sm text-yellow-800 mb-6">
          ⏳ Tu cuenta está <strong>pendiente de aprobación</strong> por nuestro equipo.
          Te avisaremos por email cuando esté activa.
        </div>

        <a href="/" class="inline-block bg-blue-600 text-white font-semibold px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors">
          Ir al inicio
        </a>
      </div>

    <!-- ❌ ERROR -->
    {:else if isFailure}
      <div class="bg-white rounded-2xl shadow-lg p-8 text-center">
        <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 mb-2">Hubo un problema</h1>
        <p class="text-gray-600 mb-6">
          Tu usuario fue creado pero hubo un error configurando Odoo.
          Nuestro equipo lo resolverá pronto.
        </p>
        <a href="/vendedor/registro" class="inline-block bg-blue-600 text-white font-semibold px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors">
          Volver al registro
        </a>
      </div>

    <!-- ⏳ PROCESANDO -->
    {:else}
      <div class="bg-white rounded-2xl shadow-lg p-8 text-center">
        <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg class="animate-spin w-8 h-8 text-blue-600" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
        </div>
        <h1 class="text-2xl font-bold text-gray-900 mb-2">Configurando tu cuenta...</h1>
        <p class="text-gray-500 mb-6">
          Estamos creando tu empresa en Odoo. Esto toma unos segundos.
        </p>

        <!-- Pasos de progreso -->
        <div class="text-left space-y-3 mb-6">
          {#each [
            'Usuario creado en el marketplace',
            'Creando empresa en Odoo...',
            'Configurando permisos...',
            'Configurando almacén...'
          ] as step, i}
            <div class="flex items-center gap-3">
              {#if i === 0}
                <div class="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                  </svg>
                </div>
              {:else if i <= pollCount % 4}
                <div class="w-5 h-5 border-2 border-blue-500 rounded-full animate-pulse flex-shrink-0"></div>
              {:else}
                <div class="w-5 h-5 border-2 border-gray-300 rounded-full flex-shrink-0"></div>
              {/if}
              <span class="text-sm {i === 0 ? 'text-green-700 font-medium' : i <= pollCount % 4 ? 'text-blue-700' : 'text-gray-400'}">
                {step}
              </span>
            </div>
          {/each}
        </div>

        <p class="text-xs text-gray-400">No cierres esta ventana</p>
      </div>
    {/if}

  </div>
</div>
