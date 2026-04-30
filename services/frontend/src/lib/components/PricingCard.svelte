<script lang="ts">
  import type { TierInfo } from '$lib/api/types';

  interface Props {
    tier: TierInfo;
    selected: boolean;
    onSelect: () => void;
  }

  let { tier, selected, onSelect }: Props = $props();
</script>

<div
  class="relative bg-iron-900 border transition-all duration-150 p-6
         {selected ? 'border-rust-600' : 'border-steel-600/25 hover:border-steel-400'}"
  style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)"
>
  <!-- Badge RECOMENDADO -->
  {#if tier.recommended}
    <div class="absolute -top-3 left-5">
      <span class="font-mono text-[9px] uppercase tracking-widest bg-rust-600 text-bone px-3 py-1">
        RECOMENDADO
      </span>
    </div>
  {/if}

  <!-- Nombre del plan -->
  <h3 class="font-display text-3xl {selected ? 'text-rust-600' : 'text-bone'} uppercase leading-none mb-4">
    {tier.name}
  </h3>

  <!-- Precio -->
  <div class="mb-5">
    {#if tier.price === 0}
      <span class="font-display text-4xl text-bone">GRATIS</span>
    {:else}
      <span class="font-display text-4xl text-bone">S/. {tier.price}</span>
      <span class="font-mono text-xs text-steel-500 ml-1 uppercase">/MES</span>
    {/if}
  </div>

  <!-- Separador -->
  <div class="border-t border-steel-600/25 my-4"></div>

  <!-- Características -->
  <ul class="space-y-2.5 mb-6">
    {#each tier.features as feature}
      <li class="flex items-start gap-2.5">
        <svg class="w-4 h-4 text-rust-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span class="font-mono text-xs text-steel-400 leading-relaxed">{feature}</span>
      </li>
    {/each}
  </ul>

  <!-- Botón -->
  <button
    type="button"
    onclick={onSelect}
    class="w-full font-mono text-xs uppercase tracking-industrial py-3 px-4 transition-all duration-150
           {selected
             ? 'bg-rust-600 text-bone border border-rust-600 hover:bg-rust-700'
             : 'bg-transparent text-steel-300 border border-steel-600/50 hover:border-rust-600 hover:text-rust-500'}"
  >
    {selected ? '✓ SELECCIONADO' : 'SELECCIONAR PLAN'}
  </button>
</div>
