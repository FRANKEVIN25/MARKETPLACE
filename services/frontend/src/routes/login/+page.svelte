<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';

  let username = '';
  let password = '';
  let loading = false;
  let error = '';

  async function login() {
    loading = true;
    error = '';
    try {
      const tokens = await api.auth.login(username, password);
      auth.setTokens(tokens);
      const user = await api.auth.getMe(tokens.access);
      auth.user.set(user);
      const customer = await api.customer.getProfile(tokens.access);
      auth.customer.set(customer);
      window.location.href = '/cliente/perfil';
    } catch (e: any) {
      error = 'Credenciales incorrectas. Verifica tu usuario y contraseña.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Iniciar Sesión - ECOMPARTS</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 flex items-center justify-center px-4">
  <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
    <div class="text-center mb-8">
      <div class="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center mx-auto mb-3">
        <span class="text-white font-bold text-2xl">E</span>
      </div>
      <h1 class="text-2xl font-bold text-gray-900">Iniciar Sesión</h1>
      <p class="text-gray-500 text-sm mt-1">Accede a tu cuenta ECOMPARTS</p>
    </div>

    <form on:submit|preventDefault={login} class="space-y-5">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="username">Usuario</label>
        <input id="username" type="text" bind:value={username} required autocomplete="username"
          class="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Tu nombre de usuario" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1" for="password">Contraseña</label>
        <input id="password" type="password" bind:value={password} required autocomplete="current-password"
          class="w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="••••••••" />
      </div>

      {#if error}
        <div class="bg-red-50 text-red-700 rounded-lg p-3 text-sm">{error}</div>
      {/if}

      <button type="submit" disabled={loading}
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition">
        {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
      </button>

      <p class="text-center text-sm text-gray-500">
        ¿No tienes cuenta?
        <a href="/registro" class="text-blue-600 hover:underline font-medium">Regístrate</a>
      </p>
    </form>
  </div>
</div>
