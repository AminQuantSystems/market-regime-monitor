import { act, fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { DEMO_AS_OF_DATE, DEMO_EVALUATION_DATE } from "../demo"
import type { BoardResponse } from "../types/board"
import { CLIENT_UPLOAD_BYTE_LIMIT } from "../upload-checks"
import { App } from "./App"
import { boardFixture } from "../test/board-fixture"

const uploadFixture: BoardResponse = {
  ...boardFixture,
  as_of_date: "2024-06-03",
  evaluation_date: "2024-06-03",
  data_source: "upload",
  data_label: null,
  markets: [boardFixture.markets[1], boardFixture.markets[0], ...boardFixture.markets.slice(2)],
}

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  } as Response)
}

function deferredResponse() {
  let resolve: (value: Response) => void = () => undefined
  const promise = new Promise<Response>((next) => {
    resolve = next
  })
  return { promise, resolve }
}

async function renderDemo() {
  render(<App />)
  expect(await screen.findByRole("columnheader", { name: "MARKET" })).toBeInTheDocument()
}

function chooseFile(file: File) {
  fireEvent.change(screen.getByLabelText("CSV FILE"), { target: { files: [file] } })
}

function setDates(evaluationDate: string, asOfDate: string) {
  fireEvent.change(screen.getByLabelText("EVALUATION DATE"), { target: { value: evaluationDate } })
  fireEvent.change(screen.getByLabelText("AS-OF DATE"), { target: { value: asOfDate } })
}

