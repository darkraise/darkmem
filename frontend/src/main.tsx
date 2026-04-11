import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { App } from "./app"
import { suppressUpstreamDarkraiseWarnings } from "./lib/suppress-upstream-warnings"
import "./styles/globals.css"

suppressUpstreamDarkraiseWarnings()

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
