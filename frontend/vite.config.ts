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

// The backend this dev server proxies to. `:8000` is the dev default and stays
// the default, so an ordinary `npm run dev` is unchanged.
//
// It is overridable because the Playwright e2e leg boots its *own* disposable
// backend and the proxy has to follow it there. Hardcoded, that leg could only
// run on a machine where nothing else holds `:8000` — and on a machine where
// something does, it does not fail cleanly: `stack.boot` health-checks the
// port, finds the *other* instance answering, and POSTs its admin-setup at it.
// Against an uninitialised instance that would seed an admin password on a
// system the gate does not own. One variable, read on both sides, removes that.
const API_TARGET = process.env.E2E_API_TARGET ?? "http://localhost:8000"

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
      "/api": { target: API_TARGET, agent: noKeepAliveAgent },
      "/health": { target: API_TARGET, agent: noKeepAliveAgent },
      // Settings -> Integration advertises `${origin}/mcp/` as the endpoint;
      // without this the dev server answered it with a 404.
      "/mcp": { target: API_TARGET, agent: noKeepAliveAgent },
      "/ws": { target: API_TARGET.replace(/^http/, "ws"), ws: true },
    },
  },
})