describe("CSV analysis", () => {
  it("opens CSV controls without replacing the demo result", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, boardFixture)))
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    expect(screen.getByLabelText("CSV FILE")).toBeInTheDocument()
    expect(screen.getByLabelText("EVALUATION DATE")).toHaveValue("")
    expect(screen.getByLabelText("AS-OF DATE")).toHaveValue("")
    expect(screen.getByRole("button", { name: "ANALYSE CSV" })).toBeDisabled()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByText("Synthetic demonstration. Not a live feed.")).toBeInTheDocument()
    expect(screen.getByRole("table")).toBeInTheDocument()
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1)
  })

  it("keeps Analyse CSV disabled until a csv file and both dates are present", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, boardFixture)))
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    const analyse = screen.getByRole("button", { name: "ANALYSE CSV" })
    expect(analyse).toBeDisabled()

    chooseFile(new File(["notes"], "notes.txt", { type: "text/plain" }))
    expect(screen.getByText("Choose a file whose name ends in .csv.")).toBeInTheDocument()
    expect(analyse).toBeDisabled()

    chooseFile(new File([new Uint8Array(CLIENT_UPLOAD_BYTE_LIMIT + 1)], "large.csv", { type: "text/csv" }))
    expect(screen.getByText("This file is larger than 5 MiB.")).toBeInTheDocument()
    expect(analyse).toBeDisabled()

    chooseFile(new File(["date,market_id,adjusted_close\n"], "market_data.csv", { type: "text/csv" }))
    setDates("2026-03-06", "")
    expect(analyse).toBeDisabled()
    setDates("2026-03-06", "2026-02-27")
    expect(analyse).toBeEnabled()
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1)
  })

  it("submits the selected file and date strings without reading the file", async () => {
    const pending = deferredResponse()
    const bodies: FormData[] = []
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        bodies.push(init.body as FormData)
        if (bodies.length === 1) {
          return jsonResponse(200, boardFixture)
        }
        return pending.promise
      }),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    const file = new File(["date,market_id,adjusted_close\n"], "portfolio_market_data.csv", { type: "text/csv" })
    chooseFile(file)
    setDates("2026-03-06", "2026-02-27")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))

    expect(screen.getByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")
    expect(screen.getAllByText("CSV UPLOAD").length).toBeGreaterThan(0)
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByText("DEMO DATA")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/fakepath/i)
    expect(screen.getAllByTitle("portfolio_market_data.csv").length).toBeGreaterThan(0)
    expect(screen.getAllByText("portfolio_market_data.csv").every((node) => node.textContent === "portfolio_market_data.csv")).toBe(true)

    expect(bodies[1].get("data_source")).toBe("upload")
    expect(bodies[1].get("evaluation_date")).toBe("2026-03-06")
    expect(bodies[1].get("as_of_date")).toBe("2026-02-27")
    expect(bodies[1].get("prices")).toBe(file)

    pending.resolve(await jsonResponse(200, uploadFixture))
    expect(await screen.findByText("UPLOADED CSV")).toBeInTheDocument()
  })

  it("renders the uploaded response and selects its first market", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(await jsonResponse(200, boardFixture))
        .mockResolvedValueOnce(await jsonResponse(200, uploadFixture)),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "S&P 500 SPY" }))
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    const file = new File(["date,market_id,adjusted_close\n"], "market_data.csv", { type: "text/csv" })
    chooseFile(file)
    setDates("2025-11-03", "2025-12-01")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))

    expect(await screen.findByText("UPLOADED CSV")).toBeInTheDocument()
    expect(screen.getAllByText("market_data.csv").length).toBeGreaterThan(0)
    expect(screen.queryByText("DEMO DATA")).not.toBeInTheDocument()
    expect(screen.queryByText("Synthetic demonstration. Not a live feed.")).not.toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByText("2024-06-03")).toBeInTheDocument()
    expect(screen.queryByText("2025-12-01")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Nasdaq 100 QQQ" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "false")
    const detail = document.getElementById("market-detail")
    expect(detail).not.toBeNull()
    expect(within(detail as HTMLElement).getByRole("heading", { name: "Nasdaq 100" })).toBeInTheDocument()
    expect(within(detail as HTMLElement).getAllByText("Accelerating").length).toBeGreaterThan(0)
  })

  it("replaces the board with an upload error and keeps the entered dates", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(await jsonResponse(200, boardFixture))
        .mockResolvedValueOnce(
          await jsonResponse(422, {
            error: {
              code: "DATA_INVALID_COLUMNS",
              message: "Price columns must be date, market_id, adjusted_close",
              category: "market_data",
            },
          }),
        ),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["bad"], "broken.csv", { type: "text/csv" }))
    setDates("2026-03-06", "2026-02-27")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))

    expect(await screen.findByRole("alert")).toHaveTextContent("MARKET DATA COULD NOT BE ANALYSED")
    expect(screen.getByText("DATA_INVALID_COLUMNS")).toBeInTheDocument()
    expect(screen.getByText("Price columns must be date, market_id, adjusted_close")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByText("DEMO DATA")).not.toBeInTheDocument()
    expect(screen.queryByText("N/A")).not.toBeInTheDocument()
    expect(screen.getAllByText("CSV UPLOAD").length).toBeGreaterThan(0)
    expect(screen.getByLabelText("CSV FILE")).toBeInTheDocument()
    expect(screen.getByLabelText("EVALUATION DATE")).toHaveValue("2026-03-06")
    expect(screen.getByLabelText("AS-OF DATE")).toHaveValue("2026-02-27")
    expect(screen.getAllByText("broken.csv").length).toBeGreaterThan(0)
    expect(screen.getByRole("button", { name: "ANALYSE CSV" })).toBeEnabled()
  })

  it("returns from an uploaded result to the bundled demo", async () => {
    const pending = deferredResponse()
    const bodies: FormData[] = []
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        bodies.push(init.body as FormData)
        if (bodies.length === 1) {
          return jsonResponse(200, boardFixture)
        }
        if (bodies.length === 2) {
          return jsonResponse(200, uploadFixture)
        }
        return pending.promise
      }),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["date,market_id,adjusted_close\n"], "market_data.csv", { type: "text/csv" }))
    setDates("2025-11-03", "2025-12-01")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))
    expect(await screen.findByText("UPLOADED CSV")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "RETURN TO DEMO" }))
    expect(screen.getByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("CSV FILE")).not.toBeInTheDocument()
    expect(bodies[2].get("data_source")).toBe("demo")
    expect(bodies[2].get("evaluation_date")).toBe(DEMO_EVALUATION_DATE)
    expect(bodies[2].get("as_of_date")).toBe(DEMO_AS_OF_DATE)
    expect(bodies[2].get("prices")).toBeNull()

    pending.resolve(await jsonResponse(200, boardFixture))
    expect(await screen.findByRole("table")).toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("CSV UPLOAD")).not.toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.getByRole("button", { name: "USE CSV" })).toBeInTheDocument()
  })

  it("returns to the demo from an upload error without reloading the page", async () => {
    const bodies: FormData[] = []
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init: RequestInit) => {
        bodies.push(init.body as FormData)
        if (bodies.length === 1) {
          return jsonResponse(200, boardFixture)
        }
        if (bodies.length === 2) {
          return jsonResponse(422, {
            error: {
              code: "DATA_INVALID_PRICE",
              message: "SPY adjusted_close is not a positive price",
              category: "market_data",
            },
          })
        }
        return jsonResponse(200, boardFixture)
      }),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["x"], "broken.CSV", { type: "text/csv" }))
    setDates("2026-03-06", "2026-03-06")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))
    expect(await screen.findByText("DATA_INVALID_PRICE")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "RETURN TO DEMO" }))
    expect(await screen.findByRole("table")).toBeInTheDocument()
    expect(bodies[2].get("data_source")).toBe("demo")
    expect(bodies[2].get("evaluation_date")).toBe("2026-03-06")
    expect(bodies[2].get("as_of_date")).toBe("2026-03-06")
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(screen.queryByText("DATA_INVALID_PRICE")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "true")
  })

  it("shows a transport failure without keeping the previous board", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(await jsonResponse(200, boardFixture))
        .mockRejectedValueOnce(new TypeError("network down")),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["date,market_id,adjusted_close\n"], "market_data.csv", { type: "text/csv" }))
    setDates("2026-03-06", "2026-02-27")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))

    expect(await screen.findByText("API_UNEXPECTED")).toBeInTheDocument()
    expect(screen.getByText("The analysis could not be completed.")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByText("DEMO DATA")).not.toBeInTheDocument()
    expect(screen.getByLabelText("EVALUATION DATE")).toHaveValue("2026-03-06")
    expect(screen.getByLabelText("AS-OF DATE")).toHaveValue("2026-02-27")
  })

  it("does not show a stale upload that resolves after Return to Demo", async () => {
    const upload = deferredResponse()
    const demo = deferredResponse()
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementationOnce(() => jsonResponse(200, boardFixture))
        .mockImplementationOnce(() => upload.promise)
        .mockImplementationOnce(() => demo.promise),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["date,market_id,adjusted_close\n"], "late.csv", { type: "text/csv" }))
    setDates("2024-06-03", "2024-06-03")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))
    expect(await screen.findByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")

    fireEvent.click(screen.getByRole("button", { name: "RETURN TO DEMO" }))
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.queryByText("late.csv")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()

    await act(async () => {
      upload.resolve(await jsonResponse(200, uploadFixture))
    })
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("late.csv")).not.toBeInTheDocument()
    expect(screen.queryByText("2024-06-03")).not.toBeInTheDocument()
    expect(screen.queryByText("VALID")).not.toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")

    await act(async () => {
      demo.resolve(await jsonResponse(200, boardFixture))
    })
    expect(await screen.findByRole("table")).toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("late.csv")).not.toBeInTheDocument()
    expect(screen.queryByText("2024-06-03")).not.toBeInTheDocument()
  })

  it("keeps the newer analysis when an older response resolves last", async () => {
    const older = deferredResponse()
    const newer = deferredResponse()
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementationOnce(() => jsonResponse(200, boardFixture))
        .mockImplementationOnce(() => older.promise)
        .mockImplementationOnce(() => newer.promise),
    )
    await renderDemo()
    fireEvent.click(screen.getByRole("button", { name: "USE CSV" }))
    chooseFile(new File(["date,market_id,adjusted_close\n"], "older.csv", { type: "text/csv" }))
    setDates("2024-06-03", "2024-06-03")
    fireEvent.click(screen.getByRole("button", { name: "ANALYSE CSV" }))
    expect(await screen.findByRole("status")).toHaveTextContent("ANALYSING MARKET STATE…")
    fireEvent.click(screen.getByRole("button", { name: "RETURN TO DEMO" }))

    await act(async () => {
      newer.resolve(await jsonResponse(200, boardFixture))
    })
    expect(await screen.findByRole("table")).toBeInTheDocument()
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "true")

    await act(async () => {
      older.resolve(await jsonResponse(200, uploadFixture))
    })
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument()
    expect(screen.getByText("VALID")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "S&P 500 SPY" })).toHaveAttribute("aria-pressed", "true")
    expect(screen.queryByText("UPLOADED CSV")).not.toBeInTheDocument()
    expect(screen.queryByText("older.csv")).not.toBeInTheDocument()
    expect(screen.queryByText("2024-06-03")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Nasdaq 100 QQQ" })).toHaveAttribute("aria-pressed", "false")
  })
})
