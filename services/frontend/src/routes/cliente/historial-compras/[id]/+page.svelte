<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import type {
    Order,
    OrderStatus,
    SubOrder,
    SubOrderStatus,
    OrderItem,
    PaymentProof,
    PaymentMethod,
  } from '$lib/api/types';

  let order: Order | null = null;
  let loading = true;
  let error = '';
  let receivingSubOrders: Record<number, boolean> = {};
  let receiveErrors: Record<number, string> = {};

  // -------------------------------------------------------------------
  // Helpers de UI
  // -------------------------------------------------------------------
  const orderStatusLabel: Record<OrderStatus, string> = {
    pendiente_pago: 'PENDIENTE DE PAGO',
    pagado: 'PAGADO',
    procesando: 'PROCESANDO',
    enviado: 'ENVIADO',
    completado: 'COMPLETADO',
    cancelado: 'CANCELADO',
  };

  const orderStatusColor: Record<OrderStatus, string> = {
    pendiente_pago: 'border-yellow-700/50 text-yellow-400',
    pagado: 'border-steel-600/50 text-steel-300',
    procesando: 'border-rust-700/50 text-rust-400',
    enviado: 'border-steel-600/50 text-bone',
    completado: 'border-green-700/50 text-green-400',
    cancelado: 'border-rust-700/50 text-rust-500',
  };

  const subOrderStatusLabel: Record<SubOrderStatus, string> = {
    pendiente_pago:   'PENDIENTE DE PAGO',
    pago_en_revision: 'PAGO EN REVISIÓN',
    pago_rechazado:   'PAGO RECHAZADO',
    confirmado:       'CONFIRMADO',
    enviado:          'ENVIADO',
    entregado:        'RECIBIDO',
    cancelado:        'CANCELADO',
  };

  const subOrderStatusColor: Record<SubOrderStatus, string> = {
    pendiente_pago:   'border-yellow-700/50 text-yellow-400',
    pago_en_revision: 'border-rust-700/50 text-rust-400',
    pago_rechazado:   'border-rust-700/50 text-rust-500',
    confirmado:       'border-steel-600/50 text-bone',
    enviado:          'border-steel-600/50 text-steel-300',
    entregado:        'border-green-700/50 text-green-400',
    cancelado:        'border-steel-600/40 text-steel-600',
  };

  const proofStatusBadge: Record<'uploaded' | 'approved' | 'rejected', string> = {
    uploaded: 'border-yellow-700/50 text-yellow-400',
    approved: 'border-green-700/50 text-green-400',
    rejected: 'border-rust-700/50 text-rust-500',
  };

  const proofStatusLabel: Record<'uploaded' | 'approved' | 'rejected', string> = {
    uploaded: 'SUBIDO',
    approved: 'APROBADO ✓',
    rejected: 'RECHAZADO ×',
  };

  const deliveryLabel: Record<string, string> = {
    domicilio: 'ENVÍO A DOMICILIO',
    agencia: 'RECOJO EN AGENCIA',
    tienda: 'RECOJO EN TIENDA',
  };

  const paymentMethodLabel: Record<string, string> = {
    transferencia: 'TRANSFERENCIA BANCARIA',
    yape: 'YAPE',
    plin: 'PLIN',
    efectivo_contraentrega: 'EFECTIVO CONTRAENTREGA',
    efectivo_tienda: 'EFECTIVO EN TIENDA',
  };

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function formatCurrency(value: string | number): string {
    return `S/ ${parseFloat(String(value)).toFixed(2)}`;
  }

  // ── Countdown timer (payment_deadline) ───────────────────────────────────
  let countdown = '';
  let countdownInterval: ReturnType<typeof setInterval> | null = null;

  function startCountdown(deadline: string) {
    if (countdownInterval) clearInterval(countdownInterval);
    function tick() {
      const diff = new Date(deadline).getTime() - Date.now();
      if (diff <= 0) {
        countdown = 'TIEMPO EXPIRADO';
        clearInterval(countdownInterval!);
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

  $: hasTrulyPending = (order?.sub_orders ?? []).some(
    s => s.status === 'pendiente_pago' && !s.expired
  );

  $: allInRevisionOrBeyond =
    order?.status === 'pendiente_pago' &&
    !hasTrulyPending &&
    (order?.sub_orders ?? []).some(s => s.status === 'pago_en_revision');

  $: if (order?.payment_deadline && hasTrulyPending) {
    startCountdown(order.payment_deadline);
  }

  $: if (!hasTrulyPending && countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
    countdown = '';
  }

  onDestroy(() => { if (countdownInterval) clearInterval(countdownInterval); });

  function getLastRejectionReason(sub: SubOrder): string {
    if (!sub.payment_rejected || !sub.payments?.length) return '';
    const rejected = sub.payments
      .filter(p => p.status === 'rejected')
      .sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime());
    return rejected[0]?.rejection_reason ?? '';
  }

  function buildPaymentOptions(sub: SubOrder): string[] {
    const opts: string[] = [];
    const info = sub.provider_payment_info;
    if (info.banco_nombre && info.banco_cuenta)
      opts.push(`${info.banco_nombre} — Cta: ${info.banco_cuenta}`);
    if (info.banco_cci)
      opts.push(`CCI: ${info.banco_cci}`);
    if (info.yape_numero)
      opts.push(`Yape: ${info.yape_numero}`);
    if (info.plin_numero)
      opts.push(`Plin: ${info.plin_numero}`);
    return opts;
  }

  // -------------------------------------------------------------------
  // Formulario de pago por SubOrder
  // -------------------------------------------------------------------
  interface ProofForm {
    payment_method: PaymentMethod;
    operation_number: string;
    amount: string;
    file: File | null;
    uploading: boolean;
    uploaded: boolean;
    error: string;
  }

  let proofForms: Record<number, ProofForm> = {};

  const PAYMENT_METHOD_LABELS: Record<string, string> = {
    transferencia: 'TRANSFERENCIA BANCARIA',
    yape: 'YAPE',
    plin: 'PLIN',
    efectivo_contraentrega: 'EFECTIVO CONTRAENTREGA',
    efectivo_tienda: 'EFECTIVO EN TIENDA',
  };

  $: if (order) {
    for (const sub of order.sub_orders) {
      if (
        (sub.status === 'pendiente_pago' || sub.status === 'pago_rechazado') &&
        !proofForms[sub.id]
      ) {
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
      proofForms[subId] = { ...proofForms[subId], file: input.files[0] };
    }
  }

  async function subirComprobante(sub: SubOrder) {
    const form = proofForms[sub.id];
    if (!form.file) {
      proofForms[sub.id] = { ...form, error: 'Debes adjuntar un comprobante.' };
      return;
    }
    if (!form.amount || parseFloat(form.amount) <= 0) {
      proofForms[sub.id] = { ...form, error: 'Ingresa el monto pagado.' };
      return;
    }
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
      order = await api.orders.getOrder(token, order!.id);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Error al subir el comprobante.';
      proofForms[sub.id] = { ...proofForms[sub.id], uploading: false, error: msg };
    }
  }

  async function marcarComoRecibido(sub: SubOrder) {
    const token = auth.getAccessToken();
    if (!token || !order) return;

    receivingSubOrders = { ...receivingSubOrders, [sub.id]: true };
    receiveErrors = { ...receiveErrors, [sub.id]: '' };

    try {
      await api.orders.markSubOrderReceived(token, sub.id);
      order = await api.orders.getOrder(token, order.id);
    } catch (e: any) {
      const msg = e?.response?.data?.error || 'No se pudo marcar la suborden como recibida.';
      receiveErrors = { ...receiveErrors, [sub.id]: msg };
    } finally {
      receivingSubOrders = { ...receivingSubOrders, [sub.id]: false };
    }
  }

  // -------------------------------------------------------------------
  // Carga de datos
  // -------------------------------------------------------------------
  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }
    const { id } = $page.params;
    try {
      order = await api.orders.getOrder(token, Number(id));
    } catch (e: any) {
      error =
        e?.response?.status === 404
          ? 'Pedido no encontrado o no tienes acceso a él.'
          : 'No se pudo cargar el detalle del pedido.';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{order ? `Pedido ${order.order_number}` : 'Detalle de Pedido'} — ECOMPARTS</title>
</svelte:head>

<div class="container-responsive py-10 max-w-4xl">

  <!-- Breadcrumb -->
  <div class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-steel-500 mb-8">
    <a href="/cliente/perfil" class="hover:text-rust-500 transition-colors">MI CUENTA</a>
    <span class="text-steel-700">/</span>
    <a href="/cliente/historial-compras" class="hover:text-rust-500 transition-colors">HISTORIAL</a>
    <span class="text-steel-700">/</span>
    <span class="text-bone truncate">{order ? order.order_number : 'CARGANDO...'}</span>
  </div>

  <!-- Cargando -->
  {#if loading}
    <div class="flex flex-col items-center justify-center py-24 gap-4">
      <svg class="animate-spin h-8 w-8 text-rust-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO PEDIDO...</p>
    </div>

  {:else if error}
    <div class="border border-rust-700/50 bg-rust-600/10 p-6 text-center">
      <p class="font-mono text-xs text-rust-400 mb-4">{error}</p>
      <a href="/cliente/historial-compras" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">
        ← VOLVER AL HISTORIAL
      </a>
    </div>

  {:else if order}

    <!-- ================================================================
         ENCABEZADO DE LA ORDEN
    ================================================================ -->
    <div class="bg-iron-900 border border-steel-600/25 mb-4"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-6 py-4 flex items-center justify-between gap-3 flex-wrap">
        <div class="flex items-center gap-3 flex-wrap">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// ORDEN {order.order_number}</p>
          {#if allInRevisionOrBeyond}
            <span class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border border-rust-700/50 text-rust-400">
              PAGO EN REVISIÓN
            </span>
          {:else}
            <span class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border {orderStatusColor[order.status]}">
              {orderStatusLabel[order.status]}
            </span>
          {/if}
        </div>
        <p class="font-mono text-[10px] text-steel-500">{formatDate(order.created_at)}</p>
      </div>

      <div class="px-6 py-5 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-5">
        <div class="space-y-1">
          {#if order.payment_deadline && hasTrulyPending}
            <div class="border border-yellow-700/50 bg-yellow-600/10 px-4 py-2 flex items-center gap-3 mb-3">
              <span class="w-1.5 h-1.5 bg-yellow-500 flex-shrink-0"></span>
              <p class="font-mono text-xs text-yellow-400 uppercase tracking-widest">
                TIEMPO PARA PAGAR: {countdown || '...'}
              </p>
            </div>
          {/if}
          {#if order.customer_notes}
            <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
              NOTA: {order.customer_notes}
            </p>
          {/if}
        </div>

        <!-- Totales -->
        <div class="min-w-[180px] space-y-1.5">
          <div class="flex justify-between gap-6">
            <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">SUBTOTAL</span>
            <span class="font-mono text-xs text-steel-400">{formatCurrency(order.subtotal)}</span>
          </div>
          {#if parseFloat(order.discount) > 0}
            <div class="flex justify-between gap-6">
              <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">DESCUENTO</span>
              <span class="font-mono text-xs text-green-400">-{formatCurrency(order.discount)}</span>
            </div>
          {/if}
          <div class="flex justify-between gap-6">
            <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">IGV</span>
            <span class="font-mono text-xs text-steel-400">{formatCurrency(order.tax)}</span>
          </div>
          <div class="flex justify-between gap-6 border-t border-steel-600/20 pt-1.5">
            <span class="font-mono text-[10px] text-steel-400 uppercase tracking-widest">TOTAL</span>
            <span class="font-display text-2xl text-rust-600 leading-none">{formatCurrency(order.total)}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================
         ENTREGA
    ================================================================ -->
    <div class="bg-iron-900 border border-steel-600/25 mb-4"
         style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
      <div class="border-b border-steel-600/25 px-5 py-3">
        <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// ENTREGA</p>
      </div>
      <div class="px-5 py-4 flex items-start gap-3">
        <svg class="h-5 w-5 text-rust-600 mt-0.5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
          <path fill-rule="evenodd"
            d="M11.54 22.351l.07.04.028.016a.76.76 0 00.723 0l.028-.015.071-.041a16.975 16.975 0 001.144-.742 19.58 19.58 0 002.683-2.282c1.944-2.013 3.5-4.697 3.5-8.327a8 8 0 10-16 0c0 3.63 1.556 6.314 3.5 8.327a19.579 19.579 0 002.682 2.282 16.975 16.975 0 001.145.742zM12 13.5a3 3 0 100-6 3 3 0 000 6z"
            clip-rule="evenodd"/>
        </svg>
        <div>
          <p class="font-mono text-xs text-bone uppercase tracking-widest mb-1">
            {deliveryLabel[order.delivery_method] ?? order.delivery_method}
          </p>
          {#if order.shipping_address_detail}
            <p class="font-mono text-xs text-steel-400">
              {order.shipping_address_detail.contact_name} · {order.shipping_address_detail.contact_phone}
            </p>
            <p class="font-mono text-[10px] text-steel-500 mt-0.5">
              {order.shipping_address_detail.full_address}
            </p>
            {#if order.shipping_address_detail.reference}
              <p class="font-mono text-[10px] text-steel-600 mt-0.5">
                REF: {order.shipping_address_detail.reference}
              </p>
            {/if}
          {:else}
            <p class="font-mono text-[10px] text-steel-600">SIN DIRECCIÓN REGISTRADA</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- ================================================================
         SUB-ÓRDENES POR PROVEEDOR
    ================================================================ -->
    {#if order.sub_orders && order.sub_orders.length > 0}
      <div class="space-y-4">
        {#each order.sub_orders as sub (sub.id)}
          <div class="bg-iron-900 border border-steel-600/25"
               style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">

            <!-- Encabezado sub-orden -->
            <div class="border-b border-steel-600/25 px-5 py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-iron-800/50">
              <div class="flex items-center gap-3 flex-wrap">
                <span class="font-mono text-xs text-bone">{sub.provider_name}</span>
                <span class="font-mono text-[9px] text-steel-600">#{sub.sub_order_number}</span>
                <span class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border {subOrderStatusColor[sub.status]}">
                  {subOrderStatusLabel[sub.status]}
                </span>
              </div>
              <div class="text-right">
                <p class="font-display text-xl text-bone leading-none">{formatCurrency(sub.total)}</p>
                <p class="font-mono text-[9px] text-steel-600 uppercase">IGV INCL.</p>
              </div>
            </div>

            {#if sub.tracking_number || sub.shipped_at || sub.delivered_at}
              <div class="border-b border-steel-600/20 px-5 py-2 flex flex-wrap gap-4">
                {#if sub.tracking_number}
                  <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                    TRACKING: <span class="text-bone">{sub.tracking_number}</span>
                  </p>
                {/if}
                {#if sub.shipped_at}
                  <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                    DESPACHADO: {formatDate(sub.shipped_at)}
                  </p>
                {/if}
                {#if sub.delivered_at}
                  <p class="font-mono text-[10px] text-green-400 uppercase tracking-widest">
                    RECIBIDO: {formatDate(sub.delivered_at)}
                  </p>
                {/if}
              </div>
            {/if}

            <!-- Confirmar recepción -->
            {#if sub.status === 'enviado'}
              <div class="border-b border-green-700/30 bg-green-600/10 px-5 py-4">
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <p class="font-mono text-xs text-green-400 uppercase tracking-widest mb-1">¿YA RECIBISTE ESTE ENVÍO?</p>
                    <p class="font-mono text-[10px] text-steel-400">
                      Confírmalo para cerrar correctamente el seguimiento de esta suborden.
                    </p>
                  </div>
                  <button
                    class="btn-rust disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                    on:click={() => marcarComoRecibido(sub)}
                    disabled={receivingSubOrders[sub.id]}
                  >
                    {receivingSubOrders[sub.id] ? 'CONFIRMANDO...' : 'MARCAR COMO RECIBIDO'}
                  </button>
                </div>
                {#if receiveErrors[sub.id]}
                  <p class="font-mono text-[10px] text-rust-400 mt-3">{receiveErrors[sub.id]}</p>
                {/if}
              </div>
            {/if}

            <!-- Items de la sub-orden -->
            <div class="divide-y divide-steel-600/15">
              {#each sub.items as item (item.id)}
                <div class="flex justify-between items-start gap-4 px-5 py-4">
                  <div class="flex-1 min-w-0">
                    <p class="font-mono text-xs text-bone truncate">{item.product_name}</p>
                    <p class="font-mono text-[10px] text-steel-600 mt-0.5">SKU: {item.product_sku}</p>
                  </div>
                  <div class="text-right flex-shrink-0 space-y-0.5">
                    <p class="font-mono text-[10px] text-steel-500">{item.quantity} × {formatCurrency(item.unit_price)}</p>
                    <p class="font-mono text-xs text-bone">{formatCurrency(item.subtotal)}</p>
                    {#if parseFloat(item.discount) > 0}
                      <p class="font-mono text-[10px] text-green-400">-{formatCurrency(item.discount)}</p>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>

            <!-- Desglose -->
            <div class="border-t border-steel-600/20 px-5 py-3 bg-iron-800/30 flex flex-wrap gap-x-6 gap-y-1">
              <span class="font-mono text-[10px] text-steel-600 uppercase">SUBTOTAL: {formatCurrency(sub.subtotal)}</span>
              <span class="font-mono text-[10px] text-steel-600 uppercase">IGV ({parseFloat(sub.igv_rate) * 100}%): {formatCurrency(sub.igv_amount)}</span>
              <span class="font-mono text-[10px] text-bone uppercase">TOTAL: {formatCurrency(sub.total)}</span>
            </div>

            <!-- Pago pendiente / rechazado -->
            {#if (sub.status === 'pendiente_pago' && !sub.expired) || sub.status === 'pago_rechazado'}
              {@const pay = sub.provider_payment_info}
              {@const form = proofForms[sub.id]}

              <!-- Banner rechazo -->
              {#if sub.status === 'pago_rechazado'}
                <div class="border-t border-rust-700/50 bg-rust-600/10 px-5 py-4">
                  <div class="flex items-start gap-3">
                    <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
                    <div>
                      <p class="font-mono text-xs text-rust-400 uppercase tracking-widest mb-1">
                        COMPROBANTE RECHAZADO — CORRÍGELO Y REENVÍA
                      </p>
                      {#if sub.rejection_reason}
                        <p class="font-mono text-[10px] text-steel-400">
                          MOTIVO: {sub.rejection_reason}
                        </p>
                      {:else}
                        {@const reason = getLastRejectionReason(sub)}
                        {#if reason}
                          <p class="font-mono text-[10px] text-steel-400">MOTIVO: {reason}</p>
                        {/if}
                      {/if}
                    </div>
                  </div>
                </div>
              {/if}

              <div class="border-t border-steel-600/20 px-5 py-5 space-y-5">

                <!-- Datos bancarios del proveedor -->
                <div class="bg-iron-800 border border-steel-600/25 p-4">
                  <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">
                    // DATOS DE PAGO — {sub.provider_name}
                  </p>

                  {#if pay.banco_nombre || pay.banco_cuenta}
                    <div class="border border-steel-600/20 bg-iron-900/50 p-3 mb-3 space-y-2">
                      <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest">TRANSFERENCIA BANCARIA</p>
                      {#if pay.banco_nombre}
                        <div class="flex justify-between">
                          <span class="font-mono text-[10px] text-steel-500 uppercase">BANCO</span>
                          <span class="font-mono text-xs text-bone">{pay.banco_nombre}</span>
                        </div>
                      {/if}
                      {#if pay.banco_cuenta}
                        <div class="flex justify-between">
                          <span class="font-mono text-[10px] text-steel-500 uppercase">N° CUENTA</span>
                          <span class="font-mono text-xs text-bone select-all">{pay.banco_cuenta}</span>
                        </div>
                      {/if}
                      {#if pay.banco_cci}
                        <div class="flex justify-between">
                          <span class="font-mono text-[10px] text-steel-500 uppercase">CCI</span>
                          <span class="font-mono text-xs text-bone select-all">{pay.banco_cci}</span>
                        </div>
                      {/if}
                    </div>
                  {/if}

                  {#if pay.yape_numero || pay.plin_numero}
                    <div class="flex gap-3 flex-wrap">
                      {#if pay.yape_numero}
                        <div class="flex-1 min-w-[120px] border border-steel-600/25 bg-iron-900/50 p-3 text-center">
                          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">YAPE</p>
                          <p class="font-mono text-sm text-bone select-all">{pay.yape_numero}</p>
                        </div>
                      {/if}
                      {#if pay.plin_numero}
                        <div class="flex-1 min-w-[120px] border border-steel-600/25 bg-iron-900/50 p-3 text-center">
                          <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-1">PLIN</p>
                          <p class="font-mono text-sm text-bone select-all">{pay.plin_numero}</p>
                        </div>
                      {/if}
                    </div>
                  {/if}

                  {#if !pay.banco_nombre && !pay.banco_cuenta && !pay.yape_numero && !pay.plin_numero}
                    <p class="font-mono text-[10px] text-steel-600 uppercase">
                      EL PROVEEDOR COORDINARÁ EL MÉTODO DE PAGO CONTIGO.
                    </p>
                  {/if}
                </div>

                <!-- Formulario de comprobante -->
                {#if form && !form.uploaded}
                  <div class="space-y-4">
                    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// SUBE TU COMPROBANTE DE PAGO</p>

                    <!-- Método de pago -->
                    <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {#each [
                        { value: 'transferencia',          label: 'TRANSFERENCIA' },
                        { value: 'yape',                   label: 'YAPE' },
                        { value: 'plin',                   label: 'PLIN' },
                        { value: 'efectivo_contraentrega', label: 'CONTRAENTREGA' },
                        { value: 'efectivo_tienda',        label: 'EN TIENDA' },
                      ] as m}
                        <button
                          class="border py-2 px-3 font-mono text-[10px] uppercase tracking-widest transition-colors
                            {form.payment_method === m.value
                              ? 'border-rust-600 bg-rust-600/20 text-rust-400'
                              : 'border-steel-600/40 text-steel-500 hover:border-steel-400 hover:text-bone'}"
                          on:click={() => { proofForms[sub.id] = { ...form, payment_method: m.value as PaymentMethod }; }}
                        >{m.label}</button>
                      {/each}
                    </div>

                    <!-- Monto y número de operación -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label for="hist-amount-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                          // MONTO PAGADO (S/) *
                        </label>
                        <input
                          id="hist-amount-{sub.id}"
                          type="number" step="0.01" min="0.01"
                          bind:value={proofForms[sub.id].amount}
                          class="input-industrial" />
                      </div>
                      <div>
                        <label for="hist-opnum-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                          // N° DE OPERACIÓN
                        </label>
                        <input
                          id="hist-opnum-{sub.id}"
                          type="text"
                          bind:value={proofForms[sub.id].operation_number}
                          placeholder="Ej: 123456789"
                          class="input-industrial" />
                      </div>
                    </div>

                    <!-- Adjuntar archivo -->
                    <div>
                      <label for="hist-file-{sub.id}" class="block font-mono text-[10px] text-steel-500 uppercase tracking-widest mb-2">
                        // CAPTURA / VOUCHER * (JPG, PNG, PDF)
                      </label>
                      <label for="hist-file-{sub.id}"
                        class="flex flex-col items-center justify-center w-full border-2 border-dashed cursor-pointer py-6 transition-colors
                               {form.file
                                 ? 'border-green-700/50 bg-green-600/5'
                                 : 'border-steel-600/40 hover:border-rust-600/50 hover:bg-rust-600/5'}">
                        {#if form.file}
                          <p class="font-mono text-xs text-green-400 uppercase tracking-widest">{form.file.name}</p>
                          <p class="font-mono text-[10px] text-steel-600 mt-1">{(form.file.size / 1024).toFixed(1)} KB</p>
                        {:else}
                          <p class="font-mono text-xs text-steel-500 uppercase tracking-widest">ADJUNTAR ARCHIVO</p>
                          <p class="font-mono text-[10px] text-steel-700 mt-1">HAZ CLIC O ARRASTRA AQUÍ</p>
                        {/if}
                      </label>
                      <input
                        id="hist-file-{sub.id}"
                        type="file"
                        accept="image/*,application/pdf"
                        class="hidden"
                        on:change={(e) => onFileChange(sub.id, e)}
                      />
                    </div>

                    <!-- Error -->
                    {#if form.error}
                      <div class="border border-rust-700/50 bg-rust-600/10 px-4 py-3 flex items-center gap-3">
                        <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0"></span>
                        <p class="font-mono text-xs text-rust-400">{form.error}</p>
                      </div>
                    {/if}

                    <!-- Botón subir -->
                    <button
                      class="w-full btn-rust disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      disabled={form.uploading || !form.file || !form.amount}
                      on:click={() => subirComprobante(sub)}
                    >
                      {#if form.uploading}
                        <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"></path>
                        </svg>
                        SUBIENDO COMPROBANTE...
                      {:else if sub.status === 'pago_rechazado'}
                        CORREGIR Y REENVIAR COMPROBANTE
                      {:else}
                        ENVIAR COMPROBANTE A {sub.provider_name.toUpperCase()}
                      {/if}
                    </button>
                  </div>

                {:else if form?.uploaded}
                  <div class="border border-green-700/50 bg-green-600/10 px-5 py-4 flex items-start gap-3">
                    <span class="w-1.5 h-1.5 bg-green-500 flex-shrink-0 mt-1"></span>
                    <div>
                      <p class="font-mono text-xs text-green-400 uppercase tracking-widest mb-1">
                        {sub.status === 'pago_rechazado'
                          ? 'COMPROBANTE CORREGIDO Y ENVIADO'
                          : 'COMPROBANTE ENVIADO CORRECTAMENTE'}
                      </p>
                      <p class="font-mono text-[10px] text-steel-400">
                        {PAYMENT_METHOD_LABELS[form.payment_method]} · S/ {parseFloat(form.amount).toFixed(2)}
                        {form.operation_number ? ` · OP. ${form.operation_number}` : ''}
                      </p>
                      <p class="font-mono text-[10px] text-steel-600 mt-0.5">EL PROVEEDOR VERIFICARÁ TU PAGO Y CONFIRMARÁ LA ORDEN.</p>
                    </div>
                  </div>
                {/if}

              </div>
            {/if}

            <!-- Comprobantes de pago subidos -->
            {#if sub.payments && sub.payments.length > 0}
              <div class="border-t border-steel-600/20 px-5 py-4">
                <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-3">// COMPROBANTES DE PAGO</p>
                <div class="space-y-3">
                  {#each sub.payments as proof (proof.id)}
                    <div class="bg-iron-800/50 border border-steel-600/20 px-4 py-3 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div class="space-y-1 flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                          <p class="font-mono text-xs text-bone uppercase tracking-widest">
                            {paymentMethodLabel[proof.payment_method] ?? proof.payment_method}
                          </p>
                          <span class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border {proofStatusBadge[proof.status]}">
                            {proofStatusLabel[proof.status] ?? proof.status_display}
                          </span>
                        </div>
                        <p class="font-mono text-[10px] text-steel-500">
                          {formatCurrency(proof.amount)}
                          {#if proof.operation_number}· OP: {proof.operation_number}{/if}
                        </p>
                        <p class="font-mono text-[10px] text-steel-600">
                          SUBIDO EL {formatDate(proof.uploaded_at)} POR {proof.uploaded_by_name}
                        </p>
                        {#if proof.verified_by_name}
                          <p class="font-mono text-[10px] text-green-400">
                            VERIFICADO POR {proof.verified_by_name}
                            {#if proof.verified_at}· {formatDate(proof.verified_at)}{/if}
                          </p>
                        {/if}
                        {#if proof.status === 'rejected' && proof.rejection_reason}
                          <p class="font-mono text-[10px] text-rust-400">MOTIVO: {proof.rejection_reason}</p>
                        {/if}
                      </div>
                      {#if proof.file}
                        <a
                          href={proof.file}
                          target="_blank"
                          rel="noopener noreferrer"
                          class="font-mono text-[10px] text-rust-500 hover:text-rust-400 uppercase tracking-widest flex-shrink-0 transition-colors"
                        >
                          VER COMPROBANTE →
                        </a>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Aviso pago rechazado residual -->
            {#if sub.payment_rejected && sub.status !== 'pendiente_pago'}
              {@const reason = getLastRejectionReason(sub)}
              <div class="border-t border-rust-700/30 bg-rust-600/10 px-5 py-3 flex items-start gap-3">
                <span class="w-1.5 h-1.5 bg-rust-600 flex-shrink-0 mt-1"></span>
                <div>
                  <p class="font-mono text-[10px] text-rust-400 uppercase tracking-widest">
                    PAGO RECHAZADO — SUBE UN NUEVO COMPROBANTE
                  </p>
                  {#if reason}
                    <p class="font-mono text-[10px] text-steel-400 mt-0.5">MOTIVO: {reason}</p>
                  {/if}
                </div>
              </div>
            {/if}

            <!-- SubOrder expirada -->
            {#if sub.expired}
              <div class="border-t border-steel-600/20 bg-iron-800/30 px-5 py-3">
                <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">
                  ESTA SUB-ORDEN EXPIRÓ SIN RECIBIR PAGO Y FUE CANCELADA.
                </p>
              </div>
            {/if}

          </div>
        {/each}
      </div>

    {:else}
      <!-- Fallback: items directos -->
      <div class="bg-iron-900 border border-steel-600/25"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        <div class="border-b border-steel-600/25 px-5 py-3">
          <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// PRODUCTOS DEL PEDIDO</p>
        </div>
        <div class="divide-y divide-steel-600/15">
          {#each order.items as item (item.id)}
            <div class="flex justify-between items-start gap-4 px-5 py-4">
              <div class="flex-1 min-w-0">
                <p class="font-mono text-xs text-bone truncate">{item.product_name}</p>
                <p class="font-mono text-[10px] text-steel-600 mt-0.5">SKU: {item.product_sku}</p>
                <p class="font-mono text-[10px] text-steel-500">PROVEEDOR: {item.provider_name}</p>
              </div>
              <div class="text-right flex-shrink-0">
                <p class="font-mono text-[10px] text-steel-500">{item.quantity} × {formatCurrency(item.unit_price)}</p>
                <p class="font-mono text-xs text-bone">{formatCurrency(item.subtotal)}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Volver -->
    <div class="mt-8">
      <a href="/cliente/historial-compras" class="btn-ghost font-mono text-[10px] uppercase tracking-widest">
        ← VOLVER AL HISTORIAL DE COMPRAS
      </a>
    </div>

  {/if}
</div>
