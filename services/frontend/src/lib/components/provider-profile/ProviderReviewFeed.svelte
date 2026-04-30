<script lang="ts">
  import type { ProviderReview } from '$lib/api/types';

  export let reviews: ProviderReview[] = [];

  function formatDate(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;

    return new Intl.DateTimeFormat('es-PE', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(date);
  }

  function stars(rating: number): string[] {
    return Array.from({ length: 5 }, (_, index) => (index < rating ? 'filled' : 'empty'));
  }
</script>

<div class="bg-iron-900 border border-steel-600/25"
     style="clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)">
  <div class="border-b border-steel-600/25 px-6 py-4 flex flex-wrap items-start justify-between gap-3">
    <div>
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-1">// REVIEWS</p>
      <h2 class="font-display text-3xl text-bone uppercase leading-none">LO QUE DICEN LOS CLIENTES</h2>
    </div>
    <p class="font-mono text-[10px] text-steel-500 max-w-xs leading-relaxed">
      SOLO RESEÑAS VISIBLES DE SUBÓRDENES ENTREGADAS.
    </p>
  </div>

  {#if reviews.length === 0}
    <div class="p-8 text-center">
      <p class="font-mono text-xs text-steel-600 uppercase tracking-widest">SIN RESEÑAS PUBLICADAS AÚN</p>
    </div>
  {:else}
    <div class="p-5 grid gap-4 lg:grid-cols-2">
      {#each reviews as review}
        <div class="bg-iron-800/50 border border-steel-600/20 p-5">
          <div class="flex items-start justify-between gap-3 mb-3">
            <div>
              <p class="font-mono text-xs text-bone">{review.customer_name}</p>
              <p class="font-mono text-[9px] text-steel-600 uppercase">{review.sub_order_number}</p>
            </div>
            <p class="font-mono text-[9px] text-steel-600 uppercase flex-shrink-0">{formatDate(review.created_at)}</p>
          </div>

          <div class="flex items-center gap-1 mb-3">
            {#each stars(review.rating) as starState}
              <span class={starState === 'filled' ? 'text-rust-600' : 'text-steel-700'}>★</span>
            {/each}
            <span class="font-mono text-[10px] text-steel-500 ml-2">{review.rating}/5</span>
          </div>

          <p class="font-mono text-[10px] text-steel-400 leading-relaxed">
            {review.comment || 'El cliente dejó una calificación sin comentario adicional.'}
          </p>
        </div>
      {/each}
    </div>
  {/if}
</div>
