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

<div class="max-w-4xl mx-auto p-6">
  <!-- Título -->
  <div class="text-center mb-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-2">
      Regístrate como Vendor
    </h1>
    <p class="text-gray-600">
      Empieza a vender en ECOMPARTS PERÚ
    </p>
  </div>
  
  <!-- Mensaje de error general -->
  {#if generalError}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
      <p class="font-medium">Error</p>
      <p>{generalError}</p>
    </div>
  {/if}
  
  <!-- FORMULARIO -->
  <form onsubmit={handleSubmit} class="space-y-8">
    
    <!-- ========================================== -->
    <!-- SECCIÓN 1: SELECCIÓN DE PLAN -->
    <!-- ========================================== -->
    <section>
      <h2 class="text-2xl font-bold text-gray-900 mb-4">
        1. Selecciona tu plan
      </h2>
      
      <!-- Grid con las 3 tarjetas de planes -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        {#each tiers as tier}
          <PricingCard
            {tier}
            selected={formData.tier === tier.id}
            onSelect={() => selectTier(tier.id)}
          />
        {/each}
      </div>
    </section>
    
    <!-- ========================================== -->
    <!-- SECCIÓN 2: DATOS DEL USUARIO -->
    <!-- ========================================== -->
    <section>
      <h2 class="text-2xl font-bold text-gray-900 mb-4">
        2. Datos de acceso
      </h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Username -->
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
            Nombre de usuario *
          </label>
          <input
            type="text"
            id="username"
            bind:value={formData.username}
            onblur={() => validateField('username')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="juan_autopartes"
          />
          {#if errors.username}
            <p class="text-red-600 text-sm mt-1">{errors.username}</p>
          {/if}
        </div>
        
        <!-- Email -->
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700 mb-1">
            Email *
          </label>
          <input
            type="email"
            id="email"
            bind:value={formData.email}
            onblur={() => validateField('email')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="juan@example.com"
          />
          {#if errors.email}
            <p class="text-red-600 text-sm mt-1">{errors.email}</p>
          {/if}
        </div>
        
        <!-- Password -->
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
            Contraseña *
          </label>
          <input
            type="password"
            id="password"
            bind:value={formData.password}
            onblur={() => validateField('password')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Mínimo 8 caracteres"
          />
          {#if errors.password}
            <p class="text-red-600 text-sm mt-1">{errors.password}</p>
          {/if}
        </div>
        
        <!-- Confirmar Password -->
        <div>
          <label for="password_confirm" class="block text-sm font-medium text-gray-700 mb-1">
            Confirmar contraseña *
          </label>
          <input
            type="password"
            id="password_confirm"
            bind:value={formData.password_confirm}
            onblur={() => validateField('password_confirm')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Repetir contraseña"
          />
          {#if errors.password_confirm}
            <p class="text-red-600 text-sm mt-1">{errors.password_confirm}</p>
          {/if}
        </div>
      </div>
    </section>
    
    <!-- ========================================== -->
    <!-- SECCIÓN 3: DATOS DEL NEGOCIO -->
    <!-- ========================================== -->
    <section>
      <h2 class="text-2xl font-bold text-gray-900 mb-4">
        3. Datos del negocio
      </h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Nombre del negocio -->
        <div class="md:col-span-2">
          <label for="business_name" class="block text-sm font-medium text-gray-700 mb-1">
            Nombre del negocio *
          </label>
          <input
            type="text"
            id="business_name"
            bind:value={formData.business_name}
            onblur={() => validateField('business_name')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="AutoPartes Juan SAC"
          />
          {#if errors.business_name}
            <p class="text-red-600 text-sm mt-1">{errors.business_name}</p>
          {/if}
        </div>
        
        <!-- RUC -->
        <div>
          <label for="ruc" class="block text-sm font-medium text-gray-700 mb-1">
            RUC *
          </label>
          <input
            type="text"
            id="ruc"
            bind:value={formData.ruc}
            onblur={() => validateField('ruc')}
            required
            maxlength="11"
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="20123456789"
          />
          {#if errors.ruc}
            <p class="text-red-600 text-sm mt-1">{errors.ruc}</p>
          {/if}
        </div>
        
        <!-- Teléfono -->
        <div>
          <label for="phone" class="block text-sm font-medium text-gray-700 mb-1">
            Teléfono *
          </label>
          <input
            type="tel"
            id="phone"
            bind:value={formData.phone}
            onblur={() => validateField('phone')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="+51 999 888 777"
          />
          {#if errors.phone}
            <p class="text-red-600 text-sm mt-1">{errors.phone}</p>
          {/if}
        </div>
        
        <!-- Email del negocio -->
        <div class="md:col-span-2">
          <label for="business_email" class="block text-sm font-medium text-gray-700 mb-1">
            Email del negocio *
          </label>
          <input
            type="email"
            id="business_email"
            bind:value={formData.business_email}
            onblur={() => validateField('business_email')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="ventas@autopartesjuan.com"
          />
          {#if errors.business_email}
            <p class="text-red-600 text-sm mt-1">{errors.business_email}</p>
          {/if}
        </div>
      </div>
    </section>
    
    <!-- ========================================== -->
    <!-- SECCIÓN 4: ACCESO A ODOO -->
    <!-- ========================================== -->
    <section>
      <h2 class="text-2xl font-bold text-gray-900 mb-4">
        4. Acceso a Odoo (ERP)
      </h2>
      
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <p class="text-sm text-blue-800">
          💡 <strong>Odoo</strong> es el sistema donde gestionarás tu inventario y productos.
          Esta contraseña es diferente a tu contraseña de login del marketplace.
        </p>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Password Odoo -->
        <div>
          <label for="odoo_password" class="block text-sm font-medium text-gray-700 mb-1">
            Contraseña Odoo *
          </label>
          <input
            type="password"
            id="odoo_password"
            bind:value={formData.odoo_password}
            onblur={() => validateField('odoo_password')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Mínimo 8 caracteres"
          />
          {#if errors.odoo_password}
            <p class="text-red-600 text-sm mt-1">{errors.odoo_password}</p>
          {/if}
        </div>
        
        <!-- Confirmar Password Odoo -->
        <div>
          <label for="odoo_password_confirm" class="block text-sm font-medium text-gray-700 mb-1">
            Confirmar contraseña Odoo *
          </label>
          <input
            type="password"
            id="odoo_password_confirm"
            bind:value={formData.odoo_password_confirm}
            onblur={() => validateField('odoo_password_confirm')}
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Repetir contraseña"
          />
          {#if errors.odoo_password_confirm}
            <p class="text-red-600 text-sm mt-1">{errors.odoo_password_confirm}</p>
          {/if}
        </div>
      </div>
    </section>
    
    <!-- ========================================== -->
    <!-- TÉRMINOS Y CONDICIONES -->
    <!-- ========================================== -->
    <section>
      <div class="flex items-start">
        <input
          type="checkbox"
          id="accept_terms"
          bind:checked={formData.accept_terms}
          required
          class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-1"
        />
        <label for="accept_terms" class="ml-2 text-sm text-gray-700">
          Acepto los <a href="/terminos" class="text-blue-600 hover:underline">términos y condiciones</a>
          y la <a href="/privacidad" class="text-blue-600 hover:underline">política de privacidad</a> *
        </label>
      </div>
      {#if errors.accept_terms}
        <p class="text-red-600 text-sm mt-1">{errors.accept_terms}</p>
      {/if}
    </section>
    
    <!-- ========================================== -->
    <!-- BOTÓN DE ENVÍO -->
    <!-- ========================================== -->
    <div class="flex justify-center">
      <button
        type="submit"
        disabled={isSubmitting}
        class="px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        {#if isSubmitting}
          <!-- Spinner de carga -->
          <span class="flex items-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Registrando...
          </span>
        {:else}
          Registrar mi negocio
        {/if}
      </button>
    </div>
  </form>
</div>