import { readFileSync, readdirSync, statSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ChangeCell } from "../components/ChangeCell"
import { presentMomentum, presentRelative, presentTrend, presentVolatility } from "../design-system/semantics"
import type { ChangeReading, MomentumState, RelativePerformanceState, TrendState, VolatilityRegime } from "../types/board"
import { App } from "./App"
import { boardFixture, hiddenMeasurements } from "../test/board-fixture"

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  } as Response)
}

describe("Market State Board", () => {
  it("renders the demo board from the API contract", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, boardFixture)))
    render(<App />)
    expect(await screen.findByRole("columnheader", { name: "MARKET" })).toBeInTheDocument()
    const headings = screen.getAllByRole("columnheader").map((heading) => heading.textContent)
    expect(headings).toEqual(["MARKET", "DIRECTION", "MOMENTUM", "VOL", "RELATIVE", "CHANGE"])
    const markets = screen.getAllByRole("rowheader").map((cell) => cell.textContent)
    expect(markets).toEqual([
      "S&P 500SPY",
      "Nasdaq 100QQQ",
      "Russell 2000IWM",
      "UK EquitiesEWU",
      "Germany EquitiesEWG",
      "Japan EquitiesEWJ",
      "Emerging MarketsEEM",
    ])
    expect(screen.queryByRole("rowheader", { name: /ACWI/ })).not.toBeInTheDocument()
    expect(screen.getAllByText("Strong Up").length).toBeGreaterThan(0)
    expect(screen.getByText("Accelerating")).toBeInTheDocument()
    expect(screen.getAllByText("Deteriorating").length).toBeGreaterThan(0)
    expect(screen.getByText("Elevated")).toBeInTheDocument()
    expect(screen.getAllByText("Strong Underperform").length).toBeGreaterThan(0)
    expect(screen.getByText("Negative")).toBeInTheDocument()
    expect(screen.getByText("M", { exact: true })).toBeInTheDocument()
    expect(screen.getByText("D M V R")).toBeInTheDocument()
    expect(screen.getAllByText("—").length).toBeGreaterThan(0)
    expect(screen.getByText("N/A")).toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByText("2026-03-01")).toBeInTheDocument()
    const text = document.body.textContent ?? ""
    for (const hidden of hiddenMeasurements) {
      expect(text).not.toContain(hidden)
    }
    expect(screen.queryByText("ANALYSING MARKET STATE…")).not.toBeInTheDocument()
  })

  it("shows the loading status while the request is pending", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)))
    render(<App />)
    expect(screen.getByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
  })

  it("replaces the board with the API error", async () => {
    vi.stubGlobal("fetch", vi.fn(() =>
      jsonResponse(422, {
        error: {
          code: "DATA_DATE_INDEX_MISMATCH",
          message: "QQQ does not share the date index of ACWI",
          category: "market_data",
        },
      }),
    ))
    render(<App />)
    expect(await screen.findByRole("alert")).toHaveTextContent("MARKET DATA COULD NOT BE ANALYSED")
    expect(screen.getByText("DATA_DATE_INDEX_MISMATCH")).toBeInTheDocument()
    expect(screen.getByText("QQQ does not share the date index of ACWI")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByText("N/A")).not.toBeInTheDocument()
  })
})

describe("change labels", () => {
  it("renders an unavailable change without a judgement", () => {
    const change: ChangeReading = {
      status: "UNAVAILABLE",
      reason_code: "CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY",
      previous_as_of_date: null,
      transitions: [],
    }
    render(<ChangeCell change={change} />)
    expect(screen.getByText("N/A")).toBeInTheDocument()
  })
})

describe("semantic mapping", () => {
  it("covers every approved label and keeps strong states in the same family", () => {
    const trends: TrendState[] = ["Strong Up", "Up", "Neutral", "Down", "Strong Down"]
    const momenta: MomentumState[] = ["Accelerating", "Positive", "Mixed", "Negative", "Deteriorating"]
    const regimes: VolatilityRegime[] = ["Low", "Normal", "Elevated", "High"]
    const relatives: RelativePerformanceState[] = [
      "Strong Outperform",
      "Outperform",
      "Neutral",
      "Underperform",
      "Strong Underperform",
    ]
    expect(trends.map((state) => presentTrend(state).semantic)).toEqual([
      "positive",
      "positive",
      "neutral",
      "negative",
      "negative",
    ])
    expect(presentTrend("Strong Up").emphasis).toBe("strong")
    expect(presentTrend("Up").emphasis).toBe("base")
    expect(momenta.map((state) => presentMomentum(state).semantic)).toEqual([
      "positive",
      "positive",
      "neutral",
      "negative",
      "negative",
    ])
    expect(regimes.map((state) => presentVolatility(state).semantic)).toEqual([
      "neutral",
      "neutral",
      "attention",
      "attention",
    ])
    expect(presentVolatility("High").emphasis).toBe("strong")
    expect(presentVolatility("Elevated").emphasis).toBe("base")
    expect(relatives.map((state) => presentRelative(state).semantic)).toEqual([
      "positive",
      "positive",
      "neutral",
      "negative",
      "negative",
    ])
    expect(presentRelative("Strong Outperform").semantic).toBe(presentRelative("Outperform").semantic)
    expect(presentRelative("Strong Underperform").semantic).toBe(presentRelative("Underperform").semantic)
  })
})

describe("design tokens", () => {
  it("keeps generated CSS current and keeps hex values out of components", () => {
    const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "../..")
    const generated = readFileSync(join(frontend, "src/design-system/tokens.generated.css"), "utf8")
    expect(generated.startsWith("/* DO NOT EDIT — GENERATED FROM MEEM_DESIGN_TOKENS.json */")).toBe(true)
    expect(generated).toContain("--meem-dark-canvas: #0D0D0D;")
    expect(generated).toContain("--meem-semantic-positive-dark: #2EA579;")
    expect(generated).toContain("--meem-brand-deep-sapphire: #052689;")
    const source = readFileSync(resolve(frontend, "../MEEM_DESIGN_TOKENS.json"), "utf8")
    const fresh = generated
    expect(source).toContain('"#0D0D0D"')
    expect(fresh).toContain("#0D0D0D")
    const roots = ["src/components", "src/app", "src/styles"].map((folder) => join(frontend, folder))
    const files = roots
      .flatMap((folder) => collect(folder))
      .filter((file) => (file.endsWith(".css") || file.endsWith(".tsx")) && !file.endsWith(".test.tsx"))
    for (const file of files) {
      expect(readFileSync(file, "utf8")).not.toMatch(/#[0-9A-Fa-f]{3,8}\b/)
    }
  })
})

function collect(folder: string): string[] {
  return readdirSync(folder).flatMap((name) => {
    const path = join(folder, name)
    return statSync(path).isDirectory() ? collect(path) : [path]
  })
}
