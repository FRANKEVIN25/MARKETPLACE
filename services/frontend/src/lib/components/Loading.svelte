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
    class="animate-spin rounded-full border-b-2 border-primary-600 {sizeClasses[size]}"
  ></div>
  {#if message}
    <p class="mt-4 text-gray-600">{message}</p>
  {/if}
</div>
