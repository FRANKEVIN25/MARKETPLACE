<script lang="ts">
  import { api } from '$lib/api/client';
  import { auth } from '$lib/store/auth';

  type CustomerType = 'individual' | 'company';
  type DocumentType = 'DNI' | 'RUC';

  let customerType: CustomerType = 'individual';
  let documentNumber = '';
  let email = '';
  let password = '';
  let confirmPassword = '';
  let loading = false;
  let error = '';
  let fieldErrors: Record<string, string> = {};

  // El tipo de documento se deduce automáticamente del tipo de cliente
  $: documentType = (customerType === 'company' ? 'RUC' : 'DNI') as DocumentType;
  $: documentLabel = customerType === 'company' ? 'RUC (11 dígitos)' : 'DNI (8 dígitos)';
  $: documentPlaceholder = customerType === 'company' ? '20XXXXXXXXX' : '12345678';

  function validar(): boolean {
    fieldErrors = {};
    if (!documentNumber) fieldErrors.documentNumber = 'Requerido';
    else if (customerType === 'individual' && documentNumber.length !== 8)
      fieldErrors.documentNumber = 'El DNI debe tener 8 dígitos';
    else if (customerType === 'company' && documentNumber.length !== 11)
      fieldErrors.documentNumber = 'El RUC debe tener 11 dígitos';
    if (!email) fieldErrors.email = 'Requerido';
    if (!password) fieldErrors.password = 'Requerido';
    else if (password.length < 8) fieldErrors.password = 'Mínimo 8 caracteres';
    if (password !== confirmPassword) fieldErrors.confirmPassword = 'Las contraseñas no coinciden';
    return Object.keys(fieldErrors).length === 0;
  }

  async function registrar() {
    error = '';
    if (!validar()) return;
    loading = true;
    try {
      const result = await api.customer.register({ customer_type: customerType, document_type: documentType, document_number: documentNumber, email, password });
      // El backend devuelve tokens + customer en la misma respuesta — no hace falta segundo request
      auth.setTokens(result.tokens);
      auth.customer.set(result.customer);
      window.location.href = '/cliente/perfil';
    } catch (e: any) {
      const data = e?.response?.data;
      if (data && typeof data === 'object') {
        // Mostrar errores de campo del backend
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
  <title>Crear Cuenta - ECOMPARTS</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4 py-12">
  <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">

    <div class="text-center mb-8">
      <div class="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-3">
        <span class="text-white font-bold text-2xl">E</span>
      </div>
      <h1 class="text-2xl font-bold text-gray-900">Crear Cuenta</h1>
      <p class="text-gray-500 text-sm mt-1">Regístrate para comprar en ECOMPARTS</p>
    </div>

    <form on:submit|preventDefault={registrar} class="space-y-5">

      <!-- Tipo de cliente -->
      <div>
        <p class="block text-sm font-medium text-gray-700 mb-2">Tipo de cuenta</p>
        <div class="grid grid-cols-2 gap-3">
          <button type="button"
            on:click={() => customerType = 'individual'}
            class="flex flex-col items-center gap-1 border-2 rounded-xl p-4 transition cursor-pointer
              {customerType === 'individual' ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}">
            <span class="text-2xl">👤</span>
            <span class="text-sm font-semibold">Persona Natural</span>
          </button>
          <button type="button"
            on:click={() => customerType = 'company'}
            class="flex flex-col items-center gap-1 border-2 rounded-xl p-4 transition cursor-pointer
              {customerType === 'company' ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}">
            <span class="text-2xl">🏢</span>
            <span class="text-sm font-semibold">Empresa</span>
          </button>
        </div>
      </div>

      <!-- Documento -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="documentNumber">
          {documentLabel}
        </label>
        <div class="flex gap-2">
          <span class="inline-flex items-center px-3 bg-gray-100 border border-r-0 border-gray-300 rounded-l-lg text-gray-600 text-sm font-semibold">
            {documentType}
          </span>
          <input id="documentNumber" type="text" bind:value={documentNumber}
            placeholder={documentPlaceholder}
            maxlength={customerType === 'company' ? 11 : 8}
            class="flex-1 border border-gray-300 rounded-r-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500
              {fieldErrors.documentNumber ? 'border-red-400' : ''}" />
        </div>
        {#if fieldErrors.documentNumber}
          <p class="text-red-500 text-xs mt-1">{fieldErrors.documentNumber}</p>
        {/if}
      </div>

      <!-- Email -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="email">Correo electrónico</label>
        <input id="email" type="email" bind:value={email} autocomplete="email"
          placeholder="tu@email.com"
          class="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500
            {fieldErrors.email ? 'border-red-400' : ''}" />
        {#if fieldErrors.email}
          <p class="text-red-500 text-xs mt-1">{fieldErrors.email}</p>
        {/if}
      </div>

      <!-- Contraseña -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="password">Contraseña</label>
        <input id="password" type="password" bind:value={password} autocomplete="new-password"
          placeholder="Mínimo 8 caracteres"
          class="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500
            {fieldErrors.password ? 'border-red-400' : ''}" />
        {#if fieldErrors.password}
          <p class="text-red-500 text-xs mt-1">{fieldErrors.password}</p>
        {/if}
      </div>

      <!-- Confirmar contraseña -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="confirmPassword">Confirmar contraseña</label>
        <input id="confirmPassword" type="password" bind:value={confirmPassword} autocomplete="new-password"
          placeholder="Repite tu contraseña"
          class="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500
            {fieldErrors.confirmPassword ? 'border-red-400' : ''}" />
        {#if fieldErrors.confirmPassword}
          <p class="text-red-500 text-xs mt-1">{fieldErrors.confirmPassword}</p>
        {/if}
      </div>

      {#if error}
        <div class="bg-red-50 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      {/if}

      <button type="submit" disabled={loading}
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition">
        {loading ? 'Creando cuenta...' : 'Crear Cuenta'}
      </button>

      <p class="text-center text-sm text-gray-500">
        ¿Ya tienes cuenta?
        <a href="/login" class="text-blue-600 hover:underline font-medium">Inicia sesión</a>
      </p>
    </form>

  </div>
</div>
