<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { cart } from '$lib/store/cart';
  import { auth } from '$lib/store/auth';
  import type { CartItem } from '$lib/store/cart';

  onMount(() => {
    cart.refresh();
  });

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

<svelte:head>
  <title>Carrito — ECOMPARTS</title>
</svelte:head>

<div class="container-responsive py-10">

  <!-- Header -->
  <div class="border-b border-steel-600/25 pb-6 mb-8">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// ORDEN EN CURSO</p>
    <h1 class="font-display text-5xl text-bone uppercase leading-none">CARRITO DE COMPRAS</h1>
  </div>

  {#if cartItems.length === 0}
    <!-- Vacío -->
    <div class="bg-iron-900 border border-steel-600/25 p-16 text-center"
         style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">
      <svg class="w-16 h-16 mx-auto text-steel-700 mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="0.75"
          d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13l-1.4 5h11.8M7 13H5.4M9 21a1 1 0 100-2 1 1 0 000 2zm10 0a1 1 0 100-2 1 1 0 000 2z" />
      </svg>
      <p class="font-display text-4xl text-steel-600 uppercase mb-3">CARRITO VACÍO</p>
      <p class="font-mono text-xs text-steel-700 uppercase tracking-widest mb-8">NO HAY PRODUCTOS EN TU ORDEN</p>
      <a href="/productos"
         class="inline-flex items-center gap-3 font-mono text-xs uppercase tracking-industrial text-bone
                border border-steel-600/60 px-8 py-4 hover:border-rust-600 hover:text-rust-500 transition-colors">
        <span>EXPLORAR CATÁLOGO</span>
        <span>→</span>
      </a>
    </div>

  {:else}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Lista de items -->
      <div class="lg:col-span-2 space-y-3">
        {#each cartItems as item (item.product.id)}
          <div class="bg-iron-900 border {item.is_available === false ? 'border-rust-700/50' : 'border-steel-600/25'}"
               style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
            <div class="p-5 flex items-start gap-5">

              <!-- Info del producto -->
              <div class="flex-1 min-w-0">
                <a href="/productos/{item.product.id}"
                   class="font-display text-xl text-bone uppercase hover:text-rust-400 transition-colors leading-tight block mb-1">
                  {item.product.name}
                </a>
                {#if item.product.reference}
                  <p class="font-mono text-[10px] text-steel-600 uppercase tracking-widest mb-2">
                    REF: {item.product.reference}
                  </p>
                {/if}
                {#if item.is_available === false}
                  <div class="flex items-center gap-2">
                    <span class="w-1.5 h-1.5 bg-rust-600"></span>
                    <p class="font-mono text-[10px] text-rust-500 uppercase tracking-widest">PRODUCTO NO DISPONIBLE</p>
                  </div>
                {/if}
              </div>

              <!-- Controles de cantidad -->
              <div class="flex flex-col items-end gap-3">
                <div class="flex items-center gap-0">
                  <button
                    on:click={() => modificarCantidad(item.product.id, item.cantidad - 1)}
                    disabled={item.cantidad <= 1}
                    class="bg-iron-800 border border-steel-600/50 text-bone font-mono w-9 h-9 flex items-center justify-center
                           hover:border-rust-600 hover:text-rust-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors text-base"
                  >−</button>
                  <div class="w-10 h-9 bg-iron-900 border-y border-steel-600/50 flex items-center justify-center">
                    <span class="font-mono text-sm text-bone">{item.cantidad}</span>
                  </div>
                  <button
                    on:click={() => modificarCantidad(item.product.id, item.cantidad + 1)}
                    class="bg-iron-800 border border-steel-600/50 text-bone font-mono w-9 h-9 flex items-center justify-center
                           hover:border-rust-600 hover:text-rust-500 transition-colors text-base"
                  >+</button>
                </div>

                <!-- Precios -->
                <div class="text-right">
                  <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest">UNIT. / SUBTOTAL</p>
                  <p class="font-mono text-xs text-steel-400">
                    S/. {item.precioUnitario.toFixed(2)} / <span class="text-bone">S/. {item.precioTotal.toFixed(2)}</span>
                  </p>
                </div>

                <!-- Eliminar -->
                <button
                  on:click={() => eliminarProducto(item.product.id)}
                  class="font-mono text-[9px] text-rust-600 hover:text-rust-400 uppercase tracking-widest transition-colors"
                >
                  ✕ ELIMINAR
                </button>
              </div>
            </div>
          </div>
        {/each}

        <!-- Link continuar comprando -->
        <a href="/productos"
           class="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-widest text-steel-500
                  hover:text-rust-500 transition-colors mt-2">
          ← CONTINUAR COMPRANDO
        </a>
      </div>

      <!-- Resumen del pedido -->
      <div class="lg:col-span-1">
        <div class="bg-iron-900 border border-steel-600/25 sticky top-20"
             style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">

          <div class="border-b border-steel-600/25 px-6 py-4">
            <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// RESUMEN DE ORDEN</p>
          </div>

          <div class="p-6 space-y-4">
            <!-- Items -->
            <div class="space-y-2">
              {#each cartItems as item (item.product.id)}
                <div class="flex justify-between items-start gap-2">
                  <span class="font-mono text-[10px] text-steel-400 uppercase flex-1 leading-tight">
                    {item.product.name} ×{item.cantidad}
                  </span>
                  <span class="font-mono text-[10px] text-bone whitespace-nowrap">
                    S/. {item.precioTotal.toFixed(2)}
                  </span>
                </div>
              {/each}
            </div>

            <!-- Total -->
            <div class="border-t border-steel-600/25 pt-4">
              <div class="flex justify-between items-baseline">
                <p class="font-mono text-[10px] text-steel-500 uppercase tracking-widest">TOTAL</p>
                <span class="font-display text-3xl text-rust-600 leading-none">
                  S/. {totalCarrito.toFixed(2)}
                </span>
              </div>
              <p class="font-mono text-[9px] text-steel-700 mt-1 uppercase tracking-widest">INC. IGV</p>
            </div>

            <!-- CTA checkout -->
            <button
              on:click={irAlCheckout}
              class="w-full bg-rust-600 hover:bg-rust-700 text-bone font-display text-lg uppercase tracking-widest
                     py-4 transition-colors mt-2"
              style="clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)"
            >
              FINALIZAR COMPRA →
            </button>
          </div>
        </div>
      </div>

    </div>
  {/if}
</div>
