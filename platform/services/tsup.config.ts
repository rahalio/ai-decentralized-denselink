import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts", "src/**/index.ts", "src/**/usecases/index.ts"],
  format: ["esm"],
  dts: false,
  outDir: "dist",
  external: [
    "@aws-sdk/lib-dynamodb",
    "@aws-sdk/client-dynamodb",
    "@denselink/core",
    /.*\/api-server\/.*/,
    /.*\/adapters\/.*/,
  ],
});
