import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { AccessPage } from "./access/AccessPage"
import { App } from "./app/App"
import "./styles/global.css"

const root = document.getElementById("root")
if (!root) {
  throw new Error("root element is missing")
}
const path = window.location.pathname.replace(/\/$/, "") || "/"
createRoot(root).render(
  <StrictMode>
    {path === "/access" ? <AccessPage /> : <App />}
  </StrictMode>,
)
