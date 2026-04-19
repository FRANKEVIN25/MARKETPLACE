<footer class="bg-iron-950 border-t-2 border-rust-600 mt-auto">

  <!-- Top grid section -->
  <div class="container-responsive py-14">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 md:gap-10">

      <!-- Col 1: Brand -->
      <div class="lg:col-span-1">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-9 h-9 bg-rust-600 flex items-center justify-center"
               style="clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)">
            <span class="font-display text-2xl text-bone leading-none">E</span>
          </div>
          <span class="font-display text-2xl text-bone tracking-widest">ECOMPARTS</span>
        </div>
        <p class="font-mono text-[11px] text-steel-500 leading-relaxed uppercase tracking-wide mb-5">
          Marketplace B2B de autopartes en Perú. Repuestos de calidad, precio justo, entrega rápida.
        </p>
        <div class="flex items-center gap-2">
          <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
          <span class="font-mono text-[10px] text-steel-600 uppercase tracking-widest">SISTEMA OPERATIVO · LIMA, PERÚ</span>
        </div>
      </div>

      <!-- Col 2: Marketplace links -->
      <div>
        <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-4">// MARKETPLACE</p>
        <ul class="space-y-2.5">
          {#each [
            { label: 'INICIO',      href: '/' },
            { label: 'PRODUCTOS',   href: '/productos' },
            { label: 'PROVEEDORES', href: '/proveedores' },
            { label: 'SERVICIOS',   href: '/servicios' },
            { label: 'CARRITO',     href: '/carrito' },
          ] as link}
            <li>
              <a href={link.href}
                 class="font-mono text-[11px] text-steel-500 uppercase tracking-widest hover:text-rust-500 transition-colors flex items-center gap-2">
                <span class="text-steel-700">—</span> {link.label}
              </a>
            </li>
          {/each}
        </ul>
      </div>

      <!-- Col 3: Vendors links -->
      <div>
        <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-4">// PARA VENDORS</p>
        <ul class="space-y-2.5">
          {#each [
            { label: 'PLANES Y PRECIOS', href: '/vendedor' },
            { label: 'CÓMO FUNCIONA',   href: '/vendedor#como-funciona' },
            { label: 'REGISTRARME',     href: '/vendedor/registro' },
            { label: 'MI DASHBOARD',    href: '/vendedor/dashboard' },
          ] as link}
            <li>
              <a href={link.href}
                 class="font-mono text-[11px] text-steel-500 uppercase tracking-widest hover:text-rust-500 transition-colors flex items-center gap-2">
                <span class="text-steel-700">—</span> {link.label}
              </a>
            </li>
          {/each}
        </ul>
      </div>

      <!-- Col 4: Contact -->
      <div>
        <p class="font-mono text-[9px] text-rust-600 uppercase tracking-widest mb-4">// CONTACTO</p>
        <ul class="space-y-3">
          <li class="flex items-start gap-2">
            <span class="font-mono text-[10px] text-steel-700 mt-0.5 shrink-0">✉</span>
            <span class="font-mono text-[11px] text-steel-500 uppercase tracking-wide break-all">INFO@ECOMPARTS.PE</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="font-mono text-[10px] text-steel-700 mt-0.5 shrink-0">☎</span>
            <span class="font-mono text-[11px] text-steel-500 uppercase tracking-wide">+51 999 999 999</span>
          </li>
          <li class="flex items-start gap-2">
            <span class="font-mono text-[10px] text-steel-700 mt-0.5 shrink-0">◉</span>
            <span class="font-mono text-[11px] text-steel-500 uppercase tracking-wide">LIMA, PERÚ</span>
          </li>
        </ul>

        <div class="mt-6 pt-4 border-t border-steel-600/20">
          <a href="/vendedor/registro"
             class="block w-full bg-rust-600 hover:bg-rust-700 text-bone font-mono text-[11px] uppercase tracking-industrial py-3 text-center transition-colors">
            QUIERO SER VENDOR →
          </a>
        </div>
      </div>

    </div>
  </div>

  <!-- Bottom bar -->
  <div class="border-t border-steel-600/20">
    <div class="container-responsive py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
      <p class="font-mono text-[10px] text-steel-700 uppercase tracking-widest">
        © 2025 ECOMPARTS · TODOS LOS DERECHOS RESERVADOS
      </p>
      <div class="flex items-center gap-4">
        <a href="/terminos" class="font-mono text-[10px] text-steel-700 hover:text-steel-500 uppercase tracking-widest transition-colors">
          TÉRMINOS
        </a>
        <span class="text-steel-700">·</span>
        <a href="/privacidad" class="font-mono text-[10px] text-steel-700 hover:text-steel-500 uppercase tracking-widest transition-colors">
          PRIVACIDAD
        </a>
        <span class="text-steel-700">·</span>
        <span class="font-mono text-[10px] text-steel-700 uppercase tracking-widest">
          v2.0 · INDUSTRIAL
        </span>
      </div>
    </div>
  </div>

</footer>
