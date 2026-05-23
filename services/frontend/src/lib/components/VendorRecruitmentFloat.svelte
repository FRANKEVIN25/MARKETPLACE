<div class="vendor-float-shell" aria-label="Invitacion para proveedores">
  <!-- 1. Eliminamos el flex horizontal del contenedor principal para que todo vaya hacia abajo -->
  <div class="vendor-float-card bg-iron-900/95 border border-steel-600/40 shadow-2xl shadow-black/30 backdrop-blur-sm flex flex-col gap-4">
    
    <!-- 2. Cambiamos la línea decorativa a horizontal (arriba del texto) para acentuar la altura -->
    <div class="flex flex-col gap-2">
      <div class="h-px w-10 bg-rust-600"></div>
      <div class="min-w-0">
        <p class="font-mono text-xs text-bone uppercase tracking-industrial">¿Vendes autopartes?</p>
        <p class="mt-2 font-mono text-[10px] text-steel-500 uppercase tracking-widest leading-relaxed">
          Unete a ECOMPARTS · Llega a miles de clientes B2B y B2C
        </p>
      </div>
    </div>

    <!-- 3. Quitamos 'sm:flex-row' para que los botones se mantengan SIEMPRE uno abajo del otro -->
    <div class="flex flex-col gap-2 w-full">
      <a
        href="/vendedor/registro"
        class="font-mono text-[11px] uppercase tracking-industrial text-bone bg-rust-600 px-4 py-2.5 text-center hover:bg-rust-700 transition-colors order-first"
        style="clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)"
      >
        REGISTRARME →
      </a>
      <a
        href="/vendedor"
        class="font-mono text-[11px] uppercase tracking-industrial text-steel-300 border border-steel-600/60 px-4 py-2.5 text-center hover:border-steel-400 hover:text-bone transition-colors"
      >
        VER PLANES
      </a>
    </div>
  </div>
</div>

<style>
  .vendor-float-shell {
    position: fixed;
    right: 1rem;
    bottom: 1rem;
    z-index: 30;
    pointer-events: none;
    width: min(14rem, calc(100vw - 1.5rem));
  }

  .vendor-float-card {
    pointer-events: auto;
    padding: 1.25rem 1rem;
    clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%);
  }

  @media (min-width: 1024px) {
    .vendor-float-shell {
      top: 50%;
      right: 1.5rem;
      bottom: auto;
      transform: translateY(-50%);
      width: min(14rem, calc(100vw - 3rem));
    }
  }
  </style>