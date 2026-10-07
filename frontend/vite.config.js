import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

const proxy = {
  "/api": {
    target: "http://127.0.0.1:8000",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ""),
  },
};
export default defineConfig({
  plugins: [vue()],
  server: { proxy },
  preview: { proxy },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.js"],
    restoreMocks: true,
  },
});
