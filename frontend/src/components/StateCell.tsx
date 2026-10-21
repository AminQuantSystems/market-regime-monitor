import type { Presentation } from "../design-system/semantics"
import styles from "./MarketStateBoard.module.css"

interface StateCellProps {
  label: string
  presentation: Presentation
}

export function StateCell({ label, presentation }: StateCellProps) {
  return (
    <span className={`${styles.label} ${styles[presentation.semantic]}`} data-emphasis={presentation.emphasis}>
      {label}
    </span>
  )
}
