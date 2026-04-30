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

<div class="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
  <!-- Rating breakdown -->
  <div class="bg-iron-900 border border-steel-600/25"
       style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
    <div class="border-b border-steel-600/25 px-5 py-3">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// RESUMEN DE REPUTACIÓN</p>
    </div>
    <div class="px-5 py-5">
      <div class="flex items-end gap-4 mb-5">
        <p class="font-display text-6xl text-rust-600 leading-none">{averageRating.toFixed(1)}</p>
        <div class="pb-1">
          <p class="font-mono text-xs text-bone uppercase">SOBRE 5.0</p>
          <p class="font-mono text-[10px] text-steel-500">{ratingCount} CALIFICACIONES</p>
        </div>
      </div>
      <div class="space-y-2">
        {#each orderedStars as star}
          <div class="grid grid-cols-[40px_1fr_32px] items-center gap-3">
            <span class="font-mono text-[10px] text-steel-400">{star}★</span>
            <div class="h-1.5 bg-iron-800 border border-steel-600/20 overflow-hidden">
              <div class="h-full bg-rust-600" style={`width: ${getWidth(star)};`}></div>
            </div>
            <span class="font-mono text-[10px] text-steel-500 text-right">{getCount(star)}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <!-- Lectura rápida -->
  <div class="bg-iron-900 border border-steel-600/25"
       style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
    <div class="border-b border-steel-600/25 px-5 py-3">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest">// LECTURA RÁPIDA</p>
    </div>
    <div class="p-5 grid gap-3 sm:grid-cols-2">
      <div class="bg-iron-800/50 border border-steel-600/20 p-4">
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">EVIDENCIA</p>
        <p class="font-mono text-xs text-bone mb-1">OPINIONES POST ENTREGA</p>
        <p class="font-mono text-[10px] text-steel-500 leading-relaxed">La reputación solo suma con subórdenes entregadas y reseñas visibles.</p>
      </div>
      <div class="bg-iron-800/50 border border-steel-600/20 p-4">
        <p class="font-mono text-[9px] text-steel-600 uppercase tracking-widest mb-2">ANTIGÜEDAD</p>
        <p class="font-mono text-xs text-bone mb-1">DESDE {formatMonth(publishedAt).toUpperCase()}</p>
        <p class="font-mono text-[10px] text-steel-500 leading-relaxed">Un formato común permite comparar proveedores sin inventar layouts distintos.</p>
      </div>
    </div>
  </div>
</div>
