import { writable, derived, get } from 'svelte/store';
import type { AuthUser, AuthTokens, Customer } from '../api/types';

const ACCESS_KEY = 'ecomparts_access';
const REFRESH_KEY = 'ecomparts_refresh';

function loadFromStorage(): { access: string | null; refresh: string | null } {
  if (typeof localStorage === 'undefined') return { access: null, refresh: null };
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  };
}

function createAuthStore() {
  const { access, refresh } = loadFromStorage();

  const tokens = writable<AuthTokens | null>(
    access && refresh ? { access, refresh } : null
  );
  const user = writable<AuthUser | null>(null);
  const customer = writable<Customer | null>(null);
  const loading = writable<boolean>(false);

  const isAuthenticated = derived(tokens, $tokens => !!$tokens?.access);

  function setTokens(t: AuthTokens) {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(ACCESS_KEY, t.access);
      localStorage.setItem(REFRESH_KEY, t.refresh);
    }
    tokens.set(t);
  }

  function clearTokens() {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }
    tokens.set(null);
    user.set(null);
    customer.set(null);
  }

  function getAccessToken(): string | null {
    return get(tokens)?.access ?? null;
  }

  function getRefreshToken(): string | null {
    return get(tokens)?.refresh ?? null;
  }

  function updateAccessToken(access: string) {
    const currentTokens = get(tokens);
    if (!currentTokens?.refresh) {
      clearTokens();
      return;
    }

    setTokens({
      access,
      refresh: currentTokens.refresh,
    });
  }

  return {
    tokens,
    user,
    customer,
    loading,
    isAuthenticated,
    setTokens,
    clearTokens,
    getAccessToken,
    getRefreshToken,
    updateAccessToken,
  };
}

export const auth = createAuthStore();
