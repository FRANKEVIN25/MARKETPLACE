<script lang="ts">
  import { api } from '$lib/api/client';
  import { auth } from '$lib/store/auth';
  import {
    BUSINESS_ACTIVITY_OPTIONS,
    type BusinessActivity,
  } from '$lib/constants/customer';

  type CustomerType = 'individual' | 'company';
  type DocumentType = 'DNI' | 'RUC';

  let customerType: CustomerType = 'individual';
  let documentNumber = '';
  let businessActivity: BusinessActivity | '' = '';
  let email = '';
  let password = '';
  let confirmPassword = '';
  let loading = false;
  let error = '';
  let fieldErrors: Record<string, string> = {};

  $: documentType = (customerType === 'company' ? 'RUC' : 'DNI') as DocumentType;
  $: documentLabel = customerType === 'company' ? 'RUC (11 DÍGITOS)' : 'DNI (8 DÍGITOS)';
  $: documentPlaceholder = customerType === 'company' ? '20XXXXXXXXX' : '12345678';

  function validar(): boolean {
    fieldErrors = {};
    if (!documentNumber) fieldErrors.documentNumber = 'REQUERIDO';
    else if (customerType === 'individual' && documentNumber.length !== 8)
      fieldErrors.documentNumber = 'EL DNI DEBE TENER 8 DÍGITOS';
    else if (customerType === 'company' && documentNumber.length !== 11)
      fieldErrors.documentNumber = 'EL RUC DEBE TENER 11 DÍGITOS';
    if (customerType === 'company' && !businessActivity)
      fieldErrors.businessActivity = 'SELECCIONA EL TIPO DE EMPRESA';
    if (!email) fieldErrors.email = 'REQUERIDO';
    if (!password) fieldErrors.password = 'REQUERIDO';
    else if (password.length < 8) fieldErrors.password = 'MÍNIMO 8 CARACTERES';
    if (password !== confirmPassword) fieldErrors.confirmPassword = 'LAS CONTRASEÑAS NO COINCIDEN';
    return Object.keys(fieldErrors).length === 0;
  }

  async function registrar() {
    error = '';
    if (!validar()) return;
    loading = true;
    try {
      const result = await api.customer.register({
        customer_type: customerType,
        document_type: documentType,
        document_number: documentNumber,
        business_activity: businessActivity,
        email,
        password,
      });
      auth.setTokens(result.tokens);
      auth.customer.set(result.customer);
      window.location.href = '/cliente/perfil';
    } catch (e: any) {
      const data = e?.response?.data;
      if (data && typeof data === 'object') {
        const msgs = Object.values(data).flat().join(' ');
        error = msgs || 'Error al registrarse. Intenta de nuevo.';
      } else {
        error = 'Error al registrarse. Intenta de nuevo.';
      }
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Crear Cuenta — ECOMPARTS</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center px-4 py-16">
  <div class="w-full max-w-md">

    <!-- Logo + header -->
    <div class="text-center mb-10">
      <a href="/" class="inline-flex flex-col items-center gap-2 group">
        <div class="w-14 h-14 bg-rust-600 flex items-center justify-center group-hover:bg-rust-700 transition-colors"
             style="clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)">
          <span class="font-display text-3xl text-bone leading-none">E</span>
        </div>
        <span class="font-display text-2xl text-bone uppercase tracking-widest group-hover:text-rust-400 transition-colors">ECOMPARTS</span>
      </a>
      <div class="mt-6 border-b border-steel-600/30 pb-6">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// REGISTRO</p>
        <h1 class="font-display text-4xl text-bone uppercase leading-none">CREAR CUENTA</h1>
      </div>
    </div>

    <!-- Card -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)">
      <div class="p-8">
        <form on:submit|preventDefault={registrar} class="space-y-5">

          <!-- Tipo de cuenta -->
          <div>
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-3">// TIPO DE CUENTA</p>
            <div class="grid grid-cols-2 gap-3">
              <button
                type="button"
                on:click={() => { customerType = 'individual'; businessActivity = ''; }}
                class="flex flex-col items-center gap-2 border py-4 px-3 transition-all duration-150
                  {customerType === 'individual'
                    ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                    : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <span class="font-mono text-[10px] uppercase tracking-widest">PERSONA NATURAL</span>
              </button>
              <button
                type="button"
                on:click={() => customerType = 'company'}
                class="flex flex-col items-center gap-2 border py-4 px-3 transition-all duration-150
                  {customerType === 'company'
                    ? 'border-rust-600 bg-rust-600/10 text-rust-400'
                    : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <span class="font-mono text-[10px] uppercase tracking-widest">EMPRESA</span>
              </button>
            </div>
          </div>

          <!-- Documento -->
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="documentNumber">
              // {documentLabel}
            </label>
            <div class="flex gap-0">
              <span class="flex items-center px-3 bg-iron-800 border border-r-0 border-steel-600/50
                           font-mono text-xs text-steel-400 uppercase tracking-widest whitespace-nowrap">
                {documentType}
              </span>
              <input
                id="documentNumber"
                type="text"
                bind:value={documentNumber}
                placeholder={documentPlaceholder}
                maxlength={customerType === 'company' ? 11 : 8}
                class="flex-1 input-industrial {fieldErrors.documentNumber ? 'border-rust-600/70' : ''}"
              />
            </div>
            {#if fieldErrors.documentNumber}
              <p class="font-mono text-[9px] text-rust-500 mt-1 uppercase tracking-widest">{fieldErrors.documentNumber}</p>
            {/if}
          </div>

          <!-- Actividad económica (empresa) -->
          {#if customerType === 'company'}
            <div>
              <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="businessActivity">
                // ACTIVIDAD ECONÓMICA
              </label>
              <select
                id="businessActivity"
                bind:value={businessActivity}
                class="input-industrial {fieldErrors.businessActivity ? 'border-rust-600/70' : ''}"
              >
                <option value="">Selecciona el tipo de empresa</option>
                {#each BUSINESS_ACTIVITY_OPTIONS as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
              <p class="font-mono text-[9px] text-steel-600 mt-1 uppercase tracking-widest">
                SOLO TALLERES MECÁNICOS VEN LA CONFIGURACIÓN DE TALLER
              </p>
              {#if fieldErrors.businessActivity}
                <p class="font-mono text-[9px] text-rust-500 mt-1 uppercase tracking-widest">{fieldErrors.businessActivity}</p>
              {/if}
            </div>
          {/if}

          <!-- Email -->
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="email">
              // CORREO ELECTRÓNICO
            </label>
            <input
              id="email"
              type="email"
              bind:value={email}
              autocomplete="email"
              placeholder="tu@email.com"
              class="input-industrial {fieldErrors.email ? 'border-rust-600/70' : ''}"
            />
            {#if fieldErrors.email}
              <p class="font-mono text-[9px] text-rust-500 mt-1 uppercase tracking-widest">{fieldErrors.email}</p>
            {/if}
          </div>

          <!-- Contraseña -->
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="password">
              // CONTRASEÑA
            </label>
            <input
              id="password"
              type="password"
              bind:value={password}
              autocomplete="new-password"
              placeholder="Mínimo 8 caracteres"
              class="input-industrial {fieldErrors.password ? 'border-rust-600/70' : ''}"
            />
            {#if fieldErrors.password}
              <p class="font-mono text-[9px] text-rust-500 mt-1 uppercase tracking-widest">{fieldErrors.password}</p>
            {/if}
          </div>

          <!-- Confirmar contraseña -->
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="confirmPassword">
              // CONFIRMAR CONTRASEÑA
            </label>
            <input
              id="confirmPassword"
              type="password"
              bind:value={confirmPassword}
              autocomplete="new-password"
              placeholder="Repite tu contraseña"
              class="input-industrial {fieldErrors.confirmPassword ? 'border-rust-600/70' : ''}"
            />
            {#if fieldErrors.confirmPassword}
              <p class="font-mono text-[9px] text-rust-500 mt-1 uppercase tracking-widest">{fieldErrors.confirmPassword}</p>
            {/if}
          </div>

          <!-- Error global -->
          {#if error}
            <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-start gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
              <p class="font-mono text-xs text-rust-400">{error}</p>
            </div>
          {/if}

          <!-- Submit -->
          <button
            type="submit"
            disabled={loading}
            class="w-full bg-rust-600 hover:bg-rust-700 disabled:opacity-50 disabled:cursor-not-allowed
                   text-bone font-display text-xl uppercase tracking-widest py-4 transition-colors"
            style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)"
          >
            {loading ? 'CREANDO CUENTA...' : 'CREAR CUENTA →'}
          </button>

          <!-- Link login -->
          <div class="border-t border-steel-600/25 pt-5 text-center">
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
              ¿YA TIENES CUENTA?&nbsp;
              <a href="/login" class="text-rust-500 hover:text-rust-400 transition-colors">INICIA SESIÓN</a>
            </p>
          </div>
        </form>
      </div>
    </div>

  </div>
</div>
