import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { App } from "./App"
import { boardFixture } from "../test/board-fixture"

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as Response)
}

async function renderBoard() {
  const fetchMock = vi.fn(() => jsonResponse(boardFixture))
  vi.stubGlobal("fetch", fetchMock)
  render(<App />)
  expect(await screen.findByRole("heading", { name: "S&P 500" })).toBeInTheDocument()
  return fetchMock
}

describe("official mark", () => {
  it("renders the approved standalone mark", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)))
    render(<App />)
    const mark = screen.getByRole("img", { name: "MEEM Technologies" })
    expect(mark).toHaveAttribute("src", "/brand/MEEM_Standalone_Mark_White.png")
  })
})

describe("market detail", () => {
  it("selects S&P 500 first and keeps the board order", async () => {
    const fetchMock = await renderBoard()
    const spy = screen.getByRole("button", { name: "S&P 500 SPY" })
    expect(spy).toHaveAttribute("aria-pressed", "true")
    expect(spy).toHaveAttribute("aria-controls", "market-detail")
    expect(screen.getByRole("button", { name: "Nasdaq 100 QQQ" })).toHaveAttribute("aria-pressed", "false")
    const before = screen.getAllByRole("rowheader").map((cell) => cell.textContent)
    fireEvent.click(screen.getByRole("button", { name: "Japan Equities EWJ" }))
    expect(screen.getAllByRole("rowheader").map((cell) => cell.textContent)).toEqual(before)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("shows fixture evidence for every detail section", async () => {
    await renderBoard()
    const detail = within(document.getElementById("market-detail") as HTMLElement)
    expect(detail.getByRole("heading", { level: 2, name: "S&P 500" })).toBeInTheDocument()
    expect(detail.getByText("SPY")).toBeInTheDocument()
    expect(detail.getByText("AS OF 2026-03-01")).toBeInTheDocument()
    expect(detail.getByRole("heading", { name: "DIRECTION" })).toBeInTheDocument()
    expect(detail.getByText("Strong Up")).toBeInTheDocument()
    expect(detail.getByText("111111.11")).toBeInTheDocument()
    expect(detail.queryByText("TREND SCORE")).not.toBeInTheDocument()
    expect(detail.queryByText("Categorical trend score from -2 to 2. Not a composite regime score.")).not.toBeInTheDocument()
    expect(detail.getByRole("heading", { name: "MOMENTUM" })).toBeInTheDocument()
    expect(detail.getByText("Positive")).toBeInTheDocument()
    expect(detail.getByText("22222222.20%")).toBeInTheDocument()
    expect(detail.getByRole("heading", { name: "VOLATILITY" })).toBeInTheDocument()
    expect(detail.getByText("Low")).toBeInTheDocument()
    expect(detail.getByText("444444.4")).toBeInTheDocument()
    expect(detail.getByRole("heading", { name: "RELATIVE PERFORMANCE" })).toBeInTheDocument()
    expect(detail.getByText("Outperform")).toBeInTheDocument()
    expect(detail.getByText("ACWI")).toBeInTheDocument()
    expect(detail.getByText("55555555.50%")).toBeInTheDocument()
    expect(detail.getAllByText("REASON_SHOULD_NOT_RENDER").length).toBe(4)
  })

  it("states an unchanged market without inventing transitions", async () => {
    await renderBoard()
    const detail = within(document.getElementById("market-detail") as HTMLElement)
    expect(detail.getByText("NO MARKET-STATE CHANGE SINCE PREVIOUS SESSION")).toBeInTheDocument()
    expect(detail.getByText("2026-02-28")).toBeInTheDocument()
    expect(detail.getByText("CHANGE_NO_STATE_CHANGE")).toBeInTheDocument()
    expect(detail.queryByRole("list")).not.toBeInTheDocument()
  })

  it("lists every changed dimension in order", async () => {
    await renderBoard()
    fireEvent.click(screen.getByRole("button", { name: "Emerging Markets EEM" }))
    const detail = within(document.getElementById("market-detail") as HTMLElement)
    const labels = detail.getAllByRole("listitem").map((item) => item.querySelector("p")?.textContent)
    expect(labels).toEqual(["DIRECTION", "MOMENTUM", "VOLATILITY", "RELATIVE PERFORMANCE"])
    expect(detail.getAllByRole("listitem")[0]).toHaveTextContent("Down→Strong Down")
    expect(detail.getAllByText("→")).toHaveLength(4)
    expect(detail.getByText("CHANGE_STATE_CHANGED")).toBeInTheDocument()
  })

  it("does not invent a previous session when change is unavailable", async () => {
    await renderBoard()
    fireEvent.click(screen.getByRole("button", { name: "Germany Equities EWG" }))
    const detail = within(document.getElementById("market-detail") as HTMLElement)
    expect(detail.getByText("PREVIOUS STATE UNAVAILABLE")).toBeInTheDocument()
    expect(detail.getByText("CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY")).toBeInTheDocument()
    expect(detail.queryByText("2026-02-28")).not.toBeInTheDocument()
    expect(detail.queryByRole("list")).not.toBeInTheDocument()
    expect(detail.queryByText("NO MARKET-STATE CHANGE SINCE PREVIOUS SESSION")).not.toBeInTheDocument()
  })

  it("leaves focus on the market button", async () => {
    await renderBoard()
    const button = screen.getByRole("button", { name: "UK Equities EWU" })
    button.focus()
    fireEvent.click(button)
    expect(button).toHaveAttribute("aria-pressed", "true")
    expect(document.activeElement).toBe(button)
  })
})
