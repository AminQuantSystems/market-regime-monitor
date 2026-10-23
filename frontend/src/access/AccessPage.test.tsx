import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { AccessPage, browser } from "./AccessPage"
import { PrivacyPage } from "./PrivacyPage"

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
  it("renders the request form", async () => {
    render(<AccessPage />)
    expect(screen.getByText("MARKET REGIME MONITOR")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Institutional Demonstration" })).toBeInTheDocument()
    expect(screen.getByLabelText("First name")).toBeInTheDocument()
    expect(screen.getByLabelText("Organisation")).toBeInTheDocument()
    expect(screen.getByText("Work email preferred.")).toBeInTheDocument()
    expect(screen.getByText(/administer demonstration access/)).toBeInTheDocument()
    expect(screen.getByText(/do not upload confidential, personal or client data/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Request Demo Access" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "End Demo Session" })).not.toBeInTheDocument()
    expect(screen.queryByText(/For your security, please end your demo session/)).not.toBeInTheDocument()
    expect(screen.queryByRole("link", { name: "Request Demo Access" })).not.toBeInTheDocument()
  })

  it("asks for the required details before sending an incomplete form", async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal("fetch", fetchMock)
    render(<AccessPage />)
    fireEvent.submit(screen.getByRole("button", { name: "Request Demo Access" }).closest("form") as HTMLFormElement)
    expect(await screen.findByText(/Enter the required details/)).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it("shows the verification instruction after a successful request", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { status: "verification_required" })))
    render(<AccessPage />)
    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Ada" } })
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "North" } })
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } })
    fireEvent.change(screen.getByLabelText("Organisation"), { target: { value: "North Yard" } })
    fireEvent.change(screen.getByLabelText("Role / Job title"), { target: { value: "Researcher" } })
    fireEvent.click(screen.getByRole("button", { name: "Request Demo Access" }))
    expect(await screen.findByText(/Check your email for a verification link/)).toBeInTheDocument()
    expect(JSON.stringify(localStorage)).not.toContain("ada@example.com")
  })

  it("shows a restrained failure when the request is not accepted", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(503, { error: { code: "DEMO_CRM_UNAVAILABLE" } })))
    render(<AccessPage />)
    fireEvent.change(screen.getByLabelText("First name"), { target: { value: "Ada" } })
    fireEvent.change(screen.getByLabelText("Last name"), { target: { value: "North" } })
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "ada@example.com" } })
    fireEvent.change(screen.getByLabelText("Organisation"), { target: { value: "North Yard" } })
    fireEvent.change(screen.getByLabelText("Role / Job title"), { target: { value: "Researcher" } })
    fireEvent.click(screen.getByRole("button", { name: "Request Demo Access" }))
    expect(await screen.findByText(/could not be requested/)).toBeInTheDocument()
  })

  it("exchanges a verification fragment, clears it, and does not store it", async () => {
    const token = "signed.verification"
    window.history.replaceState(null, "", `/access#verify=${token}`)
    const openHome = vi.spyOn(browser, "openHome").mockImplementation(() => undefined)
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { status: "ok" })))
    render(<AccessPage />)
    await waitFor(() => {
      expect(openHome).toHaveBeenCalled()
    })
    expect(window.location.hash).toBe("")
    expect(JSON.stringify(localStorage)).not.toContain(token)
    expect(JSON.stringify(sessionStorage)).not.toContain(token)
    const verify = vi.mocked(fetch).mock.calls.find((call) => String(call[0]).endsWith("/api/v1/demo-access/verify"))
    expect(verify?.[1]).toMatchObject({ method: "POST", credentials: "same-origin" })
    expect(String(verify?.[1]?.body)).toContain(token)
  })

  it("shows expired and invalid verification without keeping the fragment", async () => {
    window.history.replaceState(null, "", "/access#verify=old.token")
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(401, { error: { code: "DEMO_VERIFY_EXPIRED" } })))
    const expired = render(<AccessPage />)
    expect(await screen.findByText("This verification link has expired.")).toBeInTheDocument()
    expect(window.location.hash).toBe("")
    expired.unmount()
    window.history.replaceState(null, "", "/access#verify=bad.token")
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(401, { error: { code: "DEMO_VERIFY_INVALID" } })))
    render(<AccessPage />)
    expect(await screen.findByText("This verification link is not valid.")).toBeInTheDocument()
    expect(window.location.hash).toBe("")
  })

  it("still exchanges a manual invitation fragment", async () => {
    window.history.replaceState(null, "", "/access#token=signed.invitation")
    const openHome = vi.spyOn(browser, "openHome").mockImplementation(() => undefined)
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { status: "ok" })))
    render(<AccessPage />)
    await waitFor(() => {
      expect(openHome).toHaveBeenCalled()
    })
    expect(window.location.hash).toBe("")
    expect(vi.mocked(fetch).mock.calls.some((call) => String(call[0]).endsWith("/api/v1/auth/exchange"))).toBe(true)
  })
})

describe("privacy notice", () => {
  it("states the collected details and does not invent a postal address", async () => {
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse(200, { contact_email: null })))
    render(<PrivacyPage />)
    expect(screen.getByRole("heading", { name: "Demonstration privacy notice" })).toBeInTheDocument()
    expect(screen.getByText(/name, email address, organisation, role/)).toBeInTheDocument()
    expect(screen.getAllByText(/legitimate interests/)).toHaveLength(2)
    expect(screen.getByText(/right to object/)).toBeInTheDocument()
    expect(screen.getByText(/does not subscribe you to marketing/)).toBeInTheDocument()
    expect(screen.queryByText(/consent/i)).not.toBeInTheDocument()
    expect(screen.getByText(/HubSpot is used/)).toBeInTheDocument()
    expect(screen.getByText(/Microsoft Azure is used/)).toBeInTheDocument()
    expect(await screen.findByText(/Contact MEEM Technologies with questions/)).toBeInTheDocument()
    expect(screen.queryByText(/registered address/i)).not.toBeInTheDocument()
  })
})
