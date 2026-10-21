import styles from "./ApplicationHeader.module.css"

interface ApplicationHeaderProps {
  asOfDate: string
  universeSize: number
  dataLabel: string | null
  validationStatus: "VALID" | null
}

export function ApplicationHeader({ asOfDate, universeSize, dataLabel, validationStatus }: ApplicationHeaderProps) {
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
        <div>
          <p className={styles.product}>MARKET REGIME MONITOR</p>
          {dataLabel ? <p className={styles.demo}>{dataLabel}</p> : null}
          {dataLabel ? <p className={styles.note}>Synthetic demonstration. Not a live feed.</p> : null}
        </div>
      </div>
      <dl className={styles.context}>
        <div className={styles.fact}>
          <dt>AS OF</dt>
          <dd>{asOfDate}</dd>
        </div>
        <div className={styles.fact}>
          <dt>BENCHMARK</dt>
          <dd>ACWI</dd>
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
    </header>
  )
}
