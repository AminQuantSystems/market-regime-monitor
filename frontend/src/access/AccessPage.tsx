import { useEffect, useState } from "react"
import styles from "./AccessPage.module.css"

const REQUEST_SUBJECT = "Market Regime Monitor — Demo Access Request"
const REQUEST_BODY = `Hello MEEM Technologies,

I would like to request access to the Market Regime Monitor demonstration.

Name:
Organisation:
Role:
Work email:
What I would like to evaluate (optional):

Regards,
`

type View = "loading" | "request" | "invalid" | "expired"

export const browser = {
  clearToken() {
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`)
  },
  openHome() {
    window.location.assign("/")
  },
}

function mailto(email: string): string {
  return `mailto:${email}?subject=${encodeURIComponent(REQUEST_SUBJECT)}&body=${encodeURIComponent(REQUEST_BODY)}`
}

async function exchangeInvitation(token: string): Promise<View> {
  browser.clearToken()
  try {
    const response = await fetch("/api/v1/auth/exchange", {
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
    return payload?.error?.code === "DEMO_INVITE_EXPIRED" ? "expired" : "invalid"
  } catch {
    return "invalid"
  }
}

export function AccessPage() {
  const [view, setView] = useState<View>("loading")
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
    const prefix = "#token="
    const hash = window.location.hash
    if (!hash.startsWith(prefix) || hash.length === prefix.length) {
      setView("request")
      return
    }
    let token = hash.slice(prefix.length)
    try {
      token = decodeURIComponent(token)
    } catch {
      setView("invalid")
      browser.clearToken()
      return
    }
    let cancelled = false
    void exchangeInvitation(token).then((next) => {
      if (!cancelled) {
        setView(next)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (view === "loading") {
      return
    }
    let cancelled = false
    void fetch("/api/v1/public/demo-access", { credentials: "same-origin" })
      .then((response) => response.json())
      .then((payload: { contact_email?: unknown }) => {
        if (!cancelled) {
          setEmail(typeof payload.contact_email === "string" && payload.contact_email !== "" ? payload.contact_email : null)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEmail(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [view])

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
        {view === "invalid" ? <p className={styles.notice}>This invitation is not valid.</p> : null}
        {email ? (
          <a className={styles.request} href={mailto(email)}>
            Request Demo Access
          </a>
        ) : view === "loading" ? null : (
          <p className={styles.copy}>Contact MEEM Technologies to request demonstration access.</p>
        )}
        <p className={styles.support}>Already have an invitation? Open the access link supplied by MEEM Technologies.</p>
        <p className={styles.disclaimer}>Analytical research software. No investment recommendation, trade signal or price prediction.</p>
      </section>
    </main>
  )
}
