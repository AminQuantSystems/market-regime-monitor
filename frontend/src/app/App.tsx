import { useEffect, useState } from "react"
import { analyseBoard, AnalysisError } from "../api/client"
import { ApplicationHeader } from "../components/ApplicationHeader"
import { MarketStateBoard } from "../components/MarketStateBoard"
import { ValidationErrorState } from "../components/ValidationErrorState"
import { DEMO_AS_OF_DATE, DEMO_EVALUATION_DATE, DEMO_LABEL } from "../demo"
import type { BoardResponse } from "../types/board"
import styles from "./App.module.css"

type LoadState =
  | { phase: "loading" }
  | { phase: "ready"; board: BoardResponse }
  | { phase: "error"; code: string; message: string }

export function App() {
  const [state, setState] = useState<LoadState>({ phase: "loading" })

  useEffect(() => {
    let active = true
    analyseBoard({
      dataSource: "demo",
      evaluationDate: DEMO_EVALUATION_DATE,
      asOfDate: DEMO_AS_OF_DATE,
    })
      .then((board) => {
        if (active) {
          setState({ phase: "ready", board })
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return
        }
        if (error instanceof AnalysisError) {
          setState({ phase: "error", code: error.code, message: error.message })
          return
        }
        setState({ phase: "error", code: "API_UNEXPECTED", message: "The analysis could not be completed." })
      })
    return () => {
      active = false
    }
  }, [])

  const board = state.phase === "ready" ? state.board : null
  return (
    <main className={styles.shell}>
      <ApplicationHeader
        asOfDate={board?.as_of_date ?? DEMO_AS_OF_DATE}
        universeSize={board?.universe_size ?? 7}
        dataLabel={board?.data_label ?? DEMO_LABEL}
        validationStatus={board?.validation_status ?? null}
      />
      {state.phase === "loading" ? <p className={styles.status} role="status">ANALYSING MARKET STATE…</p> : null}
      {state.phase === "error" ? <ValidationErrorState code={state.code} message={state.message} /> : null}
      {board ? <MarketStateBoard markets={board.markets} /> : null}
    </main>
  )
}
