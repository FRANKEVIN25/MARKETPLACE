<script lang="ts">
  import { goto } from '$app/navigation';

  function goToRegistration(): void {
    goto('/vendedor/registro');
  }
</script>

<svelte:head>
  <title>Vende en ECOMPARTS — Marketplace de Autopartes</title>
  <meta name="description" content="Registra tu negocio y vende autopartes a miles de clientes en todo el Perú. Sistema de gestión integrado, pagos seguros y comisiones competitivas." />
</svelte:head>

<!-- ══════════════════════════════════════════════
     HERO — VENDORS
═══════════════════════════════════════════════ -->
<section class="hero-industrial relative overflow-hidden">
  <!-- Watermark -->
  <div class="absolute inset-0 flex items-center justify-end pr-8 pointer-events-none overflow-hidden select-none" aria-hidden="true">
    <span class="font-display text-[18vw] text-steel-600/5 leading-none uppercase tracking-tighter whitespace-nowrap">
      VENDORS
    </span>
  </div>
  <!-- Left accent -->
  <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-transparent via-rust-600/40 to-transparent pointer-events-none"></div>

  <div class="container-responsive py-20 md:py-28 relative z-10">
    <div class="inline-flex items-center gap-3 border border-rust-600/60 bg-rust-600/10 px-4 py-2 mb-8">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rust-500 opacity-75"></span>
        <span class="relative inline-flex h-2 w-2 rounded-full bg-rust-600"></span>
      </span>
      <span class="font-mono text-[11px] text-rust-500 uppercase tracking-widest">PARA PROVEEDORES · PROGRAMA DE VENDORS</span>
    </div>

    <h1 class="font-display uppercase leading-none mb-6 max-w-4xl">
      <span class="block text-[clamp(48px,8vw,100px)] text-bone">VENDE TUS</span>
      <span class="block text-[clamp(48px,8vw,100px)] text-rust-600">AUTOPARTES</span>
      <span class="block text-[clamp(48px,8vw,100px)] text-bone">EN ECOMPARTS</span>
    </h1>

    <p class="font-mono text-sm text-steel-400 uppercase tracking-industrial mb-10 max-w-xl">
      Llega a miles de talleres y distribuidores · Red B2B de autopartes en todo el Perú
    </p>

    <div class="flex flex-wrap gap-4">
      <button
        onclick={goToRegistration}
        class="btn-rust text-base"
      >
        REGISTRARME AHORA →
      </button>
      <a href="#como-funciona" class="btn-outline text-base">VER CÓMO FUNCIONA</a>
    </div>
  </div>

  <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-rust-600/50 to-transparent"></div>
</section>

<!-- ══════════════════════════════════════════════
     BENEFICIOS
═══════════════════════════════════════════════ -->
<section class="container-responsive py-16">
  <div class="border-b border-steel-600/25 pb-6 mb-10">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// VENTAJAS</p>
    <h2 class="font-display text-5xl text-bone uppercase leading-none">¿POR QUÉ VENDER CON NOSOTROS?</h2>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-0 bg-iron-900 border border-steel-600/25"
       style="clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%)">

    {#each [
      {
        num: '01',
        title: 'MILES DE CLIENTES',
        desc: 'Accede a una base de clientes B2B en constante crecimiento: talleres, flotas y distribuidores.',
        icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z'
      },
      {
        num: '02',
        title: 'GESTIÓN FÁCIL',
        desc: 'Sistema ERP integrado (Odoo) para gestionar tu inventario, pedidos y facturación desde un solo lugar.',
        icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
      },
      {
        num: '03',
        title: 'PAGOS SEGUROS',
        desc: 'Recibe tus pagos de forma segura y puntual. Comisiones competitivas y liquidaciones transparentes.',
        icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
      },
    ] as item, i}
      <div class="border-r border-steel-600/20 last:border-r-0 p-8">
        <span class="font-display text-6xl text-rust-600/15 leading-none block mb-4">{item.num}</span>
        <svg class="w-6 h-6 text-rust-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d={item.icon} />
        </svg>
        <h3 class="font-display text-2xl text-bone uppercase mb-2">{item.title}</h3>
        <p class="font-mono text-xs text-steel-500 leading-relaxed">{item.desc}</p>
      </div>
    {/each}

  </div>
</section>

<!-- ══════════════════════════════════════════════
     CÓMO FUNCIONA
