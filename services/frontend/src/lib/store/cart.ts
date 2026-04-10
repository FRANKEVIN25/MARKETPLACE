import { writable, get } from 'svelte/store';
import type { BackendCartLine } from '../api/types';
import { api } from '../api/client';
import { auth } from './auth';

export interface CartItem {
  id: number;
  product: {
    id: number;
    name: string;
    slug: string;
    reference: string | null;
    image_url: string | null;
  };
  provider_name: string;
  cantidad: number;
  precioUnitario: number;
  precioTotal: number;
  is_available: boolean;
}

export type Cart = CartItem[];

function lineToCartItem(line: BackendCartLine): CartItem {
  const precio = parseFloat(line.price_unit);
  const tax = parseFloat(line.tax_percent);
  const precioUnitario = precio * (1 + tax / 100);
  return {
    id: line.id,
    product: line.product,
    provider_name: line.provider_name,
    cantidad: line.quantity,
    precioUnitario,
    precioTotal: precioUnitario * line.quantity,
    is_available: line.is_available,
  };
}

function createCartStore() {
  const { subscribe, set, update } = writable<CartItem[]>([]);

  function getToken(): string | null {
    return auth.getAccessToken();
  }

  async function refresh(): Promise<void> {
    const token = getToken();
    if (!token) { set([]); return; }
    try {
      const data = await api.cart.get(token);
      set(data.lines.map(lineToCartItem));
    } catch {
      set([]);
    }
  }

  return {
    subscribe,
    refresh,

    async addItem(productId: number, cantidad: number = 1): Promise<void> {
      const token = getToken();
      if (!token) return;
      try {
        await api.cart.addLine(token, productId, cantidad);
        await refresh();
      } catch (e) {
        console.error('Error al agregar al carrito', e);
      }
    },

    async removeItem(productId: number): Promise<void> {
      const token = getToken();
      if (!token) return;
      // Optimistic update
      update(items => items.filter(i => i.product.id !== productId));
      try {
        await api.cart.removeLine(token, productId);
      } catch {
        await refresh();
      }
    },

    async updateCantidad(productId: number, nuevaCantidad: number): Promise<void> {
      if (nuevaCantidad < 1) return;
      const token = getToken();
      if (!token) return;
      try {
        const line = await api.cart.updateQuantity(token, productId, nuevaCantidad);
        update(items => items.map(i =>
          i.product.id === productId ? lineToCartItem(line) : i
        ));
      } catch {
        await refresh();
      }
    },

    async clear(): Promise<void> {
      const token = getToken();
      if (!token) { set([]); return; }
      try {
        await api.cart.clear(token);
      } catch { /* server-side clear may fail; clear locally */ }
      set([]);
    },
  };
}

export const cart = createCartStore();
