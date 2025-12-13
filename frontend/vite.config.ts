import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const FRONTEND_PORT = parseInt(env.FRONTEND_PORT || "8080");
  const BACKEND_PORT = parseInt(env.BACKEND_PORT || "8000");

  return {
    server: {
      host: "::",
      port: FRONTEND_PORT,
      proxy: {
        '/api': {
          target: `https://localhost:${BACKEND_PORT}`,
          changeOrigin: true,
          secure: false,
        },
        '/auth': {
          target: `https://localhost:${BACKEND_PORT}`,
          changeOrigin: true,
          secure: false,
        },
      },
    },
    plugins: [
      react(),
    ],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
