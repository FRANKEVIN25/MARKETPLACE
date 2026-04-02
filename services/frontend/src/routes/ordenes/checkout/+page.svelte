<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import { goto } from '$app/navigation';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import {
    checkout,
    checkoutStepIndex,
    checkoutSubtotal,
    checkoutItemsByProvider,
    checkoutProviderCount,
    CHECKOUT_STEPS,
    STEP_LABELS,
  } from '$lib/store/checkout';
  import type { Customer, Address, SubOrder, PaymentMethod } from '$lib/api/types';

  // ─── Estado reactivo del store ───────────────────────────────────────────────
  $: state        = $checkout;
  $: stepIdx      = $checkoutStepIndex;
  $: subtotal     = $checkoutSubtotal;
  $: byProvider   = $checkoutItemsByProvider;
  $: provCount    = $checkoutProviderCount;

  // ─── Inicialización ──────────────────────────────────────────────────────────
  onMount(async () => {
    const items = get(cart);
    if (items.length === 0) {
      goto('/carrito');
      return;
    }

    const token = auth.getAccessToken();
    if (!token) {
      goto('/login');
      return;
    }

    // Cargar perfil del cliente si no está en el store
    let customer: Customer | null = get(auth.customer);
    if (!customer) {
      try {
        customer = await api.customer.getProfile(token);
        auth.customer.set(customer);
      } catch {
        goto('/login');
        return;
      }
    }

    checkout.init(items, customer);
  });

  // ─── Helpers visuales ────────────────────────────────────────────────────────
  const STEP_ICONS: Record<string, string> = {
    carrito:      '🛒',
    perfil:       '👤',
    entrega:      '🚚',
    pago:         '💳',
  };

  function fmt(n: number) {
    return `S/ ${n.toFixed(2)}`;
  }

  // ─── Paso Pago ───────────────────────────────────────────────────────────────

  // Un formulario de comprobante por sub-orden
  interface ProofForm {
    payment_method: PaymentMethod;
    operation_number: string;
    amount: string;
    file: File | null;
    uploading: boolean;
    uploaded: boolean;
    error: string;
  }

  // Mapa subOrderId → formulario
  let proofForms: Record<number, ProofForm> = {};

  // Inicializar formularios cuando llega la orden
  $: if (state.order) {
    for (const sub of state.order.sub_orders) {
      if (!proofForms[sub.id]) {
        proofForms[sub.id] = {
          payment_method: 'transferencia',
          operation_number: '',
          amount: sub.total,
          file: null,
          uploading: false,
          uploaded: false,
          error: '',
        };
      }
    }
  }

  function onFileChange(subId: number, e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files?.[0]) {
      proofForms[subId].file = input.files[0];
      proofForms[subId] = { ...proofForms[subId] };
    }
  }

  async function subirComprobante(sub: SubOrder) {
    const form = proofForms[sub.id];
    if (!form.file) { proofForms[sub.id].error = 'Debes adjuntar un comprobante.'; return; }
    if (!form.amount || parseFloat(form.amount) <= 0) { proofForms[sub.id].error = 'Ingresa el monto pagado.'; return; }

    const token = auth.getAccessToken();
    if (!token) return;

    proofForms[sub.id] = { ...form, uploading: true, error: '' };
    try {
      await api.orders.uploadPaymentProof(token, {
        sub_order_id: sub.id,
        payment_method: form.payment_method,
        file: form.file,
        operation_number: form.operation_number,
        amount: parseFloat(form.amount),
      });
      proofForms[sub.id] = { ...proofForms[sub.id], uploading: false, uploaded: true };
      // Transición optimista: actualiza el status en el store para que
      // subsRealmentePendientes se recalcule y detenga el countdown si
      // ya no quedan subórdenes en 'pendiente_pago'.
      checkout.patchSubOrderStatus(sub.id, 'pago_en_revision');
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Error al subir el comprobante.';
      proofForms[sub.id] = { ...proofForms[sub.id], uploading: false, error: msg };
    }
  }

  // Todos los comprobantes subidos (excluyendo subórdenes canceladas/expiradas)
  $: activeSubs = state.order
    ? state.order.sub_orders.filter(s => s.status !== 'cancelado' && !s.expired)
    : [];
  $: todosSubidos = activeSubs.length > 0
    ? activeSubs.every(s => proofForms[s.id]?.uploaded)
    : false;

  // ─── Countdown timer (payment_deadline) ─────────────────────────────────────
  let countdown = '';
  let countdownInterval: ReturnType<typeof setInterval> | null = null;

  function startCountdown(deadline: string) {
    if (countdownInterval) clearInterval(countdownInterval);
    function tick() {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) {
        countdown = 'expirado';
        clearInterval(countdownInterval!);
        countdownInterval = null;
        return;
      }
      const h = Math.floor(diff / 3_600_000);
      const m = Math.floor((diff % 3_600_000) / 60_000);
      const s = Math.floor((diff % 60_000) / 1_000);
      countdown = `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
    }
    tick();
    countdownInterval = setInterval(tick, 1_000);
  }

  // Arrancar el countdown solo si hay subórdenes genuinamente pendientes
  $: subsRealmentePendientes = state.order
    ? state.order.sub_orders.filter(s => s.status === 'pendiente_pago' && !s.expired)
    : [];

  $: hayPagosPendientes = subsRealmentePendientes.length > 0;

  // Guard: solo iniciar si no hay ya un interval corriendo, para no reiniciar
  // el timer en cada re-render reactivo mientras hayPagosPendientes sigue true.
  $: if (state.order?.payment_deadline && state.step === 'pago' && hayPagosPendientes && !countdownInterval) {
    startCountdown(state.order.payment_deadline);
  }

  // Detener el countdown cuando ya no hay pagos pendientes
  $: if (!hayPagosPendientes && countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
    countdown = '';
  }

  onDestroy(() => { if (countdownInterval) clearInterval(countdownInterval); });

  $: deadlineExpired = countdown === 'expirado';

  // ─── Paso Perfil ─────────────────────────────────────────────────────────────
  let termsAccepted = false;
  let dataAccepted  = false;

  const PAYMENT_METHOD_LABELS: Record<string, string> = {
    transferencia:          'Transferencia bancaria',
    yape:                   'Yape',
    plin:                   'Plin',
    efectivo_contraentrega: 'Efectivo contraentrega',
    efectivo_tienda:        'Efectivo en tienda',
  };


  function continuarAPerfil() {
    if (!termsAccepted) return;
    checkout.nextStep();
    // Cargar direcciones al llegar a Entrega (anticipado)
    if (!addresses.length) cargarDirecciones();
  }

  // ─── Paso Entrega ─────────────────────────────────────────────────────────────
  let addresses: Address[]  = [];
  let loadingAddresses      = false;
  let mostrarFormDireccion  = false;
  let selectedAddressId: number | null = null;
  let guardandoDireccion    = false;

  const ADDR_FORM_EMPTY = {
    address_type: 'shipping' as 'shipping' | 'agency' | 'business',
    contact_name: '', contact_phone: '',
    street: '', street_number: '', apartment: '',
    district: '', city: '', state: '',
    postal_code: '', country: 'Perú',
    reference: '', is_default: false, agency_name: '',
  };
  let nuevaDir = { ...ADDR_FORM_EMPTY };

  async function cargarDirecciones() {
    const token = auth.getAccessToken();
    if (!token || loadingAddresses) return;
    loadingAddresses = true;
    try {
      addresses = await api.customer.getAddresses(token);
      const def = addresses.find(a => a.is_default);
      if (def) { selectedAddressId = def.id; checkout.setShippingAddress(def); }
    } catch {
      checkout.setError('No se pudieron cargar tus direcciones.');
    } finally {
      loadingAddresses = false;
    }
  }

  function seleccionarDireccion(addr: Address) {
    selectedAddressId = addr.id;
    checkout.setShippingAddress(addr);
    mostrarFormDireccion = false;
  }

  async function agregarNuevaDireccion() {
    const token = auth.getAccessToken();
    if (!token) return;
    guardandoDireccion = true;
    checkout.setError('');
    try {
      const created = await api.customer.createAddress(token, nuevaDir);
      addresses = [...addresses, created];
      seleccionarDireccion(created);
      nuevaDir = { ...ADDR_FORM_EMPTY };
    } catch {
      checkout.setError('No se pudo guardar la dirección.');
    } finally {
      guardandoDireccion = false;
    }
  }

  function continuarAEntrega() {
    checkout.nextStep();
    if (!addresses.length) cargarDirecciones();
  }

  // ─── Crear orden ──────────────────────────────────────────────────────────────
  async function crearOrden() {
    const token = auth.getAccessToken();
    if (!token) return;
    const s = $checkout;

    if (s.deliveryMethod !== 'tienda' && !s.shippingAddress) {
      checkout.setError('Debes seleccionar una dirección de envío.');
      return;
    }

    checkout.setLoading(true);
    checkout.setError('');
    try {
      const order = await api.orders.createOrder(token, {
        customer_id: s.customer!.id,
        delivery_method: s.deliveryMethod,
        shipping_address_id: s.shippingAddress?.id ?? null,
        customer_notes: s.customerNotes,
        items: s.items.map(i => ({ product_id: i.product.id, quantity: i.cantidad })),
      });
      cart.clear();
      checkout.setOrder(order);   // cambia step a 'pago'
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ||
        e?.response?.data?.non_field_errors?.[0] ||
        e?.response?.data?.shipping_address_id?.[0] ||
        'Error al crear la orden. Inténtalo de nuevo.';
      checkout.setError(msg);
    } finally {
      checkout.setLoading(false);
    }
  }
</script>

<svelte:head>
  <title>Checkout — ECOMPARTS</title>
</svelte:head>

<!-- ════════════════════════════════════════════════════════════════════════════
     LAYOUT PRINCIPAL
     ═══════════════════════════════════════════════════════════════════════════ -->
<div class="min-h-screen bg-gray-100">

  <!-- ── Cabecera del checkout ─────────────────────────────────────────────── -->
  <header class="bg-white border-b border-gray-200 sticky top-0 z-30">
    <div class="max-w-6xl mx-auto px-4 py-3 flex flex-col items-center gap-3">

      <!-- Stepper ─────────────────────────────────────────────────────────── -->
      <nav class="flex items-center gap-1 text-sm select-none" aria-label="Pasos del checkout">
        {#each CHECKOUT_STEPS as step, i}
          {@const active   = i === stepIdx}
          {@const done     = i < stepIdx}
          {@const reachable = i <= stepIdx}

          <!-- Step pill -->
          <button
            class="flex items-center gap-1.5 px-3 py-1 rounded-full font-medium transition-colors
              {active   ? 'bg-primary-600 text-white'          : ''}
              {done     ? 'text-primary-600 cursor-pointer'    : ''}
              {!active && !done ? 'text-gray-400 cursor-default' : ''}"
            disabled={!reachable && step !== 'carrito'}
            on:click={() => {
              if (step === 'carrito') { goto('/carrito'); }
              else if (reachable) { checkout.goTo(step); }
            }}
          >
            <span class="flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold
              {active ? 'bg-white text-primary-700' : done ? 'bg-primary-100 text-primary-700' : 'bg-gray-200 text-gray-500'}">
              {done ? '✓' : i + 1}
            </span>
            <span class="hidden sm:inline">{STEP_LABELS[step]}</span>
          </button>

          <!-- Separador -->
          {#if i < CHECKOUT_STEPS.length - 1}
            <span class="text-gray-300">›</span>
          {/if}
        {/each}
      </nav>

    </div>
  </header>

  <!-- ── Cuerpo ────────────────────────────────────────────────────────────── -->
  {#if state.items.length > 0}
  <main class="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">

    <!-- Columna izquierda: contenido del paso actual ─────────────────────── -->
    <section class="lg:col-span-2 space-y-4">

      <!-- ══ PASO: CARRITO ══════════════════════════════════════════════════ -->
      {#if state.step === 'carrito'}
        <div class="bg-white rounded-xl shadow-sm p-6">
          <div class="flex items-center justify-between mb-5">
            <h2 class="text-xl font-bold text-gray-900">Revisión del pedido</h2>
            <a href="/carrito" class="text-sm text-primary-600 hover:underline">
              ← Editar carrito
            </a>
          </div>

          <!-- Items agrupados por proveedor -->
          {#each Object.entries(byProvider) as [providerName, items]}
            <div class="mb-6 last:mb-0">
              <!-- Cabecera proveedor -->
              <div class="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
                <span class="text-xs font-semibold uppercase tracking-wide text-primary-600
                             bg-primary-50 px-2 py-0.5 rounded-full">
                  {providerName}
                </span>
              </div>

              <!-- Lista de items -->
              <div class="space-y-3">
                {#each items as item}
                  <div class="flex gap-4 items-start">
                    <!-- Imagen -->
                    <div class="w-16 h-16 rounded-lg bg-gray-100 flex-shrink-0 overflow-hidden border border-gray-200">
                      {#if item.product.image}
                        <img src={item.product.image} alt={item.product.name}
                             class="w-full h-full object-cover" />
                      {:else}
                        <div class="w-full h-full flex items-center justify-center text-gray-400 text-2xl">📦</div>
                      {/if}
                    </div>

                    <!-- Datos -->
                    <div class="flex-1 min-w-0">
                      <p class="font-semibold text-gray-900 text-sm leading-tight truncate">
                        {item.product.name}
                      </p>
                      <p class="text-xs text-gray-500 mt-0.5">{item.product.reference}</p>
                      <div class="flex items-center gap-2 mt-2">
                        <button
                          class="w-6 h-6 rounded border border-gray-300 text-gray-600
                                 hover:bg-gray-100 flex items-center justify-center text-sm
                                 disabled:opacity-40 disabled:cursor-not-allowed"
                          disabled={item.cantidad <= 1}
                          on:click={() => cart.updateCantidad(item.product.id, item.cantidad - 1)}
                        >−</button>
                        <span class="text-sm font-medium w-6 text-center">{item.cantidad}</span>
                        <button
                          class="w-6 h-6 rounded border border-gray-300 text-gray-600
                                 hover:bg-gray-100 flex items-center justify-center text-sm
                                 disabled:opacity-40 disabled:cursor-not-allowed"
                          disabled={item.cantidad >= item.stockDisponible}
                          on:click={() => cart.updateCantidad(item.product.id, item.cantidad + 1)}
                        >+</button>
                        <button
                          class="ml-2 text-xs text-red-400 hover:text-red-600"
                          on:click={() => cart.removeItem(item.product.id)}
                        >Eliminar</button>
                      </div>
                    </div>

                    <!-- Precio -->
                    <div class="text-right flex-shrink-0">
                      <p class="font-bold text-gray-900 text-sm">{fmt(item.precioTotal)}</p>
                      <p class="text-xs text-gray-400 mt-0.5">{fmt(item.precioUnitario)} c/u</p>
                    </div>
                  </div>
                {/each}
              </div>

              <!-- Subtotal por proveedor -->
              <div class="mt-3 pt-3 border-t border-dashed border-gray-200 flex justify-between text-sm">
                <span class="text-gray-500">Subtotal {providerName}</span>
                <span class="font-semibold text-gray-800">
                  {fmt(items.reduce((s, i) => s + i.precioTotal, 0))}
                </span>
              </div>
            </div>
          {/each}

          <!-- Error global -->
          {#if state.error}
            <div class="mt-4 bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm">
              {state.error}
            </div>
          {/if}

          <!-- Acciones -->
          <div class="mt-6 flex justify-between items-center pt-4 border-t border-gray-100">
            <a href="/carrito"
               class="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1">
              ← Volver al carrito
            </a>
            <button
              class="bg-primary-600 hover:bg-primary-700 text-white font-semibold
                     px-6 py-2.5 rounded-lg transition-colors text-sm"
              on:click={() => checkout.nextStep()}
            >
              Continuar → Perfil
            </button>
          </div>
        </div>

      <!-- ══ PASO: PERFIL ════════════════════════════════════════════════════ -->
      {:else if state.step === 'perfil'}
        <div class="bg-white rounded-xl shadow-sm p-6 space-y-5">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-gray-900">Datos de contacto</h2>
            <span class="text-xs text-gray-400">Paso 2 de 4</span>
          </div>

          <!-- Datos del cliente (solo lectura) -->
          {#if state.customer}
            <div class="bg-gray-50 rounded-lg p-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Correo electrónico</p>
                <p class="font-semibold text-gray-800">{state.customer.email}</p>
              </div>
              <div>
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Usuario</p>
                <p class="font-semibold text-gray-800">{state.customer.username}</p>
              </div>
              <div>
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Nombre / Razón social</p>
                <p class="font-semibold text-gray-800">
                  {state.customer.customer_type === 'company'
                    ? (state.customer.company_name || state.customer.full_name)
                    : state.customer.full_name}
                </p>
              </div>
              <div>
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Documento</p>
                <p class="font-semibold text-gray-800">{state.customer.full_document}</p>
              </div>
              {#if state.customer.phone}
                <div>
                  <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Teléfono</p>
                  <p class="font-semibold text-gray-800">{state.customer.phone}</p>
                </div>
              {/if}
              <div>
                <p class="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Tipo de cliente</p>
                <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full font-medium">
                  {state.customer.customer_type === 'company' ? 'Empresa' : 'Individual'}
                </span>
              </div>
            </div>
            <p class="text-xs text-gray-400">
              ¿Datos incorrectos?
              <a href="/cliente/perfil" target="_blank" class="text-primary-600 hover:underline">Editar perfil</a>
            </p>
          {/if}

          <!-- Términos y condiciones -->
          <div class="space-y-3 pt-2">
            <label class="flex items-start gap-3 cursor-pointer group">
              <input type="checkbox" bind:checked={termsAccepted}
                class="mt-0.5 w-4 h-4 rounded border-gray-300 text-primary-600
                       focus:ring-primary-500 accent-primary-600 flex-shrink-0" />
              <span class="text-sm text-gray-700 group-hover:text-gray-900">
                He leído y acepto los
                <a href="/terminos" target="_blank" class="text-primary-600 hover:underline">términos y condiciones</a>
                y las
                <a href="/privacidad" target="_blank" class="text-primary-600 hover:underline">políticas de privacidad</a>.
                <span class="text-red-500">*</span>
              </span>
            </label>
            <label class="flex items-start gap-3 cursor-pointer group">
              <input type="checkbox" bind:checked={dataAccepted}
                class="mt-0.5 w-4 h-4 rounded border-gray-300 text-primary-600
                       focus:ring-primary-500 accent-primary-600 flex-shrink-0" />
              <span class="text-sm text-gray-700 group-hover:text-gray-900">
                Autorizo el tratamiento de mis datos para fines de prospección y promoción comercial.
              </span>
            </label>
          </div>

          <!-- Error -->
          {#if state.error}
            <div class="bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm">{state.error}</div>
          {/if}

          <!-- Acciones -->
          <div class="flex justify-between items-center pt-4 border-t border-gray-100">
            <button class="text-sm text-gray-500 hover:text-gray-700"
                    on:click={() => checkout.prevStep()}>← Carrito</button>
            <button
              class="bg-primary-600 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed
                     text-white font-semibold px-6 py-2.5 rounded-lg transition-colors text-sm"
              disabled={!termsAccepted}
              on:click={continuarAEntrega}>
              Continuar → Entrega
            </button>
          </div>
        </div>

      <!-- ══ PASO: ENTREGA ═══════════════════════════════════════════════════ -->
      {:else if state.step === 'entrega'}
        <div class="bg-white rounded-xl shadow-sm p-6 space-y-6">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-gray-900">Método de entrega</h2>
            <span class="text-xs text-gray-400">Paso 3 de 4</span>
          </div>

          <!-- Selector de método ─────────────────────────────────────────── -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {#each [
              { value: 'domicilio', label: 'Envío a domicilio', icon: '🏠', desc: 'Recibe en tu dirección' },
              { value: 'agencia',  label: 'Agencia de transporte', icon: '🏢', desc: 'Retira en agencia' },
              { value: 'tienda',   label: 'Recojo en tienda', icon: '🏪', desc: 'Sin costo de envío' },
            ] as opt}
              <button
                class="rounded-xl border-2 p-4 text-left transition-all
                  {state.deliveryMethod === opt.value
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 hover:border-gray-300 bg-white'}"
                on:click={() => checkout.setDeliveryMethod(opt.value as any)}
              >
                <span class="text-2xl">{opt.icon}</span>
                <p class="font-semibold text-gray-900 mt-1 text-sm">{opt.label}</p>
                <p class="text-xs text-gray-500">{opt.desc}</p>
              </button>
            {/each}
          </div>

          <!-- Direcciones (solo si no es tienda) ─────────────────────────── -->
          {#if state.deliveryMethod !== 'tienda'}
            <div>
              <div class="flex items-center justify-between mb-3">
                <h3 class="font-semibold text-gray-800 text-sm">
                  {state.deliveryMethod === 'agencia' ? 'Dirección de agencia' : 'Dirección de envío'}
                </h3>
                <button
                  class="text-xs text-primary-600 hover:underline"
                  on:click={() => { mostrarFormDireccion = !mostrarFormDireccion; }}
                >
                  {mostrarFormDireccion ? '✕ Cancelar' : '+ Nueva dirección'}
                </button>
              </div>

              <!-- Formulario nueva dirección (colapsable) -->
              {#if mostrarFormDireccion}
                <div class="border border-primary-200 rounded-xl p-4 mb-4 bg-primary-50/30 space-y-3">
                  <h4 class="text-sm font-semibold text-gray-700">Nueva dirección</h4>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label for="addr-contact-name" class="block text-xs text-gray-500 mb-1">Nombre de contacto *</label>
                      <input id="addr-contact-name" type="text" bind:value={nuevaDir.contact_name} placeholder="Juan Pérez"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-contact-phone" class="block text-xs text-gray-500 mb-1">Teléfono *</label>
                      <input id="addr-contact-phone" type="tel" bind:value={nuevaDir.contact_phone} placeholder="987654321"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div class="sm:col-span-2">
                      <label for="addr-street" class="block text-xs text-gray-500 mb-1">Calle / Avenida *</label>
                      <input id="addr-street" type="text" bind:value={nuevaDir.street} placeholder="Av. Los Olivos"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-street-number" class="block text-xs text-gray-500 mb-1">Número</label>
                      <input id="addr-street-number" type="text" bind:value={nuevaDir.street_number} placeholder="123"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-apartment" class="block text-xs text-gray-500 mb-1">Dpto / Piso</label>
                      <input id="addr-apartment" type="text" bind:value={nuevaDir.apartment} placeholder="Dpto 4B"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-district" class="block text-xs text-gray-500 mb-1">Distrito *</label>
                      <input id="addr-district" type="text" bind:value={nuevaDir.district} placeholder="Miraflores"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-city" class="block text-xs text-gray-500 mb-1">Ciudad / Provincia *</label>
                      <input id="addr-city" type="text" bind:value={nuevaDir.city} placeholder="Lima"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div>
                      <label for="addr-state" class="block text-xs text-gray-500 mb-1">Departamento *</label>
                      <input id="addr-state" type="text" bind:value={nuevaDir.state} placeholder="Lima"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                    <div class="sm:col-span-2">
                      <label for="addr-reference" class="block text-xs text-gray-500 mb-1">Referencia</label>
                      <input id="addr-reference" type="text" bind:value={nuevaDir.reference}
                        placeholder="Cerca al parque, portón azul…"
                        class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                               focus:outline-none focus:ring-2 focus:ring-primary-400" />
                    </div>
                  </div>
                  <div class="flex justify-end pt-1">
                    <button
                      class="bg-primary-600 hover:bg-primary-700 disabled:opacity-40
                             text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
                      disabled={guardandoDireccion || !nuevaDir.contact_name || !nuevaDir.street || !nuevaDir.district}
                      on:click={agregarNuevaDireccion}
                    >
                      {guardandoDireccion ? 'Guardando…' : 'Guardar dirección'}
                    </button>
                  </div>
                </div>
              {/if}

              <!-- Lista de direcciones guardadas -->
              {#if loadingAddresses}
                <p class="text-sm text-gray-400 py-4 text-center">Cargando direcciones…</p>
              {:else if addresses.length === 0}
                <div class="text-center py-6 bg-gray-50 rounded-xl border border-dashed border-gray-300">
                  <p class="text-sm text-gray-500">No tienes direcciones guardadas.</p>
                  <button class="mt-2 text-sm text-primary-600 hover:underline"
                          on:click={() => { mostrarFormDireccion = true; }}>
                    + Agregar una dirección
                  </button>
                </div>
              {:else}
                <div class="space-y-2">
                  {#each addresses as addr}
                    <button
                      class="w-full text-left rounded-xl border-2 p-4 transition-all
                        {selectedAddressId === addr.id
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300 bg-white'}"
                      on:click={() => seleccionarDireccion(addr)}
                    >
                      <div class="flex items-start justify-between gap-2">
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-sm font-semibold text-gray-800">
                              {addr.contact_name}
                            </span>
                            {#if addr.is_default}
                              <span class="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">Predeterminada</span>
                            {/if}
                            <span class="text-xs text-gray-500">
                              {addr.address_type === 'agency' ? '🏢 Agencia' : addr.address_type === 'business' ? '🏬 Negocio' : '🏠 Domicilio'}
                            </span>
                          </div>
                          <p class="text-xs text-gray-600 mt-0.5">{addr.contact_phone}</p>
                          <p class="text-sm text-gray-700 mt-1">{addr.full_address}</p>
                          {#if addr.reference}
                            <p class="text-xs text-gray-400 mt-0.5">Ref: {addr.reference}</p>
                          {/if}
                        </div>
                        <div class="flex-shrink-0 mt-0.5">
                          {#if selectedAddressId === addr.id}
                            <span class="w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs">✓</span>
                          {:else}
                            <span class="w-5 h-5 rounded-full border-2 border-gray-300"></span>
                          {/if}
                        </div>
                      </div>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {:else}
            <!-- Recojo en tienda -->
            <div class="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-800">
              🏪 <strong>Recojo en tienda:</strong> Un asesor te contactará para coordinar la entrega.
            </div>
          {/if}

          <!-- Notas del pedido -->
          <div>
            <label for="order-notes" class="block text-sm font-medium text-gray-700 mb-1">Notas del pedido (opcional)</label>
            <textarea
              id="order-notes"
              rows="2"
              placeholder="Instrucciones especiales, horario de recepción, etc."
              value={state.customerNotes}
              on:input={(e) => checkout.setNotes((e.target as HTMLTextAreaElement).value)}
              class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-primary-400 resize-none"
            ></textarea>
          </div>

          <!-- Error -->
          {#if state.error}
            <div class="bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm">{state.error}</div>
          {/if}

          <!-- Acciones -->
          <div class="flex justify-between items-center pt-4 border-t border-gray-100">
            <button class="text-sm text-gray-500 hover:text-gray-700"
                    on:click={() => checkout.prevStep()}>← Perfil</button>
            <button
              class="bg-primary-600 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed
                     text-white font-semibold px-6 py-2.5 rounded-lg transition-colors text-sm
                     flex items-center gap-2"
              disabled={state.loading || (state.deliveryMethod !== 'tienda' && !selectedAddressId)}
              on:click={crearOrden}
            >
              {#if state.loading}
                <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                </svg>
                Creando orden…
              {:else}
                Confirmar y continuar al pago →
              {/if}
            </button>
          </div>
        </div>

      <!-- ══ PASO: PAGO ═══════════════════════════════════════════════════════ -->
      {:else if state.step === 'pago'}
        <div class="space-y-4">

          <!-- Cabecera -->
          <div class="bg-white rounded-xl shadow-sm p-5">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-xl font-bold text-gray-900">Pago y Confirmación</h2>
                {#if state.order}
                  <p class="text-xs text-gray-500 mt-0.5">Orden <span class="font-mono font-semibold">{state.order.order_number}</span></p>
                {/if}
              </div>
              <span class="text-xs text-gray-400">Paso 4 de 4</span>
            </div>
            {#if (state.order?.sub_orders.length ?? 0) > 1}
              <div class="mt-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
                ⚠️ Tu pedido tiene <strong>{state.order?.sub_orders.length} proveedores</strong>.
                Debes realizar un pago <strong>separado</strong> a cada uno y subir su comprobante.
              </div>
            {/if}
          </div>

          <!-- Banner de reserva con countdown (solo si hay pagos realmente pendientes o la reserva expiró) -->
          {#if state.order?.payment_deadline && (hayPagosPendientes || deadlineExpired)}
            <div class="rounded-xl border px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3
              {deadlineExpired
                ? 'bg-red-50 border-red-200'
                : 'bg-amber-50 border-amber-200'}"
            >
              <div class="flex items-center gap-3">
                <span class="text-2xl">{deadlineExpired ? '⏰' : '⏱️'}</span>
                <div>
                  {#if deadlineExpired}
                    <p class="text-sm font-semibold text-red-700">La reserva de stock ha expirado.</p>
                    <p class="text-xs text-red-600">Los artículos pendientes de pago fueron liberados.</p>
                  {:else}
                    <p class="text-sm font-semibold text-amber-800">
                      Por favor realiza el pago pendiente.
                    </p>
                    <p class="text-xs text-amber-700">
                      La reserva de stock expira en
                      <span class="font-mono font-bold">{countdown || '…'}</span>
                    </p>
                  {/if}
                </div>
              </div>
              <!-- Botón Pagar más tarde -->
              {#if !deadlineExpired && !todosSubidos}
                <a
                  href="/cliente/historial-compras"
                  class="flex-shrink-0 text-sm text-amber-700 border border-amber-300
                         bg-white hover:bg-amber-50 font-medium px-4 py-2 rounded-lg transition-colors"
                >
                  Pagar más tarde →
                </a>
              {/if}
            </div>
          {/if}

          <!-- Card por cada sub-orden -->
          {#if state.order}
            {#each state.order.sub_orders as sub (sub.id)}
              {@const form = proofForms[sub.id]}
              {@const pay  = sub.provider_payment_info}

              <div class="bg-white rounded-xl shadow-sm overflow-hidden
                {form?.uploaded ? 'ring-2 ring-green-400' : ''}">

                <!-- Header sub-orden -->
                <div class="flex items-center justify-between px-5 py-4
                            border-b border-gray-100 bg-gray-50">
                  <div>
                    <p class="font-semibold text-gray-900">{sub.provider_name}</p>
                    <p class="text-xs text-gray-500 font-mono">{sub.sub_order_number}</p>
                  </div>
                  <div class="text-right">
                    <p class="font-bold text-gray-900">S/ {parseFloat(sub.total).toFixed(2)}</p>
                    {#if form?.uploaded}
                      <span class="text-xs text-green-600 font-semibold">✓ Comprobante enviado</span>
                    {:else}
                      <span class="text-xs text-amber-600">Pendiente de pago</span>
                    {/if}
                  </div>
                </div>

                <div class="p-5 space-y-5">

                  <!-- Items de esta sub-orden -->
                  <div class="space-y-2">
                    {#each sub.items as item}
                      <div class="flex justify-between text-sm text-gray-700">
                        <span>{item.quantity}× {item.product_name}</span>
                        <span class="font-medium">S/ {parseFloat(item.subtotal).toFixed(2)}</span>
                      </div>
                    {/each}

                    <!-- Desglose financiero: subtotal, descuento, IGV, total -->
                    <div class="mt-3 pt-3 border-t border-dashed border-gray-200 space-y-1.5 text-xs">
                      <div class="flex justify-between text-gray-500">
                        <span>Subtotal</span>
                        <span>S/ {parseFloat(sub.subtotal).toFixed(2)}</span>
                      </div>

                      {#if parseFloat(sub.discount) > 0}
                        <div class="flex justify-between text-green-600 font-medium">
                          <span>Descuento cliente ({sub.discount_percent}%)</span>
                          <span>− S/ {parseFloat(sub.discount).toFixed(2)}</span>
                        </div>
                      {/if}

                      {#if parseFloat(sub.igv_amount) > 0}
                        <div class="flex justify-between text-gray-400">
                          <span>IGV ({sub.igv_rate}%)</span>
                          <span>S/ {parseFloat(sub.igv_amount).toFixed(2)}</span>
                        </div>
                      {/if}

                      <div class="flex justify-between font-semibold text-gray-800 pt-1 border-t border-gray-200">
                        <span>Total a pagar</span>
                        <span>S/ {parseFloat(sub.total).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Datos de pago del proveedor -->
                  <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-3">
                    <p class="text-sm font-semibold text-blue-900">💳 Datos de pago — {sub.provider_name}</p>

                    {#if pay.banco_nombre || pay.banco_cuenta}
                      <div class="bg-white rounded-lg p-3 border border-blue-100 space-y-1.5">
                        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">🏦 Transferencia Bancaria</p>
                        {#if pay.banco_nombre}
                          <div class="flex justify-between text-sm">
                            <span class="text-gray-500">Banco</span>
                            <span class="font-semibold text-gray-800">{pay.banco_nombre}</span>
                          </div>
                        {/if}
                        {#if pay.banco_cuenta}
                          <div class="flex justify-between text-sm">
                            <span class="text-gray-500">N° Cuenta</span>
                            <span class="font-mono font-semibold text-gray-800 select-all">{pay.banco_cuenta}</span>
                          </div>
                        {/if}
                        {#if pay.banco_cci}
                          <div class="flex justify-between text-sm">
                            <span class="text-gray-500">CCI</span>
                            <span class="font-mono font-semibold text-gray-800 select-all">{pay.banco_cci}</span>
                          </div>
                        {/if}
                      </div>
                    {/if}

                    {#if pay.yape_numero || pay.plin_numero}
                      <div class="flex gap-3 flex-wrap">
                        {#if pay.yape_numero}
                          <div class="flex-1 min-w-[120px] bg-white rounded-lg p-3 border border-blue-100 text-center">
                            <p class="text-xs font-semibold text-purple-600 mb-1">💜 Yape</p>
                            <p class="font-mono font-bold text-gray-800 select-all">{pay.yape_numero}</p>
                          </div>
                        {/if}
                        {#if pay.plin_numero}
                          <div class="flex-1 min-w-[120px] bg-white rounded-lg p-3 border border-blue-100 text-center">
                            <p class="text-xs font-semibold text-green-600 mb-1">💚 Plin</p>
                            <p class="font-mono font-bold text-gray-800 select-all">{pay.plin_numero}</p>
                          </div>
                        {/if}
                      </div>
                    {/if}

                    {#if !pay.banco_nombre && !pay.banco_cuenta && !pay.yape_numero && !pay.plin_numero}
                      <p class="text-sm text-gray-500 italic">El proveedor coordinará el método de pago contigo.</p>
                    {/if}
                  </div>

                  <!-- SubOrder expirada ──────────────────────────────────── -->
                  {#if sub.expired || sub.status === 'cancelado'}
                    <div class="bg-gray-50 border border-gray-200 rounded-xl p-4 flex items-center gap-3">
                      <span class="text-xl">⏰</span>
                      <div>
                        <p class="text-sm font-semibold text-gray-700">La reserva de este artículo ha expirado y fue liberado.</p>
                        <p class="text-xs text-gray-500 mt-0.5">
                          Puedes volver a agregarlo al
                          <a href="/carrito" class="text-primary-600 hover:underline">carrito</a>
                          si aún está disponible.
                        </p>
                      </div>
                    </div>

                  <!-- Comprobante ya enviado ──────────────────────────────── -->
                  {:else if form?.uploaded}
                    <div class="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-3">
                      <span class="text-2xl">✅</span>
                      <div>
                        <p class="text-sm font-semibold text-green-800">Comprobante enviado correctamente</p>
                        <p class="text-xs text-green-600">
                          {PAYMENT_METHOD_LABELS[form.payment_method]} · S/ {parseFloat(form.amount).toFixed(2)}
                          {form.operation_number ? ` · Op. ${form.operation_number}` : ''}
                        </p>
                        <p class="text-xs text-green-500 mt-0.5">El proveedor verificará tu pago y confirmará la orden.</p>
                      </div>
                    </div>

                  <!-- Formulario comprobante -->
                  {:else if form}
                    <div class="space-y-4 pt-1">
                      <p class="text-sm font-semibold text-gray-800">📎 Sube tu comprobante de pago</p>

                      <!-- Método de pago -->
                      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {#each [
                          { value: 'transferencia',          label: 'Transferencia', icon: '🏦' },
                          { value: 'yape',                   label: 'Yape',          icon: '💜' },
                          { value: 'plin',                   label: 'Plin',          icon: '💚' },
                          { value: 'efectivo_contraentrega', label: 'Contraentrega', icon: '🚚' },
                          { value: 'efectivo_tienda',        label: 'En tienda',     icon: '🏪' },
                        ] as m}
                          <button
                            class="rounded-lg border-2 py-2 px-3 text-xs font-medium text-center transition-all
                              {form.payment_method === m.value
                                ? 'border-primary-500 bg-primary-50 text-primary-700'
                                : 'border-gray-200 hover:border-gray-300 text-gray-600'}"
                            on:click={() => { proofForms[sub.id] = { ...form, payment_method: m.value as PaymentMethod }; }}
                          >{m.icon} {m.label}</button>
                        {/each}
                      </div>

                      <!-- Monto y número de operación -->
                      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label for="amount-{sub.id}" class="block text-xs text-gray-500 mb-1">Monto pagado (S/) *</label>
                          <input
                            id="amount-{sub.id}"
                            type="number"
                            step="0.01"
                            min="0.01"
                            bind:value={proofForms[sub.id].amount}
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                                   focus:outline-none focus:ring-2 focus:ring-primary-400" />
                        </div>
                        <div>
                          <label for="opnum-{sub.id}" class="block text-xs text-gray-500 mb-1">N° de operación</label>
                          <input
                            id="opnum-{sub.id}"
                            type="text"
                            bind:value={proofForms[sub.id].operation_number}
                            placeholder="Ej: 123456789"
                            class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                                   focus:outline-none focus:ring-2 focus:ring-primary-400" />
                        </div>
                      </div>

                      <!-- Adjuntar archivo -->
                      <div>
                        <label for="file-{sub.id}" class="block text-xs text-gray-500 mb-1">
                          Captura / voucher * (JPG, PNG, PDF)
                        </label>
                        <label for="file-{sub.id}"
                          class="flex flex-col items-center justify-center w-full border-2 border-dashed
                                 rounded-xl cursor-pointer py-5 transition-colors
                                 {form.file
                                   ? 'border-green-400 bg-green-50'
                                   : 'border-gray-300 hover:border-primary-400 hover:bg-primary-50/30'}">
                          {#if form.file}
                            <span class="text-2xl">📄</span>
                            <span class="text-sm font-medium text-green-700 mt-1">{form.file.name}</span>
                            <span class="text-xs text-gray-400 mt-0.5">{(form.file.size / 1024).toFixed(1)} KB</span>
                          {:else}
                            <span class="text-2xl text-gray-300">📎</span>
                            <span class="text-sm text-gray-500 mt-1">Haz clic para adjuntar</span>
                            <span class="text-xs text-gray-400">o arrastra aquí</span>
                          {/if}
                        </label>
                        <input
                          id="file-{sub.id}"
                          type="file"
                          accept="image/*,application/pdf"
                          class="hidden"
                          on:change={(e) => onFileChange(sub.id, e)}
                        />
                      </div>

                      <!-- Error -->
                      {#if form.error}
                        <div class="bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm">{form.error}</div>
                      {/if}

                      <!-- Botón subir -->
                      <button
                        class="w-full bg-primary-600 hover:bg-primary-700 disabled:opacity-40
                               disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-lg
                               transition-colors text-sm flex items-center justify-center gap-2"
                        disabled={form.uploading || !form.file || !form.amount}
                        on:click={() => subirComprobante(sub)}
                      >
                        {#if form.uploading}
                          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                          </svg>
                          Subiendo comprobante…
                        {:else}
                          ↑ Enviar comprobante a {sub.provider_name}
                        {/if}
                      </button>
                    </div>
                  {/if}

                </div>
              </div>
            {/each}
          {/if}

          <!-- Panel de progreso y confirmación final -->
          {#if !todosSubidos && activeSubs.length > 0}
            <div class="bg-white rounded-xl shadow-sm p-5">
              <p class="text-sm text-gray-500">
                {activeSubs.filter(s => proofForms[s.id]?.uploaded).length}
                de {activeSubs.length} comprobante(s) enviado(s). Sube todos para confirmar tu pedido.
              </p>
            </div>
          {:else}
            <!-- Confirmación inline: todos los comprobantes enviados -->
            <div class="bg-white rounded-xl shadow-sm p-8 text-center space-y-4">
              <div class="text-6xl">&#x2705;</div>
              <h2 class="text-2xl font-bold text-gray-900">¡Pedido confirmado!</h2>
              <p class="text-gray-600 text-sm max-w-md mx-auto">
                Tus comprobantes han sido enviados correctamente. Los proveedores verificarán los pagos
                y actualizarán el estado de tu pedido.
              </p>
              {#if state.order}
                <div class="inline-block bg-gray-50 border border-gray-200 rounded-xl px-6 py-3 text-sm">
                  <p class="text-gray-500">Número de orden</p>
                  <p class="font-mono font-bold text-gray-900 text-lg">{state.order.order_number}</p>
                </div>
              {/if}
              <div class="pt-2 flex flex-col sm:flex-row gap-3 justify-center">
                <a
                  href="cliente/historial-compras"
                  class="bg-primary-600 hover:bg-primary-700 text-white font-semibold
                         px-6 py-3 rounded-lg transition-colors text-sm"
                >
                  Ver mis pedidos →
                </a>
                <a
                  href="/"
                  class="bg-white border border-gray-300 hover:border-gray-400 text-gray-700 font-semibold
                         px-6 py-3 rounded-lg transition-colors text-sm"
                >
                  Seguir comprando
                </a>
              </div>
            </div>
          {/if}

        </div>

      {/if}

    </section>

    <!-- Columna derecha: Resumen de compra (sticky) ──────────────────────── -->
    <aside class="lg:col-span-1">
      <div class="bg-white rounded-xl shadow-sm p-5 sticky top-24 space-y-4">

        <h3 class="font-bold text-gray-900 text-base border-b border-gray-100 pb-3">
          Resumen de compra
        </h3>

        <!-- Productos con desglose por proveedor -->
        <div class="space-y-2 text-sm">
          {#each Object.entries(byProvider) as [provName, items]}
            <div>
              <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{provName}</p>
              {#each items as item}
                <div class="flex justify-between text-gray-700 pl-2">
                  <span class="truncate pr-2 max-w-[150px]">
                    {item.cantidad}× {item.product.name}
                  </span>
                  <span class="flex-shrink-0">{fmt(item.precioTotal)}</span>
                </div>
              {/each}
            </div>
          {/each}
        </div>

        <!-- Separador -->
        <div class="border-t border-dashed border-gray-200 pt-3 space-y-2 text-sm">
          {#if state.order}
            <!-- Desglose real una vez creada la orden -->
            <div class="flex justify-between text-gray-600">
              <span>Subtotal</span>
              <span>{fmt(parseFloat(state.order.subtotal))}</span>
            </div>
            {#if parseFloat(state.order.discount) > 0}
              <div class="flex justify-between text-green-600 font-medium">
                <span>Descuento</span>
                <span>− {fmt(parseFloat(state.order.discount))}</span>
              </div>
            {/if}
            {#if parseFloat(state.order.tax) > 0}
              <div class="flex justify-between text-gray-500">
                <span>IGV (18%)</span>
                <span>{fmt(parseFloat(state.order.tax))}</span>
              </div>
            {/if}
          {:else}
            <div class="flex justify-between text-gray-600">
              <span>Productos ({state.items.length})</span>
              <span>{fmt(subtotal)}</span>
            </div>
          {/if}
          {#if provCount > 1}
            <p class="text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">
              ⚠️ Pedido con {provCount} proveedores — se generará una sub-orden por cada uno.
            </p>
          {/if}
        </div>

        <!-- Total -->
        <div class="border-t border-gray-200 pt-3 flex justify-between items-center">
          <span class="font-bold text-gray-900">Total</span>
          <span class="font-bold text-gray-900 text-lg">
            {state.order ? fmt(parseFloat(state.order.total)) : fmt(subtotal)}
          </span>
        </div>

        {#if !state.order}
          <p class="text-xs text-gray-400 italic">
            *El descuento por historial de compras se aplicará al confirmar el pedido.
          </p>
        {/if}

        <!-- Indicadores de pasos -->
        <div class="border-t border-gray-100 pt-4 space-y-2">
          {#each CHECKOUT_STEPS as step, i}
            {@const done    = i < stepIdx}
            {@const active  = i === stepIdx}
            <div class="flex items-center gap-3 text-sm
              {active ? 'text-gray-900' : done ? 'text-primary-600' : 'text-gray-400'}">
              <span class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
                {active  ? 'bg-primary-600 text-white'    : ''}
                {done    ? 'bg-primary-100 text-primary-700' : ''}
                {!active && !done ? 'bg-gray-100 text-gray-400' : ''}">
                {done ? '✓' : i + 1}
              </span>
              <div class="leading-tight">
                <p class="font-medium">{STEP_LABELS[step]}</p>
                {#if active && step === 'carrito'}
                  <p class="text-xs text-gray-400">{state.items.length} producto(s)</p>
                {:else if active && step === 'perfil' && state.customer}
                  <p class="text-xs text-gray-400">{state.customer.email}</p>
                {:else if active && step === 'entrega'}
                  <p class="text-xs text-gray-400">
                    {state.shippingAddress ? state.shippingAddress.full_address : 'Por definir'}
                  </p>
                {:else if !done && !active}
                  <p class="text-xs text-gray-400">Por definir</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>

      </div>
    </aside>

  </main>
  {:else}
    <!-- Estado vacío / cargando -->
    <div class="flex items-center justify-center min-h-[60vh]">
      <div class="text-gray-400 text-center">
        <p class="text-4xl mb-3">🛒</p>
        <p class="text-lg font-medium">Cargando tu pedido…</p>
      </div>
    </div>
  {/if}

</div>
