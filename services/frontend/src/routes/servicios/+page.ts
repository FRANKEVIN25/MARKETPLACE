import type { PageLoad } from './$types';

// La página principal de /servicios contiene solo el wizard de búsqueda guiada.
// El resultado se carga en /servicios/resultados.
// No es necesario pre-cargar datos de servicios aquí.
export const load: PageLoad = async () => {
  return {};
};
