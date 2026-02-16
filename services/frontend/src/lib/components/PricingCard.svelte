<!--
  COMPONENTE: PricingCard.svelte
  
  ¿QUÉ HACE?
  Muestra una tarjeta con la información de un plan (Starter, Pro, Premium)
  
  ¿CÓMO FUNCIONA?
  - Recibe la información del plan como "prop" (parámetro)
  - Muestra el nombre, precio y características
  - Tiene un botón para seleccionar ese plan
  - Si está seleccionado, se muestra diferente (con border azul)
  
  ANALOGÍA:
  Es como una tarjeta de producto en una tienda online, pero para planes de suscripción
-->

<script lang="ts">
  /**
   * IMPORTS
   * Importamos el tipo TierInfo que definimos en types.ts
   * Esto nos ayuda a que TypeScript verifique que los datos sean correctos
   */
  import type { TierInfo } from '$lib/api/types';
  
  /**
   * PROPS (Parámetros que recibe el componente)
   * 
   * tier: La información del plan (nombre, precio, características)
   * selected: ¿Este plan está seleccionado? (true/false)
   * onSelect: Función que se ejecuta cuando el usuario hace clic en "Seleccionar"
   */
  interface Props {
    tier: TierInfo;         // Información del plan
    selected: boolean;      // ¿Está seleccionado?
    onSelect: () => void;   // Función a ejecutar al hacer clic
  }
  
  // Declaramos las props para que el componente las pueda usar
  let { tier, selected, onSelect }: Props = $props();
</script>

<!--
  HTML DEL COMPONENTE
  
  ESTRUCTURA:
  - Un <div> principal (la tarjeta)
  - Badge de "RECOMENDADO" (si aplica)
  - Nombre del plan
  - Precio
  - Lista de características
  - Botón de selección
-->

<div 
  class="relative rounded-lg border-2 p-6 transition-all hover:shadow-lg
         {selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}"
>
  <!-- Badge "RECOMENDADO" -->
  <!-- Se muestra SOLO si tier.recommended es true -->
  {#if tier.recommended}
    <div class="absolute -top-3 left-1/2 -translate-x-1/2">
      <span class="bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
        RECOMENDADO
      </span>
    </div>
  {/if}
  
  <!-- Nombre del plan -->
  <h3 class="text-xl font-bold text-gray-900 mb-2">
    {tier.name}
  </h3>
  
  <!-- Precio -->
  <div class="mb-4">
    {#if tier.price === 0}
      <!-- Si el precio es 0, mostrar "GRATIS" -->
      <span class="text-4xl font-bold text-gray-900">GRATIS</span>
    {:else}
      <!-- Si tiene precio, mostrar con formato S/ -->
      <span class="text-4xl font-bold text-gray-900">S/ {tier.price}</span>
      <span class="text-gray-600">/mes</span>
    {/if}
  </div>
  
  <!-- Línea separadora -->
  <div class="border-t border-gray-200 my-4"></div>
  
  <!-- Lista de características -->
  <ul class="space-y-3 mb-6">
    <!-- Iteramos sobre cada característica del plan -->
    {#each tier.features as feature}
      <li class="flex items-start">
        <!-- Icono de check (✓) -->
        <svg 
          class="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" 
          fill="currentColor" 
          viewBox="0 0 20 20"
        >
          <path 
            fill-rule="evenodd" 
            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" 
            clip-rule="evenodd"
          />
        </svg>
        <!-- Texto de la característica -->
        <span class="text-gray-700">{feature}</span>
      </li>
    {/each}
  </ul>
  
  <!-- Botón de selección -->
  <button
    type="button"
    onclick={onSelect}
    class="w-full py-3 px-4 rounded-lg font-medium transition-colors
           {selected 
             ? 'bg-blue-500 text-white hover:bg-blue-600' 
             : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}"
  >
    {selected ? '✓ Seleccionado' : 'Seleccionar'}
  </button>
</div>

<!--
  ESTILOS (opcional)
  
  En este caso usamos Tailwind CSS directamente en las clases,
  así que no necesitamos un bloque <style>
-->