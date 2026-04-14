/**
 * Checkout Store
 *
 * Persiste el estado completo del proceso de compra entre los pasos:
 * Carrito → Perfil → Entrega → Pago → Confirmación
 */
import { writable, derived, get } from 'svelte/store';
import type { CartItem } from './cart';
import type {
  Address,
  Customer,
  DeliveryMethod,
  Order,
} from '../api/types';

// ─── Pasos del checkout ───────────────────────────────────────────────────────
export type CheckoutStep = 'carrito' | 'perfil' | 'entrega' | 'pago';

export const CHECKOUT_STEPS: CheckoutStep[] = [
  'carrito',
  'perfil',
  'entrega',
  'pago',
];

export const STEP_LABELS: Record<CheckoutStep, string> = {
  carrito: 'Carrito',
  perfil: 'Perfil',
  entrega: 'Entrega',
  pago: 'Pago y Confirmación',
};

// ─── Estado del checkout ──────────────────────────────────────────────────────
export interface CheckoutState {
  /** Paso activo */
  step: CheckoutStep;

  /** Snapshot de los items del carrito al iniciar el checkout */
  items: CartItem[];

  /** Cliente autenticado (se carga al abrir el checkout) */
  customer: Customer | null;

  /** Método de entrega elegido */
  deliveryMethod: DeliveryMethod;

  /** Dirección seleccionada (para domicilio o agencia) */
  shippingAddress: Address | null;

  /** Notas del cliente para el pedido */
  customerNotes: string;

  /** Orden creada en el backend (disponible desde el paso "pago") */
  order: Order | null;

  /** Si está procesando alguna acción asíncrona */
  loading: boolean;

  /** Mensaje de error global */
  error: string;
}

const INITIAL_STATE: CheckoutState = {
  step: 'carrito',
  items: [],
  customer: null,
  deliveryMethod: 'domicilio',
  shippingAddress: null,
  customerNotes: '',
  order: null,
  loading: false,
  error: '',
};

// ─── Store factory ────────────────────────────────────────────────────────────
function createCheckoutStore() {
  const { subscribe, set, update } = writable<CheckoutState>({ ...INITIAL_STATE });

  return {
    subscribe,

    /** Iniciar el checkout con los items actuales del carrito */
    init(items: CartItem[], customer: Customer) {
      update(s => ({ ...s, items, customer, step: 'perfil', error: '', order: null }));
    },

    /** Avanzar al siguiente paso */
    nextStep() {
      update(s => {
        const idx = CHECKOUT_STEPS.indexOf(s.step);
        if (idx < CHECKOUT_STEPS.length - 1) {
          return { ...s, step: CHECKOUT_STEPS[idx + 1], error: '' };
        }
        return s;
      });
    },

    /** Retroceder al paso anterior */
    prevStep() {
      update(s => {
        const idx = CHECKOUT_STEPS.indexOf(s.step);
        if (idx > 0) {
          return { ...s, step: CHECKOUT_STEPS[idx - 1], error: '' };
        }
        return s;
      });
    },

    /** Ir directamente a un paso */
    goTo(step: CheckoutStep) {
      update(s => ({ ...s, step, error: '' }));
    },

    /** Guardar método de entrega */
    setDeliveryMethod(method: DeliveryMethod) {
      update(s => ({ ...s, deliveryMethod: method }));
    },

    /** Guardar dirección seleccionada */
    setShippingAddress(address: Address | null) {
      update(s => ({ ...s, shippingAddress: address }));
    },

    /** Guardar notas del cliente */
    setNotes(notes: string) {
      update(s => ({ ...s, customerNotes: notes }));
    },

    /** Guardar la orden creada en el backend */
    setOrder(order: Order) {
      update(s => ({ ...s, order, step: 'pago', error: '' }));
    },

    /**
     * Actualizar el status de una SubOrder específica dentro de state.order.
     * Se usa para reflejar la transición optimista pendiente_pago → pago_en_revision
     * inmediatamente después de que el cliente sube su comprobante, sin necesidad
     * de re-fetch completo. Esto detiene el countdown timer.
     */
    patchSubOrderStatus(subOrderId: number, newStatus: string) {
      update(s => {
        if (!s.order) return s;
        return {
          ...s,
          order: {
            ...s.order,
            sub_orders: s.order.sub_orders.map(so =>
              so.id === subOrderId ? { ...so, status: newStatus } : so
            ),
          },
        };
      });
    },

    /** Estado de carga */
    setLoading(loading: boolean) {
      update(s => ({ ...s, loading }));
    },

    /** Mensaje de error */
    setError(error: string) {
      update(s => ({ ...s, error, loading: false }));
    },

    /** Resetear completamente el checkout */
    reset() {
      set({ ...INITIAL_STATE });
    },

    /** Leer el estado actual (sin suscribirse) */
    get(): CheckoutState {
      return get({ subscribe });
    },
  };
}

export const checkout = createCheckoutStore();

// ─── Derivados útiles ─────────────────────────────────────────────────────────

/** Índice numérico del paso actual (0-4) */
export const checkoutStepIndex = derived(
  checkout,
  $c => CHECKOUT_STEPS.indexOf($c.step)
);

/** Subtotal sin IGV (suma de precioUnitario × cantidad) */
export const checkoutSubtotal = derived(checkout, $c =>
  $c.items.reduce((acc, item) => acc + item.precioTotal, 0)
);

/** Grupos de items por proveedor { providerName: CartItem[] } */
export const checkoutItemsByProvider = derived(checkout, $c => {
  const groups: Record<string, CartItem[]> = {};
  for (const item of $c.items) {
    const key = item.provider_name || 'Sin proveedor';
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return groups;
});

/** Número de proveedores distintos en el carrito */
export const checkoutProviderCount = derived(
  checkoutItemsByProvider,
  $g => Object.keys($g).length
);
