import { writable } from 'svelte/store';
import type { Product, StockItem } from '../api/types';

export interface CartItem {
  product: Product;
  cantidad: number;
  precioUnitario: number;
  precioTotal: number;
  stockDisponible: number;
  stockItems?: StockItem[];
}

export type Cart = CartItem[];

const CART_STORAGE_KEY = 'ecomparts_cart';

function loadFromStorage(): Cart {
  if (typeof localStorage === 'undefined') return [];
  try {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveToStorage(cart: Cart): void {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
  }
}

function calcularPrecioUnitario(product: Product): number {
  const precioBase = parseFloat(product.price || '0');
  const impuesto = parseFloat(product.tax_percent || '18') || 18;
  return precioBase + (precioBase * impuesto / 100);
}

function calcularPrecioTotal(product: Product, cantidad: number): number {
  return calcularPrecioUnitario(product) * cantidad;
}

function getStockDisponible(product: Product): number {
  return product.total_stock || 0;
}

function createCartStore() {
  const { subscribe, set, update } = writable<Cart>(loadFromStorage());

  function persist(cart: Cart): Cart {
    saveToStorage(cart);
    return cart;
  }

  return {
    subscribe,
    addItem(product: Product, cantidad: number = 1) {
      update(cart => {
        const index = cart.findIndex(item => item.product.id === product.id);
        const stockDisponible = getStockDisponible(product);
        if (index !== -1) {
          const nuevaCantidad = Math.min(cart[index].cantidad + cantidad, stockDisponible);
          cart[index].cantidad = nuevaCantidad;
          cart[index].precioTotal = calcularPrecioTotal(product, nuevaCantidad);
        } else {
          cart.push({
            product,
            cantidad: Math.min(cantidad, stockDisponible),
            precioUnitario: calcularPrecioUnitario(product),
            precioTotal: calcularPrecioTotal(product, cantidad),
            stockDisponible,
            stockItems: product.stock_items || []
          });
        }
        return persist(cart);
      });
    },
    removeItem(productId: number) {
      update(cart => persist(cart.filter(item => item.product.id !== productId)));
    },
    updateCantidad(productId: number, nuevaCantidad: number) {
      update(cart => persist(cart.map(item => {
        if (item.product.id === productId) {
          const stockDisponible = getStockDisponible(item.product);
          const cantidadFinal = Math.max(1, Math.min(nuevaCantidad, stockDisponible));
          return {
            ...item,
            cantidad: cantidadFinal,
            precioTotal: calcularPrecioTotal(item.product, cantidadFinal)
          };
        }
        return item;
      })));
    },
    clear() {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(CART_STORAGE_KEY);
      }
      set([]);
    }
  };
}

export const cart = createCartStore();
