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

  // -------------------------------------------------------------------
  // Helpers de UI
  // -------------------------------------------------------------------
  const orderStatusLabel: Record<OrderStatus, string> = {
    pendiente_pago: 'Pendiente de pago',
    pagado: 'Pagado',
    procesando: 'Procesando',
    enviado: 'Enviado',
    completado: 'Completado',
    cancelado: 'Cancelado',
  };

  const orderStatusColor: Record<OrderStatus, string> = {
    pendiente_pago: 'bg-yellow-100 text-yellow-800 border border-yellow-200',
    pagado: 'bg-blue-100 text-blue-800 border border-blue-200',
    procesando: 'bg-indigo-100 text-indigo-800 border border-indigo-200',
    enviado: 'bg-purple-100 text-purple-800 border border-purple-200',
    completado: 'bg-green-100 text-green-800 border border-green-200',
    cancelado: 'bg-red-100 text-red-800 border border-red-200',
  };

  const subOrderStatusLabel: Record<SubOrderStatus, string> = {
    pendiente_pago:   'Pendiente de pago',
    pago_en_revision: 'Pago en revisión',
    pagado:           'Pago confirmado',
    confirmado:       'Confirmado',
    enviado:          'Enviado',
    entregado:        'Entregado',
    cancelado:        'Cancelado',
  };

  const subOrderStatusColor: Record<SubOrderStatus, string> = {
    pendiente_pago:   'bg-yellow-50 text-yellow-700 border border-yellow-200',
    pago_en_revision: 'bg-orange-50 text-orange-700 border border-orange-200',
    pagado:           'bg-blue-50 text-blue-700 border border-blue-200',
    confirmado:       'bg-indigo-50 text-indigo-700 border border-indigo-200',
    enviado:          'bg-purple-50 text-purple-700 border border-purple-200',
    entregado:        'bg-green-50 text-green-700 border border-green-200',
    cancelado:        'bg-gray-100 text-gray-600 border border-gray-200',
  };

  const proofStatusBadge: Record<'uploaded' | 'approved' | 'rejected', string> = {
    uploaded: 'bg-yellow-50 text-yellow-700 border border-yellow-200',
    approved: 'bg-green-50 text-green-700 border border-green-200',
    rejected: 'bg-red-50 text-red-700 border border-red-200',
  };

  const proofStatusLabel: Record<'uploaded' | 'approved' | 'rejected', string> = {
    uploaded: 'En revisión',
    approved: 'Aprobado ✓',
    rejected: 'Rechazado ×',
  };

  const deliveryLabel: Record<string, string> = {
    domicilio: 'Envío a domicilio',
    agencia: 'Recojo en agencia',
    tienda: 'Recojo en tienda',
  };

  const paymentMethodLabel: Record<string, string> = {
    transferencia: 'Transferencia bancaria',
    yape: 'Yape',
    plin: 'Plin',
    efectivo_contraentrega: 'Efectivo contraentrega',
    efectivo_tienda: 'Efectivo en tienda',
  };

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'long',
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
        countdown = '⏰ Tiempo expirado';
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

  // True si alguna SubOrder está genuinamente en pendiente_pago (no expirada, no cancelada)
  $: hasTrulyPending = (order?.sub_orders ?? []).some(
    s => s.status === 'pendiente_pago' && !s.expired
  );

  // Cuando el Order dice pendiente_pago pero todas las subórdenes ya subieron comprobante
  $: allInRevisionOrBeyond =
    order?.status === 'pendiente_pago' &&
    !hasTrulyPending &&
    (order?.sub_orders ?? []).some(s => s.status === 'pago_en_revision');

  $: if (order?.payment_deadline && hasTrulyPending) {
    startCountdown(order.payment_deadline);
  }

  // Detener el timer cuando ya no queden pagos genuinamente pendientes
  $: if (!hasTrulyPending && countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
    countdown = '';
  }

  onDestroy(() => { if (countdownInterval) clearInterval(countdownInterval); });

  /** Devuelve el motivo del rechazo más reciente desde el historial de comprobantes */
  function getLastRejectionReason(sub: SubOrder): string {
    if (!sub.payment_rejected || !sub.payments?.length) return '';
    const rejected = sub.payments
      .filter(p => p.status === 'rejected')
      .sort((a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime());
    return rejected[0]?.rejection_reason ?? '';
  }

  /** Construye el resumen de métodos de pago del proveedor */
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
    transferencia: 'Transferencia bancaria',
    yape: 'Yape',
    plin: 'Plin',
    efectivo_contraentrega: 'Efectivo contraentrega',
    efectivo_tienda: 'Efectivo en tienda',
  };

  $: if (order) {
    for (const sub of order.sub_orders) {
      if (
        (sub.status === 'pendiente_pago' || sub.payment_rejected) &&
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
      // Recargar la orden para reflejar el nuevo status
      order = await api.orders.getOrder(token, order!.id);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Error al subir el comprobante.';
      proofForms[sub.id] = { ...proofForms[sub.id], uploading: false, error: msg };
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
  <title>{order ? `Pedido ${order.order_number}` : 'Detalle de Pedido'} - ECOMPARTS</title>
</svelte:head>

<div class="max-w-4xl mx-auto py-12 px-4">
  <!-- Breadcrumb -->
  <nav class="flex items-center gap-2 text-sm text-gray-400 mb-8">
    <a href="/cliente/perfil" class="hover:text-blue-600 transition">Mi cuenta</a>
    <span>›</span>
    <a href="/cliente/historial-compras" class="hover:text-blue-600 transition">Historial de compras</a>
    <span>›</span>
    <span class="text-gray-600 font-medium">
      {order ? order.order_number : 'Cargando...'}
    </span>
  </nav>

  <!-- Estado de carga -->
  {#if loading}
    <div class="flex flex-col items-center justify-center py-24 text-gray-400">
      <svg
        class="animate-spin h-8 w-8 mb-3 text-blue-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v8H4z"
        />
      </svg>
      Cargando pedido...
    </div>

  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 rounded-lg p-6 text-center">
      {error}
      <div class="mt-4">
        <a href="/cliente/historial-compras" class="text-sm font-medium text-red-700 underline">
          ← Volver al historial
        </a>
      </div>
    </div>

  {:else if order}
    <!-- ================================================================
         ENCABEZADO DE LA ORDEN
    ================================================================ -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
      <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div class="flex items-center gap-3 flex-wrap mb-1">
            <h1 class="text-xl font-bold text-gray-900 font-mono">
              {order.order_number}
            </h1>
            <!-- Si ya están todos en revisión pero el Order aún dice pendiente_pago, mostrar badge correcto -->
            {#if allInRevisionOrBeyond}
              <span class="text-sm font-medium px-2.5 py-0.5 rounded-full bg-orange-100 text-orange-800 border border-orange-200">
                Pago en revisión
              </span>
            {:else}
              <span class="text-sm font-medium px-2.5 py-0.5 rounded-full {orderStatusColor[order.status]}">
                {orderStatusLabel[order.status]}
              </span>
            {/if}
          </div>
          <p class="text-sm text-gray-500">
            Realizado el {formatDate(order.created_at)}
          </p>
          {#if order.payment_deadline && hasTrulyPending}
            <p class="text-sm mt-1 font-medium text-amber-600">
              ⌛ Tiempo para pagar: {countdown || '...'}
            </p>
          {/if}
          {#if order.customer_notes}
            <p class="text-sm text-gray-500 mt-1 italic">
              Nota: {order.customer_notes}
            </p>
          {/if}
        </div>

        <!-- Totales -->
        <div class="text-right min-w-[160px] space-y-1">
          <div class="flex justify-between gap-6 text-sm text-gray-500">
            <span>Subtotal</span>
            <span>{formatCurrency(order.subtotal)}</span>
          </div>
          {#if parseFloat(order.discount) > 0}
            <div class="flex justify-between gap-6 text-sm text-green-600">
              <span>Descuento</span>
              <span>-{formatCurrency(order.discount)}</span>
            </div>
          {/if}
          <div class="flex justify-between gap-6 text-sm text-gray-500">
            <span>IGV</span>
            <span>{formatCurrency(order.tax)}</span>
          </div>
          <div class="flex justify-between gap-6 font-bold text-gray-900 border-t border-gray-100 pt-1">
            <span>Total</span>
            <span class="text-blue-700">{formatCurrency(order.total)}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================
         ENTREGA
    ================================================================ -->
    <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
      <h2 class="text-base font-semibold text-gray-800 mb-3">Entrega</h2>
      <div class="flex items-start gap-3">
        <svg
          class="h-5 w-5 text-blue-500 mt-0.5 flex-shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path
            fill-rule="evenodd"
            d="M11.54 22.351l.07.04.028.016a.76.76 0 00.723 0l.028-.015.071-.041a16.975 16.975 0 001.144-.742 19.58 19.58 0 002.683-2.282c1.944-2.013 3.5-4.697 3.5-8.327a8 8 0 10-16 0c0 3.63 1.556 6.314 3.5 8.327a19.579 19.579 0 002.682 2.282 16.975 16.975 0 001.145.742zM12 13.5a3 3 0 100-6 3 3 0 000 6z"
            clip-rule="evenodd"
          />
        </svg>
        <div>
          <p class="text-sm font-medium text-gray-800">
            {deliveryLabel[order.delivery_method] ?? order.delivery_method}
          </p>
          {#if order.shipping_address_detail}
            <p class="text-sm text-gray-600 mt-0.5">
              {order.shipping_address_detail.contact_name} ·
              {order.shipping_address_detail.contact_phone}
            </p>
            <p class="text-sm text-gray-500">
              {order.shipping_address_detail.full_address}
            </p>
            {#if order.shipping_address_detail.reference}
              <p class="text-xs text-gray-400 mt-0.5">
                Ref: {order.shipping_address_detail.reference}
              </p>
            {/if}
          {:else}
            <p class="text-sm text-gray-500">Sin dirección registrada</p>
          {/if}
        </div>
      </div>
    </div>

    <!-- ================================================================
         SUB-ÓRDENES POR PROVEEDOR
    ================================================================ -->
    {#if order.sub_orders && order.sub_orders.length > 0}
      <div class="space-y-6">
        {#each order.sub_orders as sub (sub.id)}
          <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <!-- Encabezado sub-orden -->
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 px-6 py-4 bg-gray-50 border-b border-gray-100">
              <div>
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-sm font-semibold text-gray-800">
                    {sub.provider_name}
                  </span>
                  <span class="text-xs font-mono text-gray-400">
                    #{sub.sub_order_number}
                  </span>
                  <span class="text-xs font-medium px-2 py-0.5 rounded-full {subOrderStatusColor[sub.status]}">
                    {subOrderStatusLabel[sub.status]}
                  </span>
                </div>
                {#if sub.tracking_number}
                  <p class="text-xs text-gray-500 mt-0.5">
                    Tracking: <span class="font-mono">{sub.tracking_number}</span>
                  </p>
                {/if}
              </div>
              <div class="text-right">
                <p class="text-sm font-bold text-gray-900">{formatCurrency(sub.total)}</p>
                <p class="text-xs text-gray-400">IGV incl.</p>
              </div>
            </div>

            <!-- Items de la sub-orden -->
            <div class="divide-y divide-gray-50">
              {#each sub.items as item (item.id)}
                <div class="flex justify-between items-start gap-4 px-6 py-4">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">
                      {item.product_name}
                    </p>
                    <p class="text-xs text-gray-400 mt-0.5 font-mono">
                      SKU: {item.product_sku}
                    </p>
                  </div>
                  <div class="text-right flex-shrink-0 space-y-0.5">
                    <p class="text-sm text-gray-600">
                      {item.quantity} × {formatCurrency(item.unit_price)}
                    </p>
                    <p class="text-sm font-semibold text-gray-900">
                      {formatCurrency(item.subtotal)}
                    </p>
                    {#if parseFloat(item.discount) > 0}
                      <p class="text-xs text-green-600">
                        Desc: -{formatCurrency(item.discount)}
                      </p>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>

            <!-- Desglose de la sub-orden -->
            <div class="px-6 py-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-500 flex flex-wrap gap-x-6 gap-y-1">
              <span>Subtotal: {formatCurrency(sub.subtotal)}</span>
              <span>IGV ({parseFloat(sub.igv_rate) * 100}%): {formatCurrency(sub.igv_amount)}</span>
              <span class="font-semibold text-gray-700">Total: {formatCurrency(sub.total)}</span>
            </div>

            <!-- Pago pendiente: datos bancarios + formulario de comprobante -->
            {#if sub.status === 'pendiente_pago' && !sub.expired}
              {@const pay = sub.provider_payment_info}
              {@const form = proofForms[sub.id]}

              <!-- Alerta pago rechazado -->
              {#if sub.payment_rejected}
                {@const reason = getLastRejectionReason(sub)}
                <div class="px-6 py-3 bg-red-50 border-t border-red-100">
                  <p class="text-sm font-semibold text-red-700">
                    ⚠️ Tu pago fue rechazado. Por favor sube un nuevo comprobante.
                  </p>
                  {#if reason}
                    <p class="text-sm text-red-600 mt-0.5">Motivo: {reason}</p>
                  {/if}
                </div>
              {/if}

              <div class="px-6 py-5 border-t border-gray-100 space-y-5">

                <!-- Datos bancarios del proveedor -->
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

                <!-- Formulario de comprobante -->
                {#if form && !form.uploaded}
                  <div class="space-y-4">
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
                              ? 'border-blue-500 bg-blue-50 text-blue-700'
                              : 'border-gray-200 hover:border-gray-300 text-gray-600'}"
                          on:click={() => { proofForms[sub.id] = { ...form, payment_method: m.value as PaymentMethod }; }}
                        >{m.icon} {m.label}</button>
                      {/each}
                    </div>

                    <!-- Monto y número de operación -->
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label for="hist-amount-{sub.id}" class="block text-xs text-gray-500 mb-1">Monto pagado (S/) *</label>
                        <input
                          id="hist-amount-{sub.id}"
                          type="number" step="0.01" min="0.01"
                          bind:value={proofForms[sub.id].amount}
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                                 focus:outline-none focus:ring-2 focus:ring-blue-400" />
                      </div>
                      <div>
                        <label for="hist-opnum-{sub.id}" class="block text-xs text-gray-500 mb-1">N° de operación</label>
                        <input
                          id="hist-opnum-{sub.id}"
                          type="text"
                          bind:value={proofForms[sub.id].operation_number}
                          placeholder="Ej: 123456789"
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                                 focus:outline-none focus:ring-2 focus:ring-blue-400" />
                      </div>
                    </div>

                    <!-- Adjuntar archivo -->
                    <div>
                      <label for="hist-file-{sub.id}" class="block text-xs text-gray-500 mb-1">
                        Captura / voucher * (JPG, PNG, PDF)
                      </label>
                      <label for="hist-file-{sub.id}"
                        class="flex flex-col items-center justify-center w-full border-2 border-dashed
                               rounded-xl cursor-pointer py-5 transition-colors
                               {form.file
                                 ? 'border-green-400 bg-green-50'
                                 : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50/30'}">
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
                        id="hist-file-{sub.id}"
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
                      class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-40
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
                {/if}

              </div>
            {/if}

            <!-- Comprobantes de pago subidos -->
            {#if sub.payments && sub.payments.length > 0}
              <div class="px-6 py-4 border-t border-gray-100">
                <p class="text-sm font-semibold text-gray-700 mb-3">Comprobantes de pago</p>
                <div class="space-y-3">
                  {#each sub.payments as proof (proof.id)}
                    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 bg-gray-50 rounded-lg p-3 text-sm">
                      <div class="space-y-0.5 flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                          <p class="font-medium text-gray-800">
                            {paymentMethodLabel[proof.payment_method] ?? proof.payment_method}
                          </p>
                          <span class="text-xs font-medium px-1.5 py-0.5 rounded-full {proofStatusBadge[proof.status]}">
                            {proofStatusLabel[proof.status] ?? proof.status_display}
                          </span>
                        </div>
                        <p class="text-gray-500 text-xs">
                          {formatCurrency(proof.amount)}
                          {#if proof.operation_number}
                            · Op: {proof.operation_number}
                          {/if}
                        </p>
                        <p class="text-gray-400 text-xs">
                          Subido el {formatDate(proof.uploaded_at)}
                          por {proof.uploaded_by_name}
                        </p>
                        {#if proof.verified_by_name}
                          <p class="text-xs text-green-600">
                            ✓ Verificado por {proof.verified_by_name}
                            {#if proof.verified_at}
                              el {formatDate(proof.verified_at)}
                            {/if}
                          </p>
                        {/if}
                        {#if proof.status === 'rejected' && proof.rejection_reason}
                          <p class="text-xs text-red-600 italic">
                            Motivo: {proof.rejection_reason}
                          </p>
                        {/if}
                      </div>
                      {#if proof.file}
                        <a
                          href={proof.file}
                          target="_blank"
                          rel="noopener noreferrer"
                          class="text-xs font-medium text-blue-600 hover:underline flex-shrink-0"
                        >
                          Ver comprobante →
                        </a>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Aviso pago rechazado (solo si NO está en pendiente_pago, es decir ya tiene otro estado pero el flag quedó) -->
            {#if sub.payment_rejected && sub.status !== 'pendiente_pago'}
              {@const reason = getLastRejectionReason(sub)}
              <div class="px-6 py-3 bg-red-50 border-t border-red-100">
                <p class="text-sm font-semibold text-red-700">
                  ⚠️ Tu pago fue rechazado. Por favor sube un nuevo comprobante.
                </p>
                {#if reason}
                  <p class="text-sm text-red-600 mt-0.5">
                    Motivo: {reason}
                  </p>
                {/if}
              </div>
            {/if}

            <!-- SubOrder expirada -->
            {#if sub.expired}
              <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
                ⏰ Esta sub-orden expiró sin recibir pago y fue cancelada.
              </div>
            {/if}
          </div>
        {/each}
      </div>

    {:else}
      <!-- Fallback: mostrar items directamente -->
      <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="px-6 py-4 bg-gray-50 border-b border-gray-100">
          <h2 class="text-sm font-semibold text-gray-700">Productos del pedido</h2>
        </div>
        <div class="divide-y divide-gray-50">
          {#each order.items as item (item.id)}
            <div class="flex justify-between items-start gap-4 px-6 py-4">
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">{item.product_name}</p>
                <p class="text-xs text-gray-400 font-mono">SKU: {item.product_sku}</p>
                <p class="text-xs text-gray-500 mt-0.5">Proveedor: {item.provider_name}</p>
              </div>
              <div class="text-right flex-shrink-0">
                <p class="text-sm text-gray-600">{item.quantity} × {formatCurrency(item.unit_price)}</p>
                <p class="text-sm font-semibold text-gray-900">{formatCurrency(item.subtotal)}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Volver -->
    <div class="mt-8">
      <a
        href="/cliente/historial-compras"
        class="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
      >
        ← Volver al historial de compras
      </a>
    </div>
  {/if}
</div>
