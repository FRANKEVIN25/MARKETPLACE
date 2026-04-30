<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { onMount } from 'svelte';
  import type { Order, OrderStatus } from '$lib/api/types';

  let orders: Order[] = [];
  let loading = true;
  let error = '';

  const statusLabel: Record<OrderStatus, string> = {
    pendiente_pago: 'PENDIENTE DE PAGO',
    pagado: 'PAGADO',
    procesando: 'PROCESANDO',
    enviado: 'ENVIADO',
    completado: 'COMPLETADO',
    cancelado: 'CANCELADO',
  };

  const statusColor: Record<OrderStatus, string> = {
    pendiente_pago: 'border-yellow-700/50 text-yellow-400',
    pagado: 'border-steel-600/50 text-steel-300',
    procesando: 'border-rust-700/50 text-rust-400',
    enviado: 'border-steel-600/50 text-bone',
    completado: 'border-green-700/50 text-green-400',
    cancelado: 'border-rust-700/50 text-rust-500',
  };

  const deliveryLabel: Record<string, string> = {
    domicilio: 'ENVÍO A DOMICILIO',
    agencia: 'RECOJO EN AGENCIA',
    tienda: 'RECOJO EN TIENDA',
  };

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  function formatCurrency(value: string | number): string {
    return `S/. ${parseFloat(String(value)).toFixed(2)}`;
  }

  onMount(async () => {
    const token = auth.getAccessToken();
    if (!token) {
      window.location.href = '/login';
      return;
    }
    try {
      orders = await api.orders.getOrders(token);
      orders.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } catch (e) {
      error = 'No se pudo cargar el historial de compras.';
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>Historial de Compras — ECOMPARTS</title>
</svelte:head>

<div class="container-responsive py-10 max-w-4xl">

  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8 flex items-start justify-between gap-4">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// MI CUENTA / PEDIDOS</p>
      <h1 class="font-display text-5xl text-bone uppercase leading-none">HISTORIAL DE COMPRAS</h1>
      <p class="font-mono text-xs text-steel-500 mt-2 uppercase tracking-widest">Estado de todos tus pedidos</p>
    </div>
    <a href="/cliente/perfil" class="btn-ghost shrink-0 font-mono text-[10px] uppercase tracking-widest mt-1">
      ← MI CUENTA
    </a>
  </div>

  {#if loading}
    <div class="flex flex-col items-center justify-center py-24 gap-4">
      <svg class="animate-spin h-8 w-8 text-rust-600" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      <p class="font-mono text-xs text-steel-500 uppercase tracking-widest animate-pulse">CARGANDO PEDIDOS...</p>
    </div>

  {:else if error}
    <div class="border border-rust-700/50 bg-rust-600/10 p-6 text-center">
      <p class="font-mono text-xs text-rust-400">{error}</p>
    </div>

  {:else if orders.length === 0}
    <div class="bg-iron-900 border border-steel-600/25 p-16 text-center"
         style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
      <svg class="h-16 w-16 mx-auto mb-5 text-steel-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="0.75"
          d="M9 17v-2a4 4 0 014-4h0a4 4 0 014 4v2M3 17v-2a4 4 0 014-4h4m0 0V7a3 3 0 10-6 0v6h6z"/>
      </svg>
      <p class="font-display text-3xl text-steel-600 uppercase mb-2">SIN PEDIDOS</p>
      <p class="font-mono text-xs text-steel-700 uppercase tracking-widest mb-8">AÚN NO TIENES PEDIDOS REGISTRADOS</p>
      <a href="/productos" class="btn-rust">EXPLORAR CATÁLOGO →</a>
    </div>

  {:else}
    <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest mb-5">
      {orders.length} PEDIDO{orders.length !== 1 ? 'S' : ''} REGISTRADO{orders.length !== 1 ? 'S' : ''}
    </p>

    <div class="space-y-3">
      {#each orders as order (order.id)}
        <a
          href="/cliente/historial-compras/{order.id}"
          class="block bg-iron-900 border border-steel-600/25 hover:border-steel-600/50 transition-colors group"
          style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)"
        >
          <div class="border-b border-steel-600/20 px-5 py-3 flex items-center justify-between gap-3 flex-wrap">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">
              // ORDEN {order.order_number}
            </p>
            <span class="font-mono text-[9px] uppercase tracking-widest px-2 py-0.5 border {statusColor[order.status]}">
              {statusLabel[order.status]}
            </span>
          </div>

          <div class="px-5 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div class="space-y-1">
              <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">
                {formatDate(order.created_at)} — {deliveryLabel[order.delivery_method] ?? order.delivery_method}
              </p>
              <p class="font-mono text-[10px] text-steel-600">
                {order.provider_count} PROVEEDOR{order.provider_count !== 1 ? 'ES' : ''}
                · {order.items.length} PRODUCTO{order.items.length !== 1 ? 'S' : ''}
              </p>
            </div>
            <div class="flex items-center gap-4">
              <span class="font-display text-2xl text-bone leading-none group-hover:text-rust-400 transition-colors">
                {formatCurrency(order.total)}
              </span>
              <svg class="h-5 w-5 text-steel-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>
