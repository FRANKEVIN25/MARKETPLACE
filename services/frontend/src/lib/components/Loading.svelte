<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let message: string = 'Cargando...';

  const sizeClasses = {
    sm: 'h-8 w-8',
    md: 'h-12 w-12',
    lg: 'h-16 w-16'
  };
</script>

<div class="flex flex-col items-center justify-center p-8">
  <div
    class="animate-spin border-2 border-steel-600/30 border-t-rust-600 {sizeClasses[size]}"
  ></div>
  {#if message}
    <p class="mt-4 font-mono text-[10px] text-steel-500 uppercase tracking-widest">{message}</p>
  {/if}
</div>
