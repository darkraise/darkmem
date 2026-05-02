import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { tanstackRouter } from "@tanstack/router-plugin/vite"
import path from "node:path"
import http from "node:http"

// Disable HTTP keep-alive on the dev proxy → backend hop. Vite's
// http-proxy reuses sockets from Node's global agent, but uvicorn
// closes idle keep-alive sockets after 5s; reusing one of those
// dead sockets surfaces as a sporadic 502 Bad Gateway on the first
// request after the user spends a few seconds idle on a page (e.g.
// typing an API key in the setup wizard before clicking Fetch).
const noKeepAliveAgent = new http.Agent({ keepAlive: false })

export default defineConfig({
  plugins: [
    tanstackRouter({
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routeTree.gen.ts",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3636,
    allowedHosts: ["host.docker.internal"],
    proxy: {
      "/api": { target: "http://localhost:8000", agent: noKeepAliveAgent },
      "/health": { target: "http://localhost:8000", agent: noKeepAliveAgent },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
})
