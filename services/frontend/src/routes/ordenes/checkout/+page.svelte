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

<!-- LAYOUT PRINCIPAL -->
<div class="min-h-screen bg-iron-950">

  <!-- Cabecera sticky con stepper -->
  <header class="bg-iron-900 border-b border-steel-600/30 sticky top-0 z-30">
    <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-center">
      <nav class="flex items-center gap-1 select-none" aria-label="Pasos del checkout">
        {#each CHECKOUT_STEPS as step, i}
          {@const active    = i === stepIdx}
          {@const done      = i < stepIdx}
          {@const reachable = i <= stepIdx}
          <button
            class="flex items-center gap-2 px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest transition-colors
              {active   ? 'text-bone border border-steel-600/50 bg-iron-800'   : ''}
              {done     ? 'text-rust-500 cursor-pointer'                        : ''}
              {!active && !done ? 'text-steel-600 cursor-default'               : ''}"
            disabled={!reachable && step !== 'carrito'}
            on:click={() => {
              if (step === 'carrito') { goto('/carrito'); }
              else if (reachable) { checkout.goTo(step); }
            }}
          >
            <span class="font-display text-sm leading-none
              {active ? 'text-rust-600' : done ? 'text-rust-700' : 'text-steel-700'}">
              {done ? '✓' : i + 1}
            </span>
            <span class="hidden sm:inline">{STEP_LABELS[step].toUpperCase()}</span>
          </button>
          {#if i < CHECKOUT_STEPS.length - 1}
            <span class="text-steel-700 font-mono text-xs">›</span>
          {/if}
        {/each}
      </nav>
    </div>
  </header>

  {#if state.items.length > 0}
  <main class="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">

    <!-- Columna izquierda: paso actual -->
    <section class="lg:col-span-2 space-y-4">

      <!-- PASO: CARRITO -->
      {#if state.step === 'carrito'}
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between">
            <div>
              <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 01</p>
              <h2 class="font-display text-2xl text-bone uppercase leading-none">REVISIÓN DEL PEDIDO</h2>
            </div>
            <a href="/carrito" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">← EDITAR</a>
          </div>

          <div class="divide-y divide-steel-600/15">
            {#each Object.entries(byProvider) as [providerName, items]}
              <div class="p-5">
                <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-3">{providerName}</p>
                <div class="space-y-4">
                  {#each items as item}
                    <div class="flex gap-4 items-start">
                      <div class="w-14 h-14 bg-iron-800 border border-steel-600/40 flex-shrink-0 overflow-hidden">
                        {#if item.product.image_url}
                          <img src={item.product.image_url} alt={item.product.name} class="w-full h-full object-cover" />
                        {:else}
                          <div class="w-full h-full flex items-center justify-center text-steel-600 text-xl">▪</div>
                        {/if}
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="font-mono text-xs text-bone truncate">{item.product.name}</p>
                        <p class="font-mono text-[10px] text-steel-600">{item.product.reference ?? ''}</p>
                        <div class="flex items-center gap-2 mt-2">
                          <button class="w-6 h-6 border border-steel-600/40 text-steel-400 hover:text-bone hover:border-steel-400 flex items-center justify-center font-mono text-sm transition-colors disabled:opacity-40"
                            disabled={item.cantidad <= 1}
                            on:click={() => cart.updateCantidad(item.product.id, item.cantidad - 1)}>−</button>
                          <span class="font-mono text-xs text-bone w-5 text-center">{item.cantidad}</span>
                          <button class="w-6 h-6 border border-steel-600/40 text-steel-400 hover:text-bone hover:border-steel-400 flex items-center justify-center font-mono text-sm transition-colors"
                            on:click={() => cart.updateCantidad(item.product.id, item.cantidad + 1)}>+</button>
                          <button class="font-mono text-[9px] text-rust-600 hover:text-rust-400 uppercase tracking-widest ml-2 transition-colors"
                            on:click={() => cart.removeItem(item.product.id)}>ELIMINAR</button>
                        </div>
                      </div>
                      <div class="text-right flex-shrink-0">
                        <p class="font-mono text-xs text-bone">{fmt(item.precioTotal)}</p>
                        <p class="font-mono text-[10px] text-steel-600">{fmt(item.precioUnitario)} c/u</p>
                      </div>
                    </div>
                  {/each}
                </div>
                <div class="mt-3 pt-3 border-t border-steel-600/20 flex justify-between">
                  <span class="font-mono text-[10px] text-steel-600 uppercase">SUBTOTAL {providerName}</span>
                  <span class="font-mono text-xs text-bone">{fmt(items.reduce((s, i) => s + i.precioTotal, 0))}</span>
                </div>
              </div>
            {/each}
          </div>

          {#if state.error}
            <div class="mx-5 mb-4 border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
              <p class="font-mono text-xs text-rust-400">{state.error}</p>
            </div>
          {/if}

          <div class="border-t border-steel-600/25 px-5 py-4 flex justify-between items-center">
            <a href="/carrito" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">← CARRITO</a>
            <button class="btn-rust" on:click={() => checkout.nextStep()}>CONTINUAR → PERFIL</button>
          </div>
        </div>

      <!-- PASO: PERFIL -->
      {:else if state.step === 'perfil'}
        <div class="bg-iron-900 border border-steel-600/25"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 02</p>
            <h2 class="font-display text-2xl text-bone uppercase leading-none">DATOS DE CONTACTO</h2>
          </div>

          {#if state.customer}
            <div class="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {#each [
                { label: 'CORREO', value: state.customer.email },
                { label: 'USUARIO', value: state.customer.username },
                { label: 'NOMBRE / RAZÓN SOCIAL', value: state.customer.customer_type === 'company'
                    ? (state.customer.company_name || state.customer.full_name)
                    : state.customer.full_name },
                { label: 'DOCUMENTO', value: state.customer.full_document },
                ...(state.customer.phone ? [{ label: 'TELÉFONO', value: state.customer.phone }] : []),
                { label: 'TIPO', value: state.customer.customer_type === 'company' ? 'EMPRESA' : 'INDIVIDUAL' },
              ] as row}
                <div class="bg-iron-800/50 border border-steel-600/20 px-4 py-3">
                  <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{row.label}</p>
                  <p class="font-mono text-xs text-bone">{row.value}</p>
                </div>
              {/each}
            </div>
            <div class="px-5 pb-2">
              <p class="font-mono text-[10px] text-steel-600">
                ¿DATOS INCORRECTOS?
                <a href="/cliente/perfil" target="_blank" class="text-rust-500 hover:text-rust-400 transition-colors">EDITAR PERFIL →</a>
              </p>
            </div>
          {/if}

          <div class="border-t border-steel-600/20 px-5 py-4 space-y-3">
            {#each [
              { key: 'terms', label: 'HE LEÍDO Y ACEPTO LOS TÉRMINOS Y CONDICIONES Y LAS POLÍTICAS DE PRIVACIDAD *', bind: 'termsAccepted' },
              { key: 'data',  label: 'AUTORIZO EL TRATAMIENTO DE MIS DATOS PARA FINES DE PROSPECCIÓN COMERCIAL.', bind: 'dataAccepted' },
            ] as opt}
              <label class="flex items-start gap-3 cursor-pointer group">
                <div class="relative w-4 h-4 border flex items-center justify-center flex-shrink-0 mt-0.5
                  {opt.key === 'terms'
                    ? (termsAccepted ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50')
                    : (dataAccepted  ? 'border-rust-600 bg-rust-600/20' : 'border-steel-600/50')}">
                  {#if opt.key === 'terms'}
                    <input type="checkbox" bind:checked={termsAccepted} class="sr-only" />
                    {#if termsAccepted}
                      <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    {/if}
                  {:else}
                    <input type="checkbox" bind:checked={dataAccepted} class="sr-only" />
                    {#if dataAccepted}
                      <svg class="w-2.5 h-2.5 text-rust-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                    {/if}
                  {/if}
                </div>
                <span class="font-mono text-[10px] text-steel-500 uppercase tracking-widest group-hover:text-bone transition-colors leading-relaxed">
                  {opt.label}
                </span>
              </label>
            {/each}
          </div>

          {#if state.error}
            <div class="mx-5 mb-3 border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
              <p class="font-mono text-xs text-rust-400">{state.error}</p>
            </div>
          {/if}

          <div class="border-t border-steel-600/25 px-5 py-4 flex justify-between items-center">
            <button class="btn-ghost font-mono text-[10px] uppercase tracking-widest" on:click={() => checkout.prevStep()}>← CARRITO</button>
            <button class="btn-rust disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={!termsAccepted} on:click={continuarAEntrega}>
              CONTINUAR → ENTREGA
            </button>
          </div>
        </div>

      <!-- PASO: ENTREGA -->
      {:else if state.step === 'entrega'}
        <div class="bg-iron-900 border border-steel-600/25 space-y-0"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 03</p>
            <h2 class="font-display text-2xl text-bone uppercase leading-none">MÉTODO DE ENTREGA</h2>
          </div>

          <!-- Selector método -->
          <div class="p-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
            {#each [
              { value: 'domicilio', label: 'ENVÍO A DOMICILIO',      desc: 'Recibe en tu dirección' },
              { value: 'agencia',  label: 'AGENCIA DE TRANSPORTE',   desc: 'Retira en agencia' },
              { value: 'tienda',   label: 'RECOJO EN TIENDA',        desc: 'Sin costo de envío' },
            ] as opt}
              <button
                class="border p-4 text-left transition-colors
                  {state.deliveryMethod === opt.value
                    ? 'border-rust-600 bg-rust-600/10'
                    : 'border-steel-600/40 hover:border-steel-400'}"
                on:click={() => checkout.setDeliveryMethod(opt.value as any)}
              >
                <p class="font-mono text-xs text-bone uppercase">{opt.label}</p>
                <p class="font-mono text-[10px] text-steel-500 mt-1">{opt.desc}</p>
              </button>
            {/each}
          </div>

          <!-- Direcciones -->
          {#if state.deliveryMethod !== 'tienda'}
            <div class="border-t border-steel-600/20 px-5 py-4">
              <div class="flex items-center justify-between mb-4">
                <p class="font-mono text-[10px] text-steel-400 uppercase tracking-widest">
                  {state.deliveryMethod === 'agencia' ? '// DIRECCIÓN DE AGENCIA' : '// DIRECCIÓN DE ENVÍO'}
                </p>
                <button class="btn-ghost font-mono text-[10px] uppercase tracking-widest"
                  on:click={() => { mostrarFormDireccion = !mostrarFormDireccion; }}>
                  {mostrarFormDireccion ? '✕ CANCELAR' : '+ NUEVA DIRECCIÓN'}
                </button>
              </div>

              {#if mostrarFormDireccion}
                <div class="bg-iron-800/50 border border-steel-600/25 p-4 mb-4 space-y-3">
                  <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// NUEVA DIRECCIÓN</p>
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {#each [
                      { id: 'addr-contact-name',   label: 'NOMBRE DE CONTACTO *', bind: 'contact_name',   ph: 'Juan Pérez',          type: 'text', span: false },
                      { id: 'addr-contact-phone',  label: 'TELÉFONO *',           bind: 'contact_phone',  ph: '987654321',            type: 'tel',  span: false },
                      { id: 'addr-street',         label: 'CALLE / AVENIDA *',    bind: 'street',         ph: 'Av. Los Olivos',       type: 'text', span: true  },
                      { id: 'addr-street-number',  label: 'NÚMERO',               bind: 'street_number',  ph: '123',                  type: 'text', span: false },
                      { id: 'addr-apartment',      label: 'DPTO / PISO',          bind: 'apartment',      ph: 'Dpto 4B',              type: 'text', span: false },
                      { id: 'addr-district',       label: 'DISTRITO *',           bind: 'district',       ph: 'Miraflores',           type: 'text', span: false },
                      { id: 'addr-city',           label: 'CIUDAD / PROVINCIA *', bind: 'city',           ph: 'Lima',                 type: 'text', span: false },
                      { id: 'addr-state',          label: 'DEPARTAMENTO *',       bind: 'state',          ph: 'Lima',                 type: 'text', span: false },
                      { id: 'addr-reference',      label: 'REFERENCIA',           bind: 'reference',      ph: 'Cerca al parque…',     type: 'text', span: true  },
                    ] as f}
                      <div class="{f.span ? 'sm:col-span-2' : ''}">
                        <label for={f.id} class="block font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">// {f.label}</label>
                        <input id={f.id} type={f.type} bind:value={nuevaDir[f.bind as keyof typeof nuevaDir]}
                          placeholder={f.ph} class="input-industrial text-xs" />
                      </div>
                    {/each}
                  </div>
                  <div class="flex justify-end">
                    <button class="btn-rust disabled:opacity-40"
                      disabled={guardandoDireccion || !nuevaDir.contact_name || !nuevaDir.street || !nuevaDir.district}
                      on:click={agregarNuevaDireccion}>
                      {guardandoDireccion ? 'GUARDANDO...' : 'GUARDAR DIRECCIÓN'}
                    </button>
                  </div>
                </div>
              {/if}

              {#if loadingAddresses}
                <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest text-center py-4 animate-pulse">CARGANDO DIRECCIONES...</p>
              {:else if addresses.length === 0}
                <div class="border border-dashed border-steel-600/30 p-6 text-center">
                  <p class="font-mono text-xs text-steel-600 uppercase">SIN DIRECCIONES GUARDADAS</p>
                  <button class="font-mono text-[10px] text-rust-500 hover:text-rust-400 uppercase tracking-widest mt-2 transition-colors"
                    on:click={() => { mostrarFormDireccion = true; }}>+ AGREGAR DIRECCIÓN</button>
                </div>
              {:else}
                <div class="space-y-2">
                  {#each addresses as addr}
                    <button class="w-full text-left border p-4 transition-colors
                        {selectedAddressId === addr.id ? 'border-rust-600 bg-rust-600/10' : 'border-steel-600/40 hover:border-steel-400'}"
                      on:click={() => seleccionarDireccion(addr)}>
                      <div class="flex items-start justify-between gap-2">
                        <div class="flex-1 min-w-0">
                          <div class="flex items-center gap-2 flex-wrap mb-1">
                            <span class="font-mono text-xs text-bone">{addr.contact_name}</span>
                            {#if addr.is_default}
                              <span class="font-mono text-[9px] border border-steel-600/40 text-steel-400 px-1.5 py-0.5">PREDETERMINADA</span>
                            {/if}
                            <span class="font-mono text-[9px] text-steel-600 uppercase">
                              {addr.address_type === 'agency' ? 'AGENCIA' : addr.address_type === 'business' ? 'NEGOCIO' : 'DOMICILIO'}
                            </span>
                          </div>
                          <p class="font-mono text-[10px] text-steel-500">{addr.contact_phone}</p>
                          <p class="font-mono text-[10px] text-steel-400 mt-0.5">{addr.full_address}</p>
                          {#if addr.reference}
                            <p class="font-mono text-[10px] text-steel-600 mt-0.5">REF: {addr.reference}</p>
                          {/if}
                        </div>
                        <div class="flex-shrink-0 mt-0.5">
                          {#if selectedAddressId === addr.id}
                            <span class="w-5 h-5 bg-rust-600/20 border border-rust-600 flex items-center justify-center text-rust-500 text-xs">✓</span>
                          {:else}
                            <span class="w-5 h-5 border border-steel-600/40"></span>
                          {/if}
                        </div>
                      </div>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {:else}
            <div class="border-t border-steel-600/20 px-5 py-4">
              <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-center gap-3">
                <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0"></span>
                <p class="font-mono text-xs text-green-400 uppercase tracking-widest">RECOJO EN TIENDA — UN ASESOR TE CONTACTARÁ.</p>
              </div>
            </div>
          {/if}

          <!-- Notas -->
          <div class="border-t border-steel-600/20 px-5 py-4">
            <label for="order-notes" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// NOTAS DEL PEDIDO (OPCIONAL)</label>
            <textarea id="order-notes" rows="2"
              placeholder="Instrucciones especiales, horario de recepción, etc."
              value={state.customerNotes}
              on:input={(e) => checkout.setNotes((e.target as HTMLTextAreaElement).value)}
              class="input-industrial resize-none text-xs w-full"></textarea>
          </div>

          {#if state.error}
            <div class="mx-5 mb-3 border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
              <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
              <p class="font-mono text-xs text-rust-400">{state.error}</p>
            </div>
          {/if}

          <div class="border-t border-steel-600/25 px-5 py-4 flex justify-between items-center">
            <button class="btn-ghost font-mono text-[10px] uppercase tracking-widest" on:click={() => checkout.prevStep()}>← PERFIL</button>
            <button class="btn-rust disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
              disabled={state.loading || (state.deliveryMethod !== 'tienda' && !selectedAddressId)}
              on:click={crearOrden}>
              {#if state.loading}
                <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                </svg>
                CREANDO ORDEN...
              {:else}
                CONFIRMAR → PAGO
              {/if}
            </button>
          </div>
        </div>

      <!-- PASO: PAGO -->
      {:else if state.step === 'pago'}
        <div class="space-y-4">

          <!-- Cabecera -->
          <div class="bg-iron-900 border border-steel-600/25"
               style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
            <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between">
              <div>
                <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// PASO 04</p>
                <h2 class="font-display text-2xl text-bone uppercase leading-none">PAGO Y CONFIRMACIÓN</h2>
                {#if state.order}
                  <p class="font-mono text-[10px] text-steel-500 mt-1">ORDEN {state.order.order_number}</p>
                {/if}
              </div>
            </div>
            {#if (state.order?.sub_orders.length ?? 0) > 1}
              <div class="px-6 py-3 border border-yellow-700/50 bg-yellow-600/10 m-4 flex items-center gap-3">
                <span class="w-1.5 h-1.5 bg-yellow-500 flex-shrink-0"></span>
                <p class="font-mono text-[10px] text-yellow-400 uppercase tracking-widest">
                  TU PEDIDO TIENE {state.order?.sub_orders.length} PROVEEDORES — REALIZA UN PAGO SEPARADO A CADA UNO.
                </p>
              </div>
            {/if}
          </div>

          <!-- Banner countdown -->
          {#if state.order?.payment_deadline && (hayPagosPendientes || deadlineExpired)}
            <div class="border px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3
              {deadlineExpired ? 'border-rust-700/50 bg-rust-600/10' : 'border-yellow-700/50 bg-yellow-600/10'}">
              <div>
                {#if deadlineExpired}
                  <p class="font-mono text-xs text-rust-400 uppercase tracking-widest">LA RESERVA DE STOCK HA EXPIRADO</p>
                  <p class="font-mono text-[10px] text-steel-500 mt-1">LOS ARTÍCULOS PENDIENTES FUERON LIBERADOS.</p>
                {:else}
                  <p class="font-mono text-xs text-yellow-400 uppercase tracking-widest">TIEMPO PARA PAGAR</p>
                  <p class="font-display text-2xl text-yellow-400 leading-none">{countdown || '...'}</p>
                {/if}
              </div>
              {#if !deadlineExpired && !todosSubidos}
                <a href="/cliente/historial-compras" class="btn-ghost font-mono text-[10px] uppercase tracking-widest shrink-0">
                  PAGAR MÁS TARDE →
                </a>
              {/if}
            </div>
          {/if}

          <!-- Sub-órdenes -->
          {#if state.order}
            {#each state.order.sub_orders as sub (sub.id)}
              {@const form = proofForms[sub.id]}
              {@const pay  = sub.provider_payment_info}

              <div class="bg-iron-900 border {form?.uploaded ? 'border-green-700/60' : 'border-steel-600/25'}"
                   style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">

                <div class="border-b border-steel-600/25 px-5 py-3 flex items-center justify-between bg-iron-800/30">
                  <div>
                    <p class="font-mono text-xs text-bone">{sub.provider_name}</p>
                    <p class="font-mono text-[9px] text-steel-600">{sub.sub_order_number}</p>
                  </div>
                  <div class="text-right">
                    <p class="font-display text-xl text-bone leading-none">S/ {parseFloat(sub.total).toFixed(2)}</p>
                    {#if form?.uploaded}
                      <p class="font-mono text-[9px] text-green-400">✓ COMPROBANTE ENVIADO</p>
                    {:else}
                      <p class="font-mono text-[9px] text-yellow-500">PENDIENTE DE PAGO</p>
                    {/if}
                  </div>
                </div>

                <div class="p-5 space-y-4">
                  <!-- Items -->
                  <div class="space-y-1.5">
                    {#each sub.items as item}
                      <div class="flex justify-between">
                        <span class="font-mono text-[10px] text-steel-400">{item.quantity}× {item.product_name}</span>
                        <span class="font-mono text-[10px] text-bone">S/ {parseFloat(item.subtotal).toFixed(2)}</span>
                      </div>
                    {/each}
                    <div class="border-t border-steel-600/20 pt-2 space-y-1">
                      <div class="flex justify-between">
                        <span class="font-mono text-[9px] text-steel-600 uppercase">SUBTOTAL</span>
                        <span class="font-mono text-[10px] text-steel-400">S/ {parseFloat(sub.subtotal).toFixed(2)}</span>
                      </div>
                      {#if parseFloat(sub.discount) > 0}
                        <div class="flex justify-between">
                          <span class="font-mono text-[9px] text-steel-600 uppercase">DESCUENTO ({sub.discount_percent}%)</span>
                          <span class="font-mono text-[10px] text-green-400">−S/ {parseFloat(sub.discount).toFixed(2)}</span>
                        </div>
                      {/if}
                      {#if parseFloat(sub.igv_amount) > 0}
                        <div class="flex justify-between">
                          <span class="font-mono text-[9px] text-steel-600 uppercase">IGV ({sub.igv_rate}%)</span>
                          <span class="font-mono text-[10px] text-steel-500">S/ {parseFloat(sub.igv_amount).toFixed(2)}</span>
                        </div>
                      {/if}
                      <div class="flex justify-between border-t border-steel-600/20 pt-1">
                        <span class="font-mono text-[10px] text-bone uppercase">TOTAL A PAGAR</span>
                        <span class="font-display text-lg text-rust-600 leading-none">S/ {parseFloat(sub.total).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  <!-- Datos de pago del proveedor -->
                  <div class="bg-iron-800 border border-steel-600/25 p-4">
                    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-3">// DATOS DE PAGO — {sub.provider_name}</p>
                    {#if pay.banco_nombre || pay.banco_cuenta}
                      <div class="border border-steel-600/20 bg-iron-900/50 p-3 mb-3 space-y-2">
                        <p class="font-mono text-[9px] text-steel-600 uppercase">TRANSFERENCIA BANCARIA</p>
                        {#each [
                          { label: 'BANCO', value: pay.banco_nombre },
                          { label: 'N° CUENTA', value: pay.banco_cuenta },
                          { label: 'CCI', value: pay.banco_cci },
                        ].filter(r => r.value) as row}
                          <div class="flex justify-between">
                            <span class="font-mono text-[10px] text-steel-500 uppercase">{row.label}</span>
                            <span class="font-mono text-xs text-bone select-all">{row.value}</span>
                          </div>
                        {/each}
                      </div>
                    {/if}
                    {#if pay.yape_numero || pay.plin_numero}
                      <div class="flex gap-3 flex-wrap">
                        {#if pay.yape_numero}
                          <div class="flex-1 min-w-[120px] border border-steel-600/25 bg-iron-900/50 p-3 text-center">
                            <p class="font-mono text-[9px] text-steel-600 uppercase mb-1">YAPE</p>
                            <p class="font-mono text-sm text-bone select-all">{pay.yape_numero}</p>
                          </div>
                        {/if}
                        {#if pay.plin_numero}
                          <div class="flex-1 min-w-[120px] border border-steel-600/25 bg-iron-900/50 p-3 text-center">
                            <p class="font-mono text-[9px] text-steel-600 uppercase mb-1">PLIN</p>
                            <p class="font-mono text-sm text-bone select-all">{pay.plin_numero}</p>
                          </div>
                        {/if}
                      </div>
                    {/if}
                    {#if !pay.banco_nombre && !pay.banco_cuenta && !pay.yape_numero && !pay.plin_numero}
                      <p class="font-mono text-[10px] text-steel-600 uppercase">EL PROVEEDOR COORDINARÁ EL MÉTODO DE PAGO CONTIGO.</p>
                    {/if}
                  </div>

                  <!-- SubOrder expirada -->
                  {#if sub.expired || sub.status === 'cancelado'}
                    <div class="border border-steel-600/30 bg-iron-800/30 px-4 py-3 flex items-start gap-3">
                      <span class="w-1.5 h-1.5 bg-steel-600 flex-shrink-0 mt-1"></span>
                      <div>
                        <p class="font-mono text-[10px] text-steel-400 uppercase">LA RESERVA EXPIRÓ Y FUE LIBERADA.</p>
                        <p class="font-mono text-[10px] text-steel-600 mt-0.5">
                          PUEDES VOLVER A AGREGARLO AL <a href="/carrito" class="text-rust-500 hover:text-rust-400">CARRITO</a> SI AÚN ESTÁ DISPONIBLE.
                        </p>
                      </div>
                    </div>

                  <!-- Comprobante enviado -->
                  {:else if form?.uploaded}
                    <div class="border border-green-700/50 bg-green-600/10 px-4 py-3 flex items-start gap-3">
                      <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0 mt-1"></span>
                      <div>
                        <p class="font-mono text-xs text-green-400 uppercase tracking-widest">COMPROBANTE ENVIADO CORRECTAMENTE</p>
                        <p class="font-mono text-[10px] text-steel-400 mt-0.5">
                          {PAYMENT_METHOD_LABELS[form.payment_method]} · S/ {parseFloat(form.amount).toFixed(2)}
                          {form.operation_number ? ` · OP. ${form.operation_number}` : ''}
                        </p>
                        <p class="font-mono text-[10px] text-steel-600 mt-0.5">EL PROVEEDOR VERIFICARÁ TU PAGO Y CONFIRMARÁ.</p>
                      </div>
                    </div>

                  <!-- Formulario comprobante -->
                  {:else if form}
                    <div class="space-y-4">
                      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SUBE TU COMPROBANTE DE PAGO</p>

                      <!-- Método -->
                      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {#each [
                          { value: 'transferencia',          label: 'TRANSFERENCIA' },
                          { value: 'yape',                   label: 'YAPE' },
                          { value: 'plin',                   label: 'PLIN' },
                          { value: 'efectivo_contraentrega', label: 'CONTRAENTREGA' },
                          { value: 'efectivo_tienda',        label: 'EN TIENDA' },
                        ] as m}
                          <button class="border py-2 px-3 font-mono text-[10px] uppercase tracking-widest transition-colors
                            {form.payment_method === m.value
                              ? 'border-rust-600 bg-rust-600/20 text-rust-400'
                              : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                            on:click={() => { proofForms[sub.id] = { ...form, payment_method: m.value as PaymentMethod }; }}
                          >{m.label}</button>
                        {/each}
                      </div>

                      <!-- Monto y número -->
                      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label for="amount-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// MONTO PAGADO (S/) *</label>
                          <input id="amount-{sub.id}" type="number" step="0.01" min="0.01"
                            bind:value={proofForms[sub.id].amount} class="input-industrial" />
                        </div>
                        <div>
                          <label for="opnum-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// N° DE OPERACIÓN</label>
                          <input id="opnum-{sub.id}" type="text" bind:value={proofForms[sub.id].operation_number}
                            placeholder="Ej: 123456789" class="input-industrial" />
                        </div>
                      </div>

                      <!-- Archivo -->
                      <div>
                        <label for="file-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">// CAPTURA / VOUCHER * (JPG, PNG, PDF)</label>
                        <label for="file-{sub.id}"
                          class="flex flex-col items-center justify-center w-full border-2 border-dashed cursor-pointer py-6 transition-colors
                            {form.file ? 'border-green-700/50 bg-green-600/5' : 'border-steel-600/40 hover:border-rust-600/50 hover:bg-rust-600/5'}">
                          {#if form.file}
                            <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{form.file.name}</p>
                            <p class="font-mono text-[10px] text-steel-600 mt-1">{(form.file.size / 1024).toFixed(1)} KB</p>
                          {:else}
                            <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">ADJUNTAR ARCHIVO</p>
                            <p class="font-mono text-[10px] text-steel-700 mt-1">HAZ CLIC O ARRASTRA AQUÍ</p>
                          {/if}
                        </label>
                        <input id="file-{sub.id}" type="file" accept="image/*,application/pdf" class="hidden"
                          on:change={(e) => onFileChange(sub.id, e)} />
                      </div>

                      {#if form.error}
                        <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
                          <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
                          <p class="font-mono text-xs text-rust-400">{form.error}</p>
                        </div>
                      {/if}

                      <button class="w-full btn-rust disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        disabled={form.uploading || !form.file || !form.amount}
                        on:click={() => subirComprobante(sub)}>
                        {#if form.uploading}
                          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                          </svg>
                          SUBIENDO COMPROBANTE...
                        {:else}
                          ENVIAR COMPROBANTE A {sub.provider_name.toUpperCase()}
                        {/if}
                      </button>
                    </div>
                  {/if}

                </div>
              </div>
            {/each}
          {/if}

          <!-- Progreso / Confirmación final -->
          {#if !todosSubidos && activeSubs.length > 0}
            <div class="bg-iron-900 border border-steel-600/25 px-5 py-4">
              <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                {activeSubs.filter(s => proofForms[s.id]?.uploaded).length} DE {activeSubs.length} COMPROBANTE(S) ENVIADO(S).
                SUBE TODOS PARA CONFIRMAR.
              </p>
            </div>
          {:else}
            <div class="bg-iron-900 border border-green-700/50 p-8 text-center"
                 style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
              <p class="font-mono text-[10px] text-green-400 uppercase tracking-widest mb-3">// PEDIDO CONFIRMADO</p>
              <h2 class="font-display text-4xl text-bone uppercase leading-none mb-3">COMPROBANTES ENVIADOS</h2>
              <p class="font-mono text-xs text-steel-400 mb-5">LOS PROVEEDORES VERIFICARÁN LOS PAGOS Y ACTUALIZARÁN EL ESTADO.</p>
              {#if state.order}
                <div class="inline-block border border-steel-600/25 bg-iron-800 px-6 py-3 mb-5">
                  <p class="font-mono text-[9px] text-steel-600 uppercase mb-1">NÚMERO DE ORDEN</p>
                  <p class="font-display text-2xl text-rust-600 leading-none">{state.order.order_number}</p>
                </div>
              {/if}
              <div class="flex flex-col sm:flex-row gap-3 justify-center">
                <a href="cliente/historial-compras" class="btn-rust">VER MIS PEDIDOS →</a>
                <a href="/" class="btn-outline">SEGUIR COMPRANDO</a>
              </div>
            </div>
          {/if}

        </div>
      {/if}

    </section>

    <!-- Columna derecha: Resumen sticky -->
    <aside class="lg:col-span-1">
      <div class="bg-iron-900 border border-steel-600/25 sticky top-24"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// RESUMEN DE COMPRA</p>
        </div>

        <!-- Items por proveedor -->
        <div class="px-5 py-4 space-y-3">
          {#each Object.entries(byProvider) as [provName, items]}
            <div>
              <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">{provName}</p>
              {#each items as item}
                <div class="flex justify-between pl-2">
                  <span class="font-mono text-[10px] text-steel-400 truncate pr-2 max-w-[140px]">
                    {item.cantidad}× {item.product.name}
                  </span>
                  <span class="font-mono text-[10px] text-bone flex-shrink-0">{fmt(item.precioTotal)}</span>
                </div>
              {/each}
            </div>
          {/each}
        </div>

        <!-- Desglose financiero -->
        <div class="border-t border-steel-600/20 px-5 py-3 space-y-1.5">
          {#if state.order}
            <div class="flex justify-between">
              <span class="font-mono text-[10px] text-steel-600 uppercase">SUBTOTAL</span>
              <span class="font-mono text-[10px] text-steel-400">{fmt(parseFloat(state.order.subtotal))}</span>
            </div>
            {#if parseFloat(state.order.discount) > 0}
              <div class="flex justify-between">
                <span class="font-mono text-[10px] text-steel-600 uppercase">DESCUENTO</span>
                <span class="font-mono text-[10px] text-green-400">−{fmt(parseFloat(state.order.discount))}</span>
              </div>
            {/if}
            {#if parseFloat(state.order.tax) > 0}
              <div class="flex justify-between">
                <span class="font-mono text-[10px] text-steel-600 uppercase">IGV (18%)</span>
                <span class="font-mono text-[10px] text-steel-500">{fmt(parseFloat(state.order.tax))}</span>
              </div>
            {/if}
          {:else}
            <div class="flex justify-between">
              <span class="font-mono text-[10px] text-steel-600 uppercase">PRODUCTOS ({state.items.length})</span>
              <span class="font-mono text-[10px] text-steel-400">{fmt(subtotal)}</span>
            </div>
          {/if}
          {#if provCount > 1}
            <div class="border border-yellow-700/50 bg-yellow-600/10 px-3 py-2 mt-2">
              <p class="font-mono text-[9px] text-yellow-400 uppercase tracking-widest">
                {provCount} PROVEEDORES — SUB-ORDEN POR CADA UNO
              </p>
            </div>
          {/if}
        </div>

        <!-- Total -->
        <div class="border-t border-steel-600/25 px-5 py-4 flex justify-between items-center">
          <span class="font-mono text-[10px] text-steel-400 uppercase">TOTAL</span>
          <span class="font-display text-2xl text-rust-600 leading-none">
            {state.order ? fmt(parseFloat(state.order.total)) : fmt(subtotal)}
          </span>
        </div>

        {#if !state.order}
          <div class="border-t border-steel-600/20 px-5 py-2">
            <p class="font-mono text-[9px] text-steel-700">*DESCUENTO POR HISTORIAL SE APLICA AL CONFIRMAR.</p>
          </div>
        {/if}

        <!-- Pasos -->
        <div class="border-t border-steel-600/25 px-5 py-4 space-y-2">
          {#each CHECKOUT_STEPS as step, i}
            {@const done   = i < stepIdx}
            {@const active = i === stepIdx}
            <div class="flex items-start gap-3">
              <span class="font-display text-lg leading-none flex-shrink-0 mt-0.5
                {active ? 'text-rust-600' : done ? 'text-rust-700' : 'text-steel-700'}">
                {done ? '✓' : i + 1}
              </span>
              <div>
                <p class="font-mono text-[10px] uppercase tracking-widest
                  {active ? 'text-bone' : done ? 'text-steel-400' : 'text-steel-700'}">
                  {STEP_LABELS[step].toUpperCase()}
                </p>
                {#if active && step === 'carrito'}
                  <p class="font-mono text-[9px] text-steel-600">{state.items.length} PRODUCTO(S)</p>
                {:else if active && step === 'perfil' && state.customer}
                  <p class="font-mono text-[9px] text-steel-600">{state.customer.email}</p>
                {:else if active && step === 'entrega'}
                  <p class="font-mono text-[9px] text-steel-600">
                    {state.shippingAddress ? state.shippingAddress.full_address : 'POR DEFINIR'}
                  </p>
                {:else if !done && !active}
                  <p class="font-mono text-[9px] text-steel-700">POR DEFINIR</p>
                {/if}
              </div>
            </div>
          {/each}
        </div>

      </div>
    </aside>

  </main>
  {:else}
    <div class="flex items-center justify-center min-h-[60vh]">
      <div class="text-center">
        <p class="font-display text-4xl text-steel-700 mb-3">▪</p>
        <p class="font-mono text-xs text-steel-600 uppercase tracking-widest animate-pulse">CARGANDO TU PEDIDO...</p>
      </div>
    </div>
  {/if}

</div>
