<script lang="ts">
  import { goto } from '$app/navigation';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';
  import type { CartItem } from '$lib/store/cart';

  $: cartItems = $cart;
  $: totalCarrito = cartItems.reduce((acc, item) => acc + item.precioTotal, 0);

  function modificarCantidad(productId: number, nuevaCantidad: number) {
    cart.updateCantidad(productId, nuevaCantidad);
  }

  function eliminarProducto(productId: number) {
    cart.removeItem(productId);
  }

  function irAlCheckout() {
    const token = auth.getAccessToken();
    if (!token) {
      goto('/login');
      return;
    }
    goto('/ordenes/checkout');
  }
</script>

<div class="max-w-4xl mx-auto py-12">
  <h1 class="text-3xl font-bold mb-8">Carrito de Compras</h1>

  {#if cartItems.length === 0}
    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
      Tu carrito está vacío.
    </div>
  {:else}
    <div class="bg-white rounded-lg shadow p-8">
      <table class="w-full text-left">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Cantidad</th>
            <th>Precio Unitario</th>
            <th>Subtotal</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {#each cartItems as item}
            <tr>
              <td>
                <div class="font-semibold">{item.product.name}</div>
                <div class="text-sm text-gray-500">{item.product.reference}</div>
                {#if !item.stockDisponible || item.cantidad > item.stockDisponible}
                  <div class="text-xs text-red-600 mt-1">Stock insuficiente</div>
                {/if}
              </td>
              <td>
                <div class="flex items-center gap-2">
                  <button
                    on:click={() => modificarCantidad(item.product.id, item.cantidad - 1)}
                    disabled={item.cantidad <= 1}
                    class="bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-1 rounded"
                  >-</button>
                  <input
                    type="number"
                    min="1"
                    max={item.stockDisponible}
                    bind:value={item.cantidad}
                    on:change={() => modificarCantidad(item.product.id, item.cantidad)}
                    class="w-16 text-center border border-gray-300 rounded"
                  />
                  <button
                    on:click={() => modificarCantidad(item.product.id, item.cantidad + 1)}
                    disabled={item.cantidad >= item.stockDisponible}
                    class="bg-gray-200 hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-1 rounded"
                  >+</button>
                </div>
                <div class="text-xs text-gray-500 mt-1">Máx. {item.stockDisponible} unidades</div>
              </td>
              <td>S/. {item.precioUnitario.toFixed(2)}</td>
              <td>S/. {item.precioTotal.toFixed(2)}</td>
              <td>
                <button
                  on:click={() => eliminarProducto(item.product.id)}
                  class="text-red-600 hover:text-red-800 font-bold"
                >Eliminar</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
      <div class="mt-8 flex justify-between items-center">
        <div class="text-xl font-bold">Total: S/. {totalCarrito.toFixed(2)}</div>
        <button
          on:click={irAlCheckout}
          class="bg-primary-600 hover:bg-primary-700 text-white font-bold py-3 px-6 rounded-lg transition text-lg"
        >Finalizar Compra →</button>
      </div>
    </div>
  {/if}
</div>
