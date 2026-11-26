import "@testing-library/jest-dom/vitest";

// Robust localStorage mock for Node 22+ / jsdom test environments
if (typeof window !== "undefined") {
  const store = new Map();
  const mockStorage = {
    getItem: (key) => (store.has(String(key)) ? store.get(String(key)) : null),
    setItem: (key, val) => {
      store.set(String(key), String(val));
    },
    removeItem: (key) => {
      store.delete(String(key));
    },
    clear: () => {
      store.clear();
    },
    get length() {
      return store.size;
    },
    key: (i) => Array.from(store.keys())[i] || null,
  };

  try {
    Object.defineProperty(window, "localStorage", {
      value: mockStorage,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(globalThis, "localStorage", {
      value: mockStorage,
      writable: true,
      configurable: true,
    });
  } catch {}
}