═══════════════════════════════════════════════ -->
<section id="como-funciona" class="bg-iron-900 border-t border-b border-steel-600/25 py-16">
  <div class="container-responsive">
    <div class="border-b border-steel-600/25 pb-6 mb-10">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// PROCESO</p>
      <h2 class="font-display text-5xl text-bone uppercase leading-none">CÓMO FUNCIONA</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      {#each [
        { step: '01', title: 'REGÍSTRATE', desc: 'Crea tu cuenta en menos de 5 minutos. Gratis y sin compromiso.' },
        { step: '02', title: 'CARGA TU CATÁLOGO', desc: 'Agrega tus productos desde el sistema Odoo integrado. Control total de stock.' },
        { step: '03', title: 'EMPIEZA A VENDER', desc: 'Recibe pedidos y gestiona tu negocio desde un solo lugar. Soporte dedicado.' },
      ] as item}
        <div class="relative border-l-2 border-rust-600/40 pl-6">
          <span class="font-display text-7xl text-rust-600/20 leading-none block mb-2">{item.step}</span>
          <h3 class="font-display text-2xl text-bone uppercase mb-2">{item.title}</h3>
          <p class="font-mono text-xs text-steel-500 leading-relaxed">{item.desc}</p>
        </div>
      {/each}
    </div>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     PLANES
═══════════════════════════════════════════════ -->
<section class="container-responsive py-16">
  <div class="border-b border-steel-600/25 pb-6 mb-10">
    <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-2">// PLANES</p>
    <h2 class="font-display text-5xl text-bone uppercase leading-none">PARA TODO TAMAÑO DE NEGOCIO</h2>
    <p class="font-mono text-xs text-steel-500 mt-2 uppercase tracking-widest">Desde emprendedores hasta grandes distribuidoras</p>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    {#each [
      { name: 'STARTER', price: 'GRATIS', highlight: false, badge: null },
      { name: 'PRO', price: 'S/. 99/MES', highlight: true, badge: 'RECOMENDADO' },
      { name: 'PREMIUM', price: 'S/. 299/MES', highlight: false, badge: null },
    ] as plan}
      <div class="bg-iron-900 border {plan.highlight ? 'border-rust-600' : 'border-steel-600/25'} relative p-6"
           style="clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)">
        {#if plan.badge}
          <div class="absolute -top-3 left-6">
            <span class="font-mono text-[9px] uppercase tracking-widest bg-rust-600 text-bone px-3 py-1">
              {plan.badge}
            </span>
          </div>
        {/if}
        <h3 class="font-display text-3xl {plan.highlight ? 'text-rust-600' : 'text-bone'} uppercase mb-2">{plan.name}</h3>
        <p class="font-display text-2xl text-bone">{plan.price}</p>
      </div>
    {/each}
  </div>

  <div class="mt-6 text-center">
    <a href="/vendedor/registro"
       class="font-mono text-[10px] uppercase tracking-widest text-rust-500 hover:text-rust-400 transition-colors">
      VER DETALLE COMPLETO DE PLANES EN EL REGISTRO →
    </a>
  </div>
</section>

<!-- ══════════════════════════════════════════════
     CTA FINAL
═══════════════════════════════════════════════ -->
<section class="container-responsive pb-16">
  <div class="relative bg-iron-900 border border-steel-600/25 p-10 md:p-16 overflow-hidden"
       style="clip-path: polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 0 100%)">
    <!-- BG decoration -->
    <div class="absolute top-0 right-0 w-64 h-64 opacity-5 pointer-events-none" aria-hidden="true">
      <svg viewBox="0 0 200 200" fill="none" stroke="#e64a19" stroke-width="0.5">
        <circle cx="100" cy="100" r="90"/>
        <circle cx="100" cy="100" r="70"/>
        <circle cx="100" cy="100" r="50"/>
        <line x1="10" y1="100" x2="190" y2="100"/>
        <line x1="100" y1="10" x2="100" y2="190"/>
      </svg>
    </div>
    <div class="relative z-10">
      <p class="font-mono text-[10px] text-rust-600 uppercase tracking-widest mb-4">// ÚNETE AHORA</p>
      <h2 class="font-display text-5xl md:text-6xl text-bone uppercase leading-none mb-4">
        ¿LISTO PARA<br/>EMPEZAR?
      </h2>
      <p class="font-mono text-sm text-steel-400 uppercase tracking-industrial mb-8 max-w-lg">
        Únete a los cientos de vendors que confían en ECOMPARTS para hacer crecer su negocio.
      </p>
      <button onclick={goToRegistration} class="btn-rust text-base">
        CREAR MI CUENTA GRATIS →
      </button>
    </div>
  </div>
</section>
