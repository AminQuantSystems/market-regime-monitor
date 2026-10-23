import styles from "./ApplicationHeader.module.css"

interface ApplicationHeaderProps {
  sourceLabel: string | null
  sourceNote: string | null
  filename: string | null
  asOfDate: string | null
  benchmarkId: string | null
  universeSize: number | null
  validationStatus: "VALID" | null
  onEndSession: () => void
}

export function ApplicationHeader({
  sourceLabel,
  sourceNote,
  filename,
  asOfDate,
  benchmarkId,
  universeSize,
  validationStatus,
  onEndSession,
}: ApplicationHeaderProps) {
  const showFacts = asOfDate !== null && benchmarkId !== null && universeSize !== null
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <img
          className={styles.mark}
          src="/brand/MEEM_Standalone_Mark_White.png"
          alt="MEEM Technologies"
          width={263}
          height={469}
        />
        <div className={styles.identity}>
          <p className={styles.product}>MARKET REGIME MONITOR</p>
          {sourceLabel ? <p className={styles.source}>{sourceLabel}</p> : null}
          {filename ? (
            <p className={styles.fileName} title={filename}>
              {filename}
            </p>
          ) : null}
          {sourceNote ? <p className={styles.note}>{sourceNote}</p> : null}
        </div>
      </div>
      {showFacts ? (
        <dl className={styles.context}>
          <div className={styles.fact}>
            <dt>AS OF</dt>
            <dd>{asOfDate}</dd>
          </div>
          <div className={styles.fact}>
            <dt>BENCHMARK</dt>
            <dd>{benchmarkId}</dd>
          </div>
          <div className={styles.fact}>
            <dt>UNIVERSE</dt>
            <dd>{universeSize} MARKETS</dd>
          </div>
          {validationStatus === "VALID" ? (
            <div className={styles.fact}>
              <dt>DATA</dt>
              <dd>VALID</dd>
            </div>
          ) : null}
        </dl>
      ) : null}
      <div className={styles.session}>
        <button className={styles.endSession} type="button" onClick={onEndSession}>
          End Demo Session
        </button>
        <p className={styles.sessionReminder}>
          For your security, please end your demo session when you have finished, particularly when using a shared device.
        </p>
      </div>
    </header>
  )
}
