import { readFileSync, writeFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const tokens = JSON.parse(readFileSync(resolve(here, "../../MEEM_DESIGN_TOKENS.json"), "utf8"))
const lines = ["/* DO NOT EDIT — GENERATED FROM MEEM_DESIGN_TOKENS.json */", ":root {"]

function variable(parts) {
  return "--meem-" + parts.join("-").replaceAll("_", "-")
}

for (const [key, value] of Object.entries(tokens.brand)) {
  if (value && typeof value.hex === "string") {
    lines.push(`  ${variable(["brand", key])}: ${value.hex};`)
  }
}
for (const [theme, values] of Object.entries(tokens.application)) {
  for (const [key, hex] of Object.entries(values)) {
    lines.push(`  ${variable([theme, key])}: ${hex};`)
  }
}
for (const [meaning, values] of Object.entries(tokens.semantic)) {
  for (const [theme, hex] of Object.entries(values)) {
    lines.push(`  ${variable(["semantic", meaning, theme])}: ${hex};`)
  }
}
lines.push("}", "")
writeFileSync(resolve(here, "../src/design-system/tokens.generated.css"), lines.join("\n"), "utf8")
