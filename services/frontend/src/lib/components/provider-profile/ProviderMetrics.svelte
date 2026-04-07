<script lang="ts">
  export let ratingBreakdown: Record<string, number> = {};
  export let averageRating = 0;
  export let ratingCount = 0;
  export let publishedAt = '';

  const orderedStars = [5, 4, 3, 2, 1];

  function getCount(star: number): number {
    return Number(ratingBreakdown[String(star)] ?? 0);
  }

  function getWidth(star: number): string {
    if (!ratingCount) return '0%';
    return `${(getCount(star) / ratingCount) * 100}%`;
  }

  function formatMonth(value: string): string {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Reciente';

    return new Intl.DateTimeFormat('es-PE', {
      month: 'long',
      year: 'numeric',
    }).format(date);
  }
</script>

<section class="grid gap-6 lg:grid-cols-[0.9fr,1.1fr]">
  <article class="rounded-[2rem] bg-slate-950 p-8 text-white shadow-[0_24px_80px_-50px_rgba(15,23,42,0.85)]">
    <p class="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-300">Resumen de reputacion</p>
    <div class="mt-6 flex items-end gap-4">
      <p class="text-6xl font-black">{averageRating.toFixed(1)}</p>
      <div class="pb-2">
        <p class="text-lg font-semibold">sobre 5.0</p>
        <p class="text-sm text-white/70">{ratingCount} calificaciones visibles</p>
      </div>
    </div>

    <div class="mt-6 space-y-3">
      {#each orderedStars as star}
        <div class="grid grid-cols-[44px,1fr,36px] items-center gap-3 text-sm">
          <span class="font-semibold text-white/80">{star}★</span>
          <div class="h-3 overflow-hidden rounded-full bg-white/10">
            <div class="h-full rounded-full bg-cyan-300" style={`width: ${getWidth(star)};`}></div>
          </div>
          <span class="text-right text-white/70">{getCount(star)}</span>
        </div>
      {/each}
    </div>
  </article>

  <article class="rounded-[2rem] border border-slate-200 bg-[linear-gradient(180deg,#fff7ed,#ffffff)] p-8 shadow-[0_24px_70px_-45px_rgba(148,163,184,0.55)]">
    <p class="text-sm font-semibold uppercase tracking-[0.24em] text-orange-700">Lectura rapida</p>
    <h2 class="mt-2 text-3xl font-black text-slate-950">La plantilla deja claro por que confiar</h2>
    <div class="mt-6 grid gap-4 sm:grid-cols-2">
      <div class="rounded-[1.5rem] border border-orange-100 bg-white/90 p-5">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Evidencia</p>
        <p class="mt-3 text-lg font-bold text-slate-950">Opiniones post entrega</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">La reputacion solo suma con subordenes entregadas y reseñas visibles.</p>
      </div>
      <div class="rounded-[1.5rem] border border-orange-100 bg-white/90 p-5">
        <p class="text-xs uppercase tracking-[0.24em] text-slate-500">Antiguedad del perfil</p>
        <p class="mt-3 text-lg font-bold text-slate-950">Desde {formatMonth(publishedAt)}</p>
        <p class="mt-2 text-sm leading-6 text-slate-600">Un formato comun permite comparar proveedores sin inventar layouts distintos.</p>
      </div>
    </div>
  </article>
</section>
