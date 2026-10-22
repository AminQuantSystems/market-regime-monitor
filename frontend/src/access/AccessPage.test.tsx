import { render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { AccessPage, browser } from "./AccessPage"

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  } as Response)
}

afterEach(() => {
  vi.restoreAllMocks()
  window.history.replaceState(null, "", "/")
  localStorage.clear()
  sessionStorage.clear()
  vi.unstubAllGlobals()
})

describe("demonstration access page", () => {
  it("renders the institutional request screen", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { contact_email: "reviews@example.com" })))
    render(<AccessPage />)
    expect(screen.getByText("MARKET REGIME MONITOR")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Institutional Demonstration" })).toBeInTheDocument()
    expect(screen.getByText(/deterministic market-state analytics application/)).toBeInTheDocument()
    expect(screen.getByText(/No investment recommendation, trade signal or price prediction/)).toBeInTheDocument()
    const request = await screen.findByRole("link", { name: "Request Demo Access" })
    expect(request.getAttribute("href")).toContain("mailto:reviews@example.com")
    expect(request.getAttribute("href")).toContain(encodeURIComponent("Market Regime Monitor — Demo Access Request"))
    expect(request.getAttribute("href")).toContain(encodeURIComponent("Organisation:"))
  })

  it("does not offer a broken mailto link when no contact address is configured", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { contact_email: null })))
    render(<AccessPage />)
    expect(await screen.findByText("Contact MEEM Technologies to request demonstration access.")).toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Request Demo Access" })).not.toBeInTheDocument()
  })

  it("exchanges a fragment token, clears the fragment, and does not store it", async () => {
    const token = "signed.invitation"
    window.history.replaceState(null, "", `/access#token=${token}`)
    const openHome = vi.spyOn(browser, "openHome").mockImplementation(() => undefined)
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.endsWith("/api/v1/auth/exchange")) {
          return jsonResponse(200, { status: "ok" })
        }
        return jsonResponse(200, { contact_email: null })
      }),
    )
    render(<AccessPage />)
    await waitFor(() => {
      expect(openHome).toHaveBeenCalled()
    })
    expect(window.location.hash).toBe("")
    expect(window.location.pathname).toBe("/access")
    expect(localStorage.getItem("token")).toBeNull()
    expect(sessionStorage.getItem("token")).toBeNull()
    expect(JSON.stringify(localStorage)).not.toContain(token)
    expect(JSON.stringify(sessionStorage)).not.toContain(token)
    const exchange = vi.mocked(fetch).mock.calls.find((call) => String(call[0]).endsWith("/api/v1/auth/exchange"))
    expect(exchange?.[1]).toMatchObject({ method: "POST", credentials: "same-origin" })
    expect(String(exchange?.[1]?.body)).toContain(token)
  })

  it("shows an invalid invitation without keeping the fragment", async () => {
    window.history.replaceState(null, "", "/access#token=bad.token")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        if (String(input).endsWith("/api/v1/auth/exchange")) {
          return jsonResponse(401, { error: { code: "DEMO_INVITE_INVALID", message: "This invitation is not valid." } })
        }
        return jsonResponse(200, { contact_email: null })
      }),
    )
    render(<AccessPage />)
    expect(await screen.findByText("This invitation is not valid.")).toBeInTheDocument()
    expect(window.location.hash).toBe("")
  })

  it("shows an expired invitation", async () => {
    window.history.replaceState(null, "", "/access#token=old.token")
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        if (String(input).endsWith("/api/v1/auth/exchange")) {
          return jsonResponse(401, { error: { code: "DEMO_INVITE_EXPIRED", message: "This invitation has expired." } })
        }
        return jsonResponse(200, { contact_email: null })
      }),
    )
    render(<AccessPage />)
    expect(await screen.findByText("This invitation has expired.")).toBeInTheDocument()
  })
})
