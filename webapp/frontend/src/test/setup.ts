// Polyfills that must run before testing libraries import any web APIs
if (!Object.getOwnPropertyDescriptor(ArrayBuffer.prototype, "resizable")) {
  Object.defineProperty(ArrayBuffer.prototype, "resizable", {
    configurable: true,
    enumerable: false,
    get() {
      return false;
    },
  });
}

if (typeof globalThis.SharedArrayBuffer !== "undefined") {
  const descriptor = Object.getOwnPropertyDescriptor(
    globalThis.SharedArrayBuffer.prototype,
    "growable",
  );
  if (!descriptor) {
    Object.defineProperty(globalThis.SharedArrayBuffer.prototype, "growable", {
      configurable: true,
      enumerable: false,
      get() {
        return false;
      },
    });
  }
} else {
  class SharedArrayBufferStub {}
  Object.defineProperty(SharedArrayBufferStub.prototype, "growable", {
    configurable: true,
    enumerable: false,
    get() {
      return false;
    },
  });
  // @ts-expect-error assign stub for test environment
  globalThis.SharedArrayBuffer = SharedArrayBufferStub;
}

if (!globalThis.ResizeObserver) {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error test shim
  globalThis.ResizeObserver = ResizeObserverMock;
}

import "@testing-library/jest-dom/vitest";

import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

afterEach(() => {
  cleanup();
});
