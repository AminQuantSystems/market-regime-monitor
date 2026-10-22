import { useEffect, useState } from "react"
import styles from "./AccessPage.module.css"

export function PrivacyPage() {
  const [email, setEmail] = useState<string | null>(null)

  useEffect(() => {
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
  }, [])

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <p className={styles.product}>MARKET REGIME MONITOR</p>
        <h1 className={styles.title}>Demonstration privacy notice</h1>
        <p className={styles.copy}>
          This notice describes the Market Regime Monitor demonstration operated by MEEM Technologies. It is not a regulated client portal.
        </p>
        <p className={styles.copy}>The demonstration request collects your name, email address, organisation, role, and any evaluation interest you choose to provide.</p>
        <p className={styles.copy}>
          Technical information required to operate and protect the service, including a session cookie and request limits, is also processed.
        </p>
        <p className={styles.copy}>
          MEEM relies on legitimate interests to process the limited information needed to administer the demonstration you requested, verify demonstration access, protect the demonstration against misuse, and respond to and follow up regarding that specific request.
        </p>
        <p className={styles.copy}>
          You have the right to object to processing based on legitimate interests. Requesting demonstration access does not subscribe you to marketing.
        </p>
        <p className={styles.copy}>HubSpot is used for customer-relationship and lead administration. Microsoft Azure is used for hosting and for the transactional verification email.</p>
        <p className={styles.copy}>
          {email ? (
            <>
              Questions about this notice: <a href={`mailto:${email}`}>{email}</a>
            </>
          ) : (
            "Contact MEEM Technologies with questions about this notice."
          )}
        </p>
        <p className={styles.support}>
          <a href="/access">Return to demonstration access</a>
        </p>
      </section>
    </main>
  )
}
