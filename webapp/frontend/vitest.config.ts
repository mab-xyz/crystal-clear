import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
Object.getOwnPropertyDescriptor = function (target: any, property: PropertyKey) {
  if (target === ArrayBuffer.prototype && property === "resizable") {
    return {
      configurable: true,
      enumerable: false,
      get() {
        return false;
      },
    } as PropertyDescriptor;
  }

  if (
    typeof globalThis.SharedArrayBuffer !== "undefined" &&
    target === SharedArrayBuffer.prototype &&
    property === "growable"
  ) {
    return {
      configurable: true,
      enumerable: false,
      get() {
        return false;
      },
    } as PropertyDescriptor;
  }

  return originalGetOwnPropertyDescriptor(target, property);
};

if (typeof globalThis.SharedArrayBuffer === "undefined") {
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

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      globalSetup: "./src/test/globalSetup.ts",
      css: true,
    },
  }),
);
