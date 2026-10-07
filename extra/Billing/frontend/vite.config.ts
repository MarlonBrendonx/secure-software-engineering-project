import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Em desenvolvimento, o Vite repassa /api para a API em :8000. Assim navegador,
// cookies e CSRF funcionam como em produção (mesma origem, sem CORS).
export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false, xfwd: true },
    },
  },
});
