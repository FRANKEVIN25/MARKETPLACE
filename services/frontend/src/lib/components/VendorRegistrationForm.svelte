<!--
  COMPONENTE: VendorRegistrationForm.svelte
  
  ¿QUÉ HACE?
  Es el formulario completo para que un vendor se registre
  
  ¿QUÉ INCLUYE?
  1. Selección de plan (Starter, Pro, Premium)
  2. Datos del usuario (username, email, password)
  3. Datos del negocio (nombre, RUC, teléfono)
  4. Contraseña para Odoo
  5. Términos y condiciones
  6. Validaciones en tiempo real
  7. Manejo de errores
  8. Loading state mientras se envía
  
  FLUJO:
  Usuario llena form → Click "Registrar" → Se envía a API → Redirige a página de éxito
-->

<script lang="ts">
  /**
   * ==========================================
   * IMPORTS
   * ==========================================
   */
  import { goto } from '$app/navigation';  // Para redirigir a otra página
  import PricingCard from './PricingCard.svelte';  // Tarjetas de planes
  import { registerVendor, getTiers, validateRUC } from '$lib/api/vendors';  // Funciones API
  import type { VendorRegistrationData } from '$lib/api/types';  // Tipos TypeScript
  
  /**
   * ==========================================
   * ESTADO DEL FORMULARIO
   * ==========================================
   * 
   * En Svelte, usamos $state() para variables que causan re-render
   * cuando cambian. Es como useState() en React.
   */
  
  // ---- Datos del formulario ----
  // Cada campo del formulario tiene su variable
  let formData = $state<VendorRegistrationData>({
    // Datos de usuario Django
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    
    // Datos del negocio
    business_name: '',
    business_email: '',
    phone: '',
    ruc: '',
    
    // Contraseña Odoo
    odoo_password: '',
    odoo_password_confirm: '',
    
    // Plan seleccionado (por defecto: starter)
    tier: 'starter',
    
    // Términos
    accept_terms: false
  });
  
  // ---- Estados de UI ----
  let isSubmitting = $state(false);  // ¿Está enviando el formulario?
  let errors = $state<Record<string, string>>({});  // Errores de validación
  let generalError = $state('');  // Error general (del servidor)
  
  // ---- Obtener información de planes ----
  const tiers = getTiers();  // Array con los 3 planes
  
  /**
   * ==========================================
   * FUNCIONES DE VALIDACIÓN
   * ==========================================
   */
  
  /**
   * Validar un campo específico
   * Se ejecuta cuando el usuario sale del campo (onblur)
   */
  function validateField(field: keyof VendorRegistrationData): void {
    // Limpiar error anterior de este campo
    delete errors[field];
    
    // Obtener el valor actual del campo
    const value = formData[field];
    
    // Validaciones según el campo
    switch (field) {
      case 'username':
        // Username debe tener al menos 3 caracteres
        if (!value || value.length < 3) {
          errors.username = 'El nombre de usuario debe tener al menos 3 caracteres';
        }
        // Solo letras, números y guion bajo
        if (value && !/^[a-zA-Z0-9_]+$/.test(value as string)) {
          errors.username = 'Solo letras, números y guion bajo';
        }
        break;
        
      case 'email':
      case 'business_email':
        // Validar formato de email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!value || !emailRegex.test(value as string)) {
          errors[field] = 'Email inválido';
        }
        break;
        
      case 'password':
        // Password debe tener al menos 8 caracteres
        if (!value || (value as string).length < 8) {
          errors.password = 'La contraseña debe tener al menos 8 caracteres';
        }
        break;
        
      case 'password_confirm':
        // Debe coincidir con password
        if (value !== formData.password) {
          errors.password_confirm = 'Las contraseñas no coinciden';
        }
        break;
        
      case 'odoo_password':
        // Password Odoo debe tener al menos 8 caracteres
        if (!value || (value as string).length < 8) {
          errors.odoo_password = 'La contraseña debe tener al menos 8 caracteres';
        }
        break;
        
      case 'odoo_password_confirm':
        // Debe coincidir con odoo_password
        if (value !== formData.odoo_password) {
          errors.odoo_password_confirm = 'Las contraseñas no coinciden';
        }
        break;
        
      case 'ruc':
        // Validar RUC peruano (11 dígitos, empieza con 10 o 20)
        if (!value || !validateRUC(value as string)) {
          errors.ruc = 'RUC inválido (11 dígitos, debe empezar con 10 o 20)';
        }
        break;
        
      case 'phone':
        // Teléfono debe tener al menos 9 caracteres
        if (!value || (value as string).length < 9) {
          errors.phone = 'Teléfono inválido';
        }
        break;
        
      case 'business_name':
        // Nombre del negocio debe tener al menos 3 caracteres
        if (!value || (value as string).length < 3) {
          errors.business_name = 'El nombre del negocio es muy corto';
        }
        break;
    }
  }
  
  /**
   * Validar todo el formulario antes de enviar
   * Retorna true si todo está OK, false si hay errores
   */
  function validateForm(): boolean {
    // Limpiar errores anteriores
    errors = {};
    
    // Validar cada campo
    const fields: (keyof VendorRegistrationData)[] = [
      'username', 'email', 'password', 'password_confirm',
      'business_name', 'business_email', 'phone', 'ruc',
      'odoo_password', 'odoo_password_confirm'
    ];
    
    fields.forEach(field => validateField(field));
    
    // Validar términos y condiciones
    if (!formData.accept_terms) {
      errors.accept_terms = 'Debes aceptar los términos y condiciones';
    }
    
    // Si hay algún error, retornar false
    return Object.keys(errors).length === 0;
  }
  
  /**
   * ==========================================
   * MANEJO DEL FORMULARIO
   * ==========================================
   */
  
  /**
   * Se ejecuta cuando el usuario hace submit del formulario
   */
  async function handleSubmit(event: SubmitEvent): Promise<void> {
    // Prevenir el comportamiento por defecto del form (recargar página)
    event.preventDefault();
    
    // Validar formulario
    if (!validateForm()) {
      // Si hay errores, no continuar
      return;
    }
    
    // Cambiar estado a "enviando"
    isSubmitting = true;
    generalError = '';
    
    try {
      // Llamar a la API para registrar el vendor
      const response = await registerVendor(formData);
      
      // Si llegamos aquí, el registro fue exitoso
      console.log('✅ Registro exitoso:', response);
      
      // Redirigir a página de éxito
      // Pasamos el task_id en la URL para mostrar el estado
      goto(`/vendedor/registro/exitoso?task_id=${response.task_id}`);
      
    } catch (error: any) {
      // Si hubo un error, mostrarlo
      console.error('❌ Error al registrar:', error);
      generalError = error.message || 'Error al registrar. Intenta de nuevo.';
      
      // Scroll al inicio para que vea el error
      window.scrollTo({ top: 0, behavior: 'smooth' });
      
    } finally {
      // Siempre cambiar estado a "no enviando"
      isSubmitting = false;
    }
  }
  
  /**
   * Seleccionar un plan
   */
  function selectTier(tierId: 'starter' | 'pro' | 'premium'): void {
    formData.tier = tierId;
  }
