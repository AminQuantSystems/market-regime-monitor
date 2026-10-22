import { FormEvent, useEffect, useState } from "react"
import styles from "./AccessPage.module.css"

type View = "loading" | "request" | "submitted" | "failed" | "invalid" | "expired" | "verifyInvalid" | "verifyExpired" | "verifyUsed"

export const browser = {
  clearFragment() {
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`)
  },
  openHome() {
    window.location.assign("/")
  },
}

function readFragment(prefix: string): string | null {
  const hash = window.location.hash
  if (!hash.startsWith(prefix) || hash.length === prefix.length) {
    return null
  }
  try {
    return decodeURIComponent(hash.slice(prefix.length))
  } catch {
    return ""
  }
}

async function postToken(path: string, token: string): Promise<string> {
  browser.clearFragment()
  const response = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    credentials: "same-origin",
    body: JSON.stringify({ token }),
  })
  if (response.ok) {
    browser.openHome()
    return "loading"
  }
  const payload = (await response.json().catch(() => null)) as { error?: { code?: string } } | null
  return payload?.error?.code ?? "invalid"
}

function emailAccepted(value: string): boolean {
  const email = value.trim()
  if (email.length === 0 || email.length > 254 || /\s/.test(email)) {
    return false
  }
  const parts = email.split("@")
  return parts.length === 2 && parts[0].length > 0 && parts[1].includes(".") && !parts[1].startsWith(".") && !parts[1].endsWith(".")
}

export function AccessPage() {
  const [view, setView] = useState<View>("loading")
  const [notice, setNotice] = useState("")

  useEffect(() => {
    const verification = readFragment("#verify=")
    const invitation = readFragment("#token=")
    if (verification === "") {
      browser.clearFragment()
      setView("verifyInvalid")
      return
    }
    const token = verification ?? invitation
    if (token === null) {
      setView("request")
      return
    }
    if (token === "") {
      browser.clearFragment()
      setView("invalid")
      return
    }
    const path = verification !== null ? "/api/v1/demo-access/verify" : "/api/v1/auth/exchange"
    let cancelled = false
    void postToken(path, token)
      .then((code) => {
        if (cancelled) {
          return
        }
        if (code === "DEMO_INVITE_EXPIRED" || code === "DEMO_VERIFY_EXPIRED") {
          setView(verification !== null ? "verifyExpired" : "expired")
          return
        }
        if (code === "DEMO_VERIFY_USED") {
          setView("verifyUsed")
          return
        }
        if (code === "loading") {
          setView("loading")
          return
        }
        setView(verification !== null ? "verifyInvalid" : "invalid")
      })
      .catch(() => {
        if (!cancelled) {
          setView(verification !== null ? "verifyInvalid" : "invalid")
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const payload = {
      first_name: String(form.get("first_name") ?? ""),
      last_name: String(form.get("last_name") ?? ""),
      email: String(form.get("email") ?? ""),
      organisation: String(form.get("organisation") ?? ""),
      role: String(form.get("role") ?? ""),
      interest: String(form.get("interest") ?? ""),
      website: String(form.get("website") ?? ""),
    }
    if (payload.website.trim() === "") {
      const required = [payload.first_name, payload.last_name, payload.email, payload.organisation, payload.role]
      if (required.some((value) => value.trim() === "") || !emailAccepted(payload.email)) {
        setNotice("Enter the required details. Use a valid email address.")
        return
      }
    }
    setNotice("")
    try {
      const response = await fetch("/api/v1/demo-access/request", {
        method: "POST",
        headers: { "content-type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      })
      if (response.ok) {
        setView("submitted")
        return
      }
      if (response.status === 429) {
        setNotice("Please wait before requesting demonstration access again.")
        return
      }
      setView("failed")
    } catch {
      setView("failed")
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <img className={styles.mark} src="/brand/MEEM_Standalone_Mark_White.png" alt="MEEM Technologies" width={263} height={469} />
        <p className={styles.product}>MARKET REGIME MONITOR</p>
        <h1 className={styles.title}>Institutional Demonstration</h1>
        <p className={styles.copy}>
          Market Regime Monitor is a deterministic market-state analytics application developed by MEEM Technologies.
        </p>
        <p className={styles.copy}>Interactive access is issued individually for evaluation and technical review.</p>
        {view === "expired" ? <p className={styles.notice}>This invitation has expired.</p> : null}
        {view === "verifyExpired" ? <p className={styles.notice}>This verification link has expired.</p> : null}
        {view === "invalid" ? <p className={styles.notice}>This invitation is not valid.</p> : null}
        {view === "verifyInvalid" ? <p className={styles.notice}>This verification link is not valid.</p> : null}
        {view === "verifyUsed" ? <p className={styles.notice}>This verification link has already been used.</p> : null}
        {view === "submitted" ? (
          <p className={styles.notice}>Check your email for a verification link. It expires in 30 minutes.</p>
        ) : null}
        {view === "failed" ? (
          <p className={styles.notice}>Demonstration access could not be requested. Please try again later.</p>
        ) : null}
        {view === "request" || view === "failed" ? (
          <form className={styles.form} onSubmit={(event) => void submit(event)}>
            <label>
              First name
              <input name="first_name" autoComplete="given-name" required maxLength={100} />
            </label>
            <label>
              Last name
              <input name="last_name" autoComplete="family-name" required maxLength={100} />
            </label>
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required maxLength={254} />
            </label>
            <span className={styles.support}>Work email preferred.</span>
            <label>
              Organisation
              <input name="organisation" autoComplete="organization" required maxLength={200} />
            </label>
            <label>
              Role / Job title
              <input name="role" autoComplete="organization-title" required maxLength={200} />
            </label>
            <label>
              What would you like to evaluate?
              <textarea name="interest" maxLength={1000} />
            </label>
            <label className={styles.honeypot} aria-hidden="true">
              Website
              <input name="website" tabIndex={-1} autoComplete="off" />
            </label>
            {notice ? <p className={styles.notice}>{notice}</p> : null}
            <button className={styles.request} type="submit">
              Request Demo Access
            </button>
            <p className={styles.support}>Your details will be used to administer demonstration access and follow up regarding this request.</p>
            <p className={styles.support}>Public demonstration — do not upload confidential, personal or client data.</p>
          </form>
        ) : null}
        <p className={styles.support}>Already have an invitation? Open the access link supplied by MEEM Technologies.</p>
        <p className={styles.support}>
          <a href="/privacy">Privacy notice</a>
        </p>
        <p className={styles.disclaimer}>Analytical research software. No investment recommendation, trade signal or price prediction.</p>
      </section>
    </main>
  )
}
