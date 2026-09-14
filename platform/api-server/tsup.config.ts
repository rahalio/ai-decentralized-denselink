import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["esm"],
  dts: false,
  external: [
    "@denselink/adapters",
    "@denselink/core",
    "@denselink/services",
    "undici",
  ],
});
