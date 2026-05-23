<script lang="ts">
  type BrandItem = {
    name: string;
    src: string;
  };

  export let brands: BrandItem[] = [];
</script>

{#if brands.length > 0}
  <section class="border-steel-600/25 bg-iron-900/70">
    <div class="brand-marquee-shell">
      <div class="brand-marquee-track">
        {#each Array(2) as _}
          <div class="brand-marquee-group" aria-hidden={_ === 1}>
            {#each brands as brand}
              <div class="brand-marquee-item">
                <img
                  src={brand.src}
                  alt={`Logo de ${brand.name}`}
                  class="brand-marquee-image"
                  loading="lazy"
                />
              </div>
            {/each}
          </div>
        {/each}
      </div>
    </div>
  </section>
{/if}

<style>
  .brand-marquee-shell {
    overflow: hidden;
    background:
      linear-gradient(90deg, rgba(29, 29, 29, 0.96) 0%, rgba(40, 40, 40, 0.96) 50%, rgba(26, 26, 26, 0.96) 100%);
  }

  .brand-marquee-track {
    display: flex;
    width: max-content;
    animation: brand-marquee-scroll 28s linear infinite;
  }

  .brand-marquee-track:hover {
    animation-play-state: paused;
  }

  .brand-marquee-group {
    display: flex;
    align-items: center;
    justify-content: space-around;
    flex-shrink: 0;
    min-width: 100%;
    gap: 1rem;
    padding: 1rem 1.2rem;
  }

  .brand-marquee-item {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 5rem;
    height: 3rem;
    padding: 0.5rem;
    opacity: 0.8;
    filter: grayscale(1) contrast(1.15) brightness(0.82);
    transition: filter 180ms ease, opacity 180ms ease, transform 180ms ease;
  }

  .brand-marquee-item:hover {
    opacity: 0.7;
    filter: grayscale(0) contrast(1) brightness(1);
    transform: translateY(-2px);
  }

  .brand-marquee-image {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    user-select: none;
  }

  @keyframes brand-marquee-scroll {
    0% {
      transform: translate3d(0, 0, 0);
    }

    100% {
      transform: translate3d(-50%, 0, 0);
    }
  }

  @media (max-width: 640px) {
    .brand-marquee-group {
      gap: 1.25rem;
      padding: 1rem 1rem;
    }

    .brand-marquee-item {
      width: 4.5rem;
      height: 2.25rem;
    }
  }
</style>