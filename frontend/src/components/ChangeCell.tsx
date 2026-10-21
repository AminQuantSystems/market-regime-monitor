import { changeLabel } from "../design-system/change-label"
import { presentChange } from "../design-system/semantics"
import type { ChangeReading } from "../types/board"
import styles from "./MarketStateBoard.module.css"

export function ChangeCell({ change }: { change: ChangeReading }) {
  const presentation = presentChange(change.status)
  return <span className={`${styles.label} ${styles[presentation.semantic]}`}>{changeLabel(change)}</span>
}
