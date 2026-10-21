import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { displayTrendState } from "../design-system/semantics"
import type { TrendState } from "../types/board"
import { App } from "./App"
import { boardFixture } from "../test/board-fixture"

const mapping: Array<[TrendState, string]> = [
  ["Strong Up", "Strong Uptrend"],
  ["Up", "Uptrend"],
  ["Neutral", "Neutral"],
  ["Down", "Downtrend"],
  ["Strong Down", "Strong Downtrend"],
]

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(body),
  } as Response)
}

describe("public direction labels", () => {
  it("maps each internal trend state and leaves the API values unchanged", () => {
    for (const [state, label] of mapping) {
      expect(displayTrendState(state)).toBe(label)
    }
    expect(boardFixture.markets.map((market) => market.current.trend.trend_state)).toEqual([
      "Strong Up",
      "Strong Up",
      "Strong Down",
      "Up",
      "Down",
      "Neutral",
      "Strong Down",
    ])
  })

  it("shows public direction labels on the board and in direction transitions", async () => {
    const upToStrong = structuredClone(boardFixture)
    upToStrong.markets[0] = {
      ...upToStrong.markets[0],
      change: {
        status: "CHANGED",
        reason_code: "CHANGE_STATE_CHANGED",
        previous_as_of_date: "2026-02-28",
        transitions: [{ dimension: "direction", previous_state: "Up", current_state: "Strong Up" }],
      },
    }
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(upToStrong)))
    render(<App />)
    expect(await screen.findByRole("columnheader", { name: "DIRECTION" })).toBeInTheDocument()
    for (const [, label] of mapping) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
    expect(screen.queryByText("Strong Up")).not.toBeInTheDocument()
    expect(screen.queryByText("Strong Down")).not.toBeInTheDocument()

    const spy = within(document.getElementById("market-detail") as HTMLElement)
    expect(spy.getAllByText("Strong Uptrend").length).toBeGreaterThan(0)
    expect(spy.getByText("Uptrend")).toBeInTheDocument()
    expect(spy.getAllByRole("listitem")[0]).toHaveTextContent("Uptrend→Strong Uptrend")
    expect(upToStrong.markets[0].current.trend.trend_state).toBe("Strong Up")
    expect(upToStrong.markets[0].change.transitions[0]).toEqual({
      dimension: "direction",
      previous_state: "Up",
      current_state: "Strong Up",
    })

    fireEvent.click(screen.getByRole("button", { name: "Emerging Markets EEM" }))
    const emerging = within(document.getElementById("market-detail") as HTMLElement)
    const items = emerging.getAllByRole("listitem")
    expect(items[0]).toHaveTextContent("Downtrend→Strong Downtrend")
    expect(items[1]).toHaveTextContent("Mixed→Deteriorating")
    expect(items[2]).toHaveTextContent("Low→High")
    expect(items[3]).toHaveTextContent("Underperform→Strong Underperform")
  })
})
