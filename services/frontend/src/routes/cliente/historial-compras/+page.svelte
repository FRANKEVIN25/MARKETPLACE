<script lang="ts">
  import { auth } from '$lib/store/auth';
  import { api } from '$lib/api/client';
  import { onMount } from 'svelte';
  import type { Order, OrderStatus } from '$lib/api/types';

  let orders: Order[] = [];
  let loading = true;
  let error = '';

  // -------------------------------------------------------------------
  // Helpers de UI
  // -------------------------------------------------------------------
  const statusLabel: Record<OrderStatus, string> = {
    pendiente_pago: 'Pendiente de pago',
    pagado: 'Pagado',
    procesando: 'Procesando',
    enviado: 'Enviado',
    completado: 'Completado',
    cancelado: 'Cancelado',
  };

  const statusColor: Record<OrderStatus, string> = {
    pendiente_pago:
      'bg-yellow-100 text-yellow-800 border border-yellow-200',
    pagado:
      'bg-blue-100 text-blue-800 border border-blue-200',
    procesando:
      'bg-indigo-100 text-indigo-800 border border-indigo-200',
    enviado:
      'bg-purple-100 text-purple-800 border border-purple-200',
    completado:
      'bg-green-100 text-green-800 border border-green-200',
    cancelado:
      'bg-red-100 text-red-800 border border-red-200',
  };

  const deliveryLabel: Record<string, string> = {
    domicilio: 'Envío a domicilio',
    agencia: 'Recojo en agencia',
    tienda: 'Recojo en tienda',
  };

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  function formatCurrency(value: string | number): string {
    return `S/ ${parseFloat(String(value)).toFixed(2)}`;
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
    try {
      orders = await api.orders.getOrders(token);
      // Ordenar por fecha descendente
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
  <title>Historial de Compras - ECOMPARTS</title>
</svelte:head>

<div class="max-w-4xl mx-auto py-12 px-4">
  <!-- Encabezado -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-3xl font-bold text-gray-900">Historial de Compras</h1>
      <p class="text-gray-500 mt-1">Revisa el estado de todos tus pedidos</p>
    </div>
    <a
      href="/cliente/perfil"
      class="text-sm text-blue-600 hover:underline flex items-center gap-1"
    >
      ← Mi cuenta
    </a>
  </div>

  <!-- Estado de carga -->
  {#if loading}
    <div class="flex flex-col items-center justify-center py-24 text-gray-400">
      <svg
        class="animate-spin h-8 w-8 mb-3 text-blue-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v8H4z"
        />
      </svg>
      Cargando pedidos...
    </div>

  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 rounded-lg p-6 text-center">
      {error}
    </div>

  {:else if orders.length === 0}
    <div class="flex flex-col items-center justify-center py-24 text-gray-400">
      <svg
        class="h-16 w-16 mb-4 text-gray-300"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1.5"
          d="M9 17v-2a4 4 0 014-4h0a4 4 0 014 4v2M3 17v-2a4 4 0 014-4h4m0 0V7a3 3 0 10-6 0v6h6z"
        />
      </svg>
      <p class="text-lg font-medium">Aún no tienes pedidos</p>
      <a
        href="/productos"
        class="mt-4 inline-block bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-6 py-2 rounded-lg transition"
      >
        Explorar productos
      </a>
    </div>

  {:else}
    <!-- Contador -->
    <p class="text-sm text-gray-500 mb-4">
      {orders.length} pedido{orders.length !== 1 ? 's' : ''} registrado{orders.length !== 1 ? 's' : ''}
    </p>

    <!-- Lista de órdenes -->
    <div class="space-y-4">
      {#each orders as order (order.id)}
        <a
          href="/cliente/historial-compras/{order.id}"
          class="block bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md hover:border-blue-200 transition p-6"
        >
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <!-- Info principal -->
            <div class="space-y-1">
              <div class="flex items-center gap-3 flex-wrap">
                <span class="font-mono font-semibold text-gray-900 text-sm">
                  {order.order_number}
                </span>
                <span
                  class="text-xs font-medium px-2.5 py-0.5 rounded-full {statusColor[order.status]}"
                >
                  {statusLabel[order.status]}
                </span>
              </div>
              <p class="text-xs text-gray-400">
                {formatDate(order.created_at)} · {deliveryLabel[order.delivery_method] ?? order.delivery_method}
              </p>
              <p class="text-xs text-gray-500">
                {order.provider_count} proveedor{order.provider_count !== 1 ? 'es' : ''}
                · {order.items.length} producto{order.items.length !== 1 ? 's' : ''}
              </p>
            </div>

            <!-- Total y flecha -->
            <div class="flex items-center gap-4">
              <span class="text-lg font-bold text-gray-900">
                {formatCurrency(order.total)}
              </span>
              <svg
                class="h-5 w-5 text-gray-400 flex-shrink-0"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
                  clip-rule="evenodd"
                />
              </svg>
            </div>
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>
