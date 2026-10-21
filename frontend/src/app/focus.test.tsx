import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import { App } from "./App"
import { boardFixture } from "../test/board-fixture"

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  } as Response)
}

async function renderDemo() {
  vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, boardFixture)))
  render(<App />)
  expect(await screen.findByRole("columnheader", { name: "MARKET" })).toBeInTheDocument()
}

describe("mode focus", () => {
  it("moves focus to the CSV file input and back to USE CSV without trapping it", async () => {
    await renderDemo()
    const useCsv = screen.getByRole("button", { name: "USE CSV" })
    expect(useCsv).not.toHaveFocus()

    fireEvent.click(useCsv)
    const file = screen.getByLabelText("CSV FILE")
    expect(file).toHaveFocus()
    expect(document.body).not.toHaveFocus()

    const evaluation = screen.getByLabelText("EVALUATION DATE")
    evaluation.focus()
    expect(evaluation).toHaveFocus()
    expect(file).not.toHaveFocus()

    const asOf = screen.getByLabelText("AS-OF DATE")
    asOf.focus()
    expect(asOf).toHaveFocus()

    const back = screen.getByRole("button", { name: "RETURN TO DEMO" })
    expect(back).toBeEnabled()
    back.focus()
    expect(back).toHaveFocus()
    expect(file).not.toHaveFocus()
    fireEvent.click(back)
    const restored = screen.getByRole("button", { name: "USE CSV" })
    expect(restored).toHaveFocus()
    expect(document.body).not.toHaveFocus()
    expect(screen.queryByLabelText("CSV FILE")).not.toBeInTheDocument()
    expect(await screen.findByRole("table")).toBeInTheDocument()
    expect(restored).toHaveFocus()
    expect(document.getElementById("market-detail")).not.toHaveFocus()
  })
})
