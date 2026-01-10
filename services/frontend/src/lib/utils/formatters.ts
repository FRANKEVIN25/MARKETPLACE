/**
 * Funciones de formateo
 */

/**
 * Formatear precio en soles peruanos
 */
export function formatPrice(price: string | number): string {
  const numPrice = typeof price === 'string' ? parseFloat(price) : price;
  return new Intl.NumberFormat('es-PE', {
    style: 'currency',
    currency: 'PEN',
  }).format(numPrice);
}

/**
 * Formatear fecha
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('es-PE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(date);
}

/**
 * Truncar texto
 */
export function truncate(text: string, length: number = 100): string {
  if (text.length <= length) return text;
  return text.substring(0, length) + '...';
}

/**
 * Obtener URL de imagen o placeholder
 */
export function getImageUrl(imagePath: string | null | undefined): string {
  if (!imagePath) {
    return '/placeholder-product.png';
  }
  
  if (imagePath.startsWith('http')) {
    return imagePath;
  }
  
  const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
  return `${API_URL}${imagePath}`;
}
