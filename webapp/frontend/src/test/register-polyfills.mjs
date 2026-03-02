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
  if (!Object.getOwnPropertyDescriptor(SharedArrayBuffer.prototype, "growable")) {
    Object.defineProperty(SharedArrayBuffer.prototype, "growable", {
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
  globalThis.SharedArrayBuffer = SharedArrayBufferStub;
}
