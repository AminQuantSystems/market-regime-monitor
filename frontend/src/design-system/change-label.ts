import type { ChangeDimension, ChangeReading } from "../types/board"

const ORDER: ChangeDimension[] = ["direction", "momentum", "volatility", "relative_performance"]
const LETTER: Record<ChangeDimension, string> = {
  direction: "D",
  momentum: "M",
  volatility: "V",
  relative_performance: "R",
}

export function changeLabel(change: ChangeReading): string {
  if (change.status === "UNAVAILABLE") {
    return "N/A"
  }
  if (change.status === "UNCHANGED") {
    return "—"
  }
  const changed = new Set(change.transitions.map((transition) => transition.dimension))
  return ORDER.filter((dimension) => changed.has(dimension))
    .map((dimension) => LETTER[dimension])
    .join(" ")
}
