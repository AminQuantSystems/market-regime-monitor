import { useLayoutEffect, useRef } from "react"

import styles from "./DataSourceControls.module.css"

interface DataSourceControlsProps {
  open: boolean
  busy: boolean
  fileName: string | null
  fileNotice: string | null
  evaluationDate: string
  asOfDate: string
  canAnalyse: boolean
  errorDescribedBy: string | null
  onOpen: () => void
  onReturn: () => void
  onFile: (file: File | null) => void
  onEvaluationDate: (value: string) => void
  onAsOfDate: (value: string) => void
  onAnalyse: () => void
}

export function DataSourceControls({
  open,
  busy,
  fileName,
  fileNotice,
  evaluationDate,
  asOfDate,
  canAnalyse,
  errorDescribedBy,
  onOpen,
  onReturn,
  onFile,
  onEvaluationDate,
  onAsOfDate,
  onAnalyse,
}: DataSourceControlsProps) {
  const fileRef = useRef<HTMLInputElement>(null)
  const useCsvRef = useRef<HTMLButtonElement>(null)
  const wasOpen = useRef(false)

  // Opening CSV mode focuses the file input that replaces USE CSV.
  // Closing it focuses USE CSV again. The first render does not move focus.
  useLayoutEffect(() => {
    if (open && !wasOpen.current) {
      fileRef.current?.focus()
    } else if (!open && wasOpen.current) {
      useCsvRef.current?.focus()
    }
    wasOpen.current = open
  }, [open])

  if (!open) {
    return (
      <div className={styles.strip}>
        <button ref={useCsvRef} className={styles.action} type="button" onClick={onOpen}>
          USE CSV
        </button>
      </div>
    )
  }

  const describedBy = ["analyse-requirements", errorDescribedBy].filter(Boolean).join(" ")
  return (
    <form
      className={styles.strip}
      aria-describedby={errorDescribedBy ?? undefined}
      onSubmit={(event) => {
        event.preventDefault()
        if (canAnalyse) {
          onAnalyse()
        }
      }}
    >
      <p className={styles.mode}>CSV UPLOAD</p>
      <div className={styles.field}>
        <label htmlFor="csv-file">CSV FILE</label>
        <input
          ref={fileRef}
          id="csv-file"
          name="prices"
          type="file"
          accept=".csv,text/csv"
          disabled={busy}
          aria-describedby={fileNotice ? "csv-file-notice" : undefined}
          aria-invalid={fileNotice ? true : undefined}
          onChange={(event) => {
            onFile(event.target.files?.[0] ?? null)
          }}
        />
        {fileName ? (
          <p className={styles.fileName} title={fileName}>
            {fileName}
          </p>
        ) : null}
        {fileNotice ? (
          <p id="csv-file-notice" className={styles.notice}>
            {fileNotice}
          </p>
        ) : null}
      </div>
      <div className={styles.field}>
        <label htmlFor="evaluation-date">EVALUATION DATE</label>
        <input
          id="evaluation-date"
          name="evaluation_date"
          type="date"
          value={evaluationDate}
          disabled={busy}
          aria-describedby="evaluation-date-hint"
          onChange={(event) => {
            onEvaluationDate(event.target.value)
          }}
        />
        <p id="evaluation-date-hint" className={styles.hint}>
          The date against which data freshness is assessed.
        </p>
      </div>
      <div className={styles.field}>
        <label htmlFor="as-of-date">AS-OF DATE</label>
        <input
          id="as-of-date"
          name="as_of_date"
          type="date"
          value={asOfDate}
          disabled={busy}
          aria-describedby="as-of-date-hint"
          onChange={(event) => {
            onAsOfDate(event.target.value)
          }}
        />
        <p id="as-of-date-hint" className={styles.hint}>
          The exact observation date to analyse.
        </p>
      </div>
      <div className={styles.actions}>
        <button className={`${styles.action} ${styles.primary}`} type="submit" disabled={!canAnalyse} aria-describedby={describedBy}>
          ANALYSE CSV
        </button>
        <button className={styles.action} type="button" onClick={onReturn}>
          RETURN TO DEMO
        </button>
        <p className={styles.warning}>Public demonstration — do not upload confidential, personal or client data.</p>
        <p id="analyse-requirements" className={styles.hint}>
          Requires a CSV file, an evaluation date, and an as-of date.
        </p>
      </div>
    </form>
  )
}
