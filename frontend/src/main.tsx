import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { AccessPage } from "./access/AccessPage"
import { PrivacyPage } from "./access/PrivacyPage"
import { App } from "./app/App"
import "./styles/global.css"

const root = document.getElementById("root")
if (!root) {
  throw new Error("root element is missing")
}
const path = window.location.pathname.replace(/\/$/, "") || "/"
const page = path === "/access" ? <AccessPage /> : path === "/privacy" ? <PrivacyPage /> : <App />
createRoot(root).render(<StrictMode>{page}</StrictMode>)
