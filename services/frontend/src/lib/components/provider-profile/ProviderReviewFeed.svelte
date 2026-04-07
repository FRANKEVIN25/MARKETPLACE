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

<section class="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-[0_24px_70px_-45px_rgba(15,23,42,0.55)]">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <p class="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-700">Reviews</p>
      <h2 class="mt-2 text-3xl font-black text-slate-950">Lo que ya dijeron los clientes</h2>
    </div>
    <p class="max-w-xl text-sm leading-6 text-slate-600">
      Solo se muestran reseñas visibles asociadas a subordenes entregadas. La plantilla es comun; la reputacion la define cada proveedor.
    </p>
  </div>

  {#if reviews.length === 0}
    <div class="mt-8 rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-600">
      Aun no hay reseñas publicadas para este proveedor.
    </div>
  {:else}
    <div class="mt-8 grid gap-4 lg:grid-cols-2">
      {#each reviews as review}
        <article class="rounded-[1.5rem] border border-slate-200 bg-[linear-gradient(180deg,#ffffff,#f8fafc)] p-6">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-lg font-bold text-slate-950">{review.customer_name}</p>
              <p class="text-xs uppercase tracking-[0.24em] text-slate-500">{review.sub_order_number}</p>
            </div>
            <p class="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{formatDate(review.created_at)}</p>
          </div>

          <div class="mt-4 flex items-center gap-1 text-lg">
            {#each stars(review.rating) as state}
              <span class={state === 'filled' ? 'text-amber-500' : 'text-slate-300'}>★</span>
            {/each}
            <span class="ml-2 text-sm font-semibold text-slate-600">{review.rating}/5</span>
          </div>

          <p class="mt-4 text-sm leading-7 text-slate-700">
            {review.comment || 'El cliente dejo una calificacion sin comentario adicional.'}
          </p>
        </article>
      {/each}
    </div>
  {/if}
</section>
