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
  <title>Iniciar Sesión — ECOMPARTS</title>
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
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// ACCESO</p>
        <h1 class="font-display text-4xl text-bone uppercase leading-none">INICIAR SESIÓN</h1>
      </div>
    </div>

    <!-- Card -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 0 100%)">
      <div class="p-8">
        <form on:submit|preventDefault={login} class="space-y-5">

          <!-- Usuario -->
          <div>
            <label class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2" for="username">
              // USUARIO
            </label>
            <input
              id="username"
              type="text"
              bind:value={username}
              required
              autocomplete="username"
              placeholder="Tu nombre de usuario"
              class="input-industrial"
            />
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
              required
              autocomplete="current-password"
              placeholder="••••••••"
              class="input-industrial"
            />
          </div>

          <!-- Error -->
          {#if error}
            <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
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
            {loading ? 'VERIFICANDO...' : 'INGRESAR →'}
          </button>

          <!-- Link registro -->
          <div class="border-t border-steel-600/25 pt-5 text-center">
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
              ¿SIN CUENTA?&nbsp;
              <a href="/registro" class="text-rust-500 hover:text-rust-400 transition-colors">REGÍSTRATE</a>
            </p>
          </div>
        </form>
      </div>
    </div>

  </div>
</div>
