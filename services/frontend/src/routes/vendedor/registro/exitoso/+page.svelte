<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { getRegistrationStatus } from '$lib/api/vendors';
  import type { RegistrationStatusResponse } from '$lib/api/types';

  const taskId = $derived($page.url.searchParams.get('task_id') ?? '');

  let status = $state<RegistrationStatusResponse | null>(null);
  let pollInterval: ReturnType<typeof setInterval> | null = null;
  let pollCount = $state(0);
  const MAX_POLLS = 20;

  onMount(() => {
    if (taskId) {
      checkStatus();
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

  const isSuccess = $derived(status?.ready && status?.result?.success === true);
  const isFailure = $derived(status?.ready && status?.result?.success === false);
  const isProcessing = $derived(!status?.ready);
</script>

<svelte:head>
  <title>Registro Completado — ECOMPARTS</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center px-4 py-16">
  <div class="w-full max-w-lg">

    <!-- ✅ ÉXITO -->
    {#if isSuccess}
      <div class="bg-iron-900 border border-green-700/50"
           style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
        <div class="border-b border-green-700/30 px-8 py-5 flex items-center gap-4">
          <div class="w-10 h-10 bg-green-600/20 border border-green-700/50 flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <div>
            <p class="font-mono text-[10px] text-green-500 uppercase tracking-widest">// REGISTRO COMPLETADO</p>
            <h1 class="font-display text-3xl text-bone uppercase leading-none">¡CUENTA ACTIVA!</h1>
          </div>
        </div>

        <div class="p-8 space-y-5">
          <p class="font-mono text-xs text-steel-400 leading-relaxed">
            Tu empresa <span class="text-bone font-bold">{status?.result?.provider_name}</span> ha sido configurada correctamente en ECOMPARTS.
          </p>

          <!-- Credenciales Odoo -->
          <div class="bg-iron-800 border border-steel-600/25 p-5">
            <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-4">// CREDENCIALES ERP (ODOO)</p>
            <div class="space-y-2">
              <div class="flex items-center gap-3">
                <span class="font-mono text-[9px] text-steel-600 uppercase w-20 flex-shrink-0">URL</span>
                <a href="http://localhost:8070" target="_blank"
                   class="font-mono text-xs text-rust-500 hover:text-rust-400 transition-colors">
                  localhost:8070 →
                </a>
              </div>
              <div class="flex items-center gap-3">
                <span class="font-mono text-[9px] text-steel-600 uppercase w-20 flex-shrink-0">USUARIO</span>
                <span class="font-mono text-xs text-bone">{status?.result?.odoo_username}</span>
              </div>
              <div class="flex items-center gap-3">
                <span class="font-mono text-[9px] text-steel-600 uppercase w-20 flex-shrink-0">CONTRASEÑA</span>
                <span class="font-mono text-xs text-steel-400">La que ingresaste en el registro</span>
              </div>
            </div>
          </div>

          <!-- Aviso pendiente -->
          <div class="border border-steel-600/30 bg-iron-800/50 p-4 flex items-start gap-3">
            <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
            <p class="font-mono text-[10px] text-steel-400 uppercase tracking-wide leading-relaxed">
              Tu cuenta está <span class="text-bone">PENDIENTE DE APROBACIÓN</span> por nuestro equipo. Te avisaremos por email cuando esté activa.
            </p>
          </div>

          <a href="/" class="btn-rust block text-center">IR AL INICIO →</a>
        </div>
      </div>

    <!-- ❌ ERROR -->
    {:else if isFailure}
      <div class="bg-iron-900 border border-rust-700/50"
           style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
        <div class="border-b border-rust-700/30 px-8 py-5 flex items-center gap-4">
          <div class="w-10 h-10 bg-rust-600/20 border border-rust-700/50 flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-rust-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </div>
          <div>
            <p class="font-mono text-[10px] text-rust-500 uppercase tracking-widest">// ERROR DE CONFIGURACIÓN</p>
            <h1 class="font-display text-3xl text-bone uppercase leading-none">HUBO UN PROBLEMA</h1>
          </div>
        </div>
        <div class="p-8 space-y-5">
          <p class="font-mono text-xs text-steel-400 leading-relaxed">
            Tu usuario fue creado pero hubo un error al configurar Odoo. Nuestro equipo lo resolverá pronto.
          </p>
          <a href="/vendedor/registro" class="btn-rust block text-center">VOLVER AL REGISTRO →</a>
        </div>
      </div>

    <!-- ⏳ PROCESANDO -->
    {:else}
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-8 py-5 flex items-center gap-4">
          <svg class="animate-spin w-8 h-8 text-rust-600 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <div>
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// EN PROCESO</p>
            <h1 class="font-display text-3xl text-bone uppercase leading-none">CONFIGURANDO CUENTA...</h1>
          </div>
        </div>
        <div class="p-8 space-y-5">
          <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">
            Estamos creando tu empresa en Odoo. Esto toma unos segundos.
          </p>

          <!-- Pasos de progreso -->
          <div class="space-y-2">
            {#each [
              'USUARIO CREADO EN EL MARKETPLACE',
              'CREANDO EMPRESA EN ODOO...',
              'CONFIGURANDO PERMISOS...',
              'CONFIGURANDO ALMACÉN...'
            ] as step, i}
              <div class="flex items-center gap-3 border border-steel-600/20 bg-iron-800/50 px-4 py-3">
                {#if i === 0}
                  <div class="w-4 h-4 bg-green-600/20 border border-green-700/50 flex items-center justify-center flex-shrink-0">
                    <svg class="w-2.5 h-2.5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/>
                    </svg>
                  </div>
                {:else if i <= pollCount % 4}
                  <div class="w-4 h-4 border border-rust-600/60 flex-shrink-0 animate-pulse bg-rust-600/10"></div>
                {:else}
                  <div class="w-4 h-4 border border-steel-600/40 flex-shrink-0"></div>
                {/if}
                <span class="font-mono text-[10px] uppercase tracking-widest {i === 0 ? 'text-green-400' : i <= pollCount % 4 ? 'text-rust-500' : 'text-steel-600'}">
                  {step}
                </span>
              </div>
            {/each}
          </div>

          <p class="font-mono text-[9px] text-steel-700 uppercase tracking-widest text-center">
            NO CIERRES ESTA VENTANA
          </p>
        </div>
      </div>
    {/if}

  </div>
</div>