</script>

<!--
  ==========================================
  HTML DEL COMPONENTE
  ==========================================
-->

<div class="container-responsive py-10 max-w-4xl">
  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// VENDEDOR / REGISTRO</p>
    <h1 class="font-display text-5xl text-bone uppercase leading-none mb-2">REGÍSTRATE COMO VENDOR</h1>
    <p class="font-mono text-xs text-steel-500">EMPIEZA A VENDER EN ECOMPARTS PERÚ</p>
  </div>

  {#if generalError}
    <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3 mb-6">
      <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
      <p class="font-mono text-xs text-rust-400">{generalError}</p>
    </div>
  {/if}

  <form onsubmit={handleSubmit} class="space-y-8">

    <!-- SECCIÓN 1: PLAN -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 01</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">SELECCIONA TU PLAN</h2>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-3 gap-4">
        {#each tiers as tier}
          <PricingCard
            {tier}
            selected={formData.tier === tier.id}
            onSelect={() => selectTier(tier.id)}
          />
        {/each}
      </div>
    </div>

    <!-- SECCIÓN 2: DATOS DE ACCESO -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 02</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">DATOS DE ACCESO</h2>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="username" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NOMBRE DE USUARIO *</label>
          <input type="text" id="username" bind:value={formData.username}
            onblur={() => validateField('username')} required
            class="input-industrial" placeholder="juan_autopartes" />
          {#if errors.username}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.username}</p>
          {/if}
        </div>

        <div>
          <label for="email" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// EMAIL *</label>
          <input type="email" id="email" bind:value={formData.email}
            onblur={() => validateField('email')} required
            class="input-industrial" placeholder="juan@example.com" />
          {#if errors.email}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.email}</p>
          {/if}
        </div>

        <div>
          <label for="password" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// CONTRASEÑA *</label>
          <input type="password" id="password" bind:value={formData.password}
            onblur={() => validateField('password')} required
            class="input-industrial" placeholder="Mínimo 8 caracteres" />
          {#if errors.password}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.password}</p>
          {/if}
        </div>

        <div>
          <label for="password_confirm" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// CONFIRMAR CONTRASEÑA *</label>
          <input type="password" id="password_confirm" bind:value={formData.password_confirm}
            onblur={() => validateField('password_confirm')} required
            class="input-industrial" placeholder="Repetir contraseña" />
          {#if errors.password_confirm}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.password_confirm}</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- SECCIÓN 3: DATOS DEL NEGOCIO -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 03</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">DATOS DEL NEGOCIO</h2>
      </div>
      <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <label for="business_name" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NOMBRE DEL NEGOCIO *</label>
          <input type="text" id="business_name" bind:value={formData.business_name}
            onblur={() => validateField('business_name')} required
            class="input-industrial" placeholder="AutoPartes Juan SAC" />
          {#if errors.business_name}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.business_name}</p>
          {/if}
        </div>

        <div>
          <label for="ruc" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// RUC *</label>
          <input type="text" id="ruc" bind:value={formData.ruc}
            onblur={() => validateField('ruc')} required maxlength="11"
            class="input-industrial" placeholder="20123456789" />
          {#if errors.ruc}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.ruc}</p>
          {/if}
        </div>

        <div>
          <label for="phone" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// TELÉFONO *</label>
          <input type="tel" id="phone" bind:value={formData.phone}
            onblur={() => validateField('phone')} required
            class="input-industrial" placeholder="+51 999 888 777" />
          {#if errors.phone}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.phone}</p>
          {/if}
        </div>

        <div class="md:col-span-2">
          <label for="business_email" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// EMAIL DEL NEGOCIO *</label>
          <input type="email" id="business_email" bind:value={formData.business_email}
            onblur={() => validateField('business_email')} required
            class="input-industrial" placeholder="ventas@autopartesjuan.com" />
          {#if errors.business_email}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.business_email}</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- SECCIÓN 4: ACCESO A ODOO -->
    <div class="bg-iron-900 border border-steel-600/25"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 04</p>
        <h2 class="font-display text-2xl text-bone uppercase leading-none">ACCESO A ODOO (ERP)</h2>
      </div>
      <div class="px-6 pt-4 pb-2">
        <div class="border border-steel-600/25 bg-iron-800/50 px-4 py-3 flex items-start gap-3 mb-4">
          <span class="w-1.5 h-1.5 bg-steel-400 flex-shrink-0 mt-1"></span>
          <p class="font-mono text-[10px] text-steel-400 leading-relaxed">
            ODOO ES EL SISTEMA DONDE GESTIONARÁS TU INVENTARIO Y PRODUCTOS. ESTA CONTRASEÑA ES DIFERENTE A TU CONTRASEÑA DE LOGIN DEL MARKETPLACE.
          </p>
        </div>
      </div>
      <div class="px-5 pb-5 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label for="odoo_password" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// CONTRASEÑA ODOO *</label>
          <input type="password" id="odoo_password" bind:value={formData.odoo_password}
            onblur={() => validateField('odoo_password')} required
            class="input-industrial" placeholder="Mínimo 8 caracteres" />
          {#if errors.odoo_password}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.odoo_password}</p>
          {/if}
        </div>

        <div>
          <label for="odoo_password_confirm" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// CONFIRMAR CONTRASEÑA ODOO *</label>
          <input type="password" id="odoo_password_confirm" bind:value={formData.odoo_password_confirm}
            onblur={() => validateField('odoo_password_confirm')} required
            class="input-industrial" placeholder="Repetir contraseña" />
          {#if errors.odoo_password_confirm}
            <p class="font-mono text-[10px] text-rust-400 mt-1">{errors.odoo_password_confirm}</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- TÉRMINOS -->
    <div>
      <label class="flex items-start gap-3 cursor-pointer group">
        <div class="relative w-4 h-4 border flex items-center justify-center flex-shrink-0 mt-0.5
                    {formData.accept_terms ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50 hover:border-steel-400'}">
          <input type="checkbox" id="accept_terms" bind:checked={formData.accept_terms} required class="sr-only" />
          {#if formData.accept_terms}
            <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          {/if}
        </div>
        <span class="font-mono text-[10px] text-steel-500 uppercase tracking-widest group-hover:text-bone transition-colors leading-relaxed">
          ACEPTO LOS <a href="/terminos" class="text-rust-500 hover:text-rust-400">TÉRMINOS Y CONDICIONES</a>
          Y LA <a href="/privacidad" class="text-rust-500 hover:text-rust-400">POLÍTICA DE PRIVACIDAD</a> *
        </span>
      </label>
      {#if errors.accept_terms}
        <p class="font-mono text-[10px] text-rust-400 mt-1 ml-7">{errors.accept_terms}</p>
      {/if}
    </div>

    <!-- BOTÓN ENVÍO -->
    <div class="flex justify-center pt-2">
      <button type="submit" disabled={isSubmitting}
        class="btn-rust px-10 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-3">
        {#if isSubmitting}
          <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          REGISTRANDO...
        {:else}
          REGISTRAR MI NEGOCIO →
        {/if}
      </button>
    </div>
  </form>
</div>