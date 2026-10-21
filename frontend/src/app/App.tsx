import { useEffect, useRef, useState } from "react"
import { analyseBoard, AnalysisError } from "../api/client"
import { ApplicationHeader } from "../components/ApplicationHeader"
import { DataSourceControls } from "../components/DataSourceControls"
import { MarketDetailPanel } from "../components/MarketDetailPanel"
import { MarketStateBoard } from "../components/MarketStateBoard"
import { ValidationErrorState } from "../components/ValidationErrorState"
import { DEMO_AS_OF_DATE, DEMO_EVALUATION_DATE, DEMO_LABEL } from "../demo"
import type { BoardResponse } from "../types/board"
import { clientFileNotice } from "../upload-checks"
import styles from "./App.module.css"

const SYNTHETIC_NOTE = "Synthetic demonstration. Not a live feed."
const UPLOAD_CONTEXT = "CSV UPLOAD"
const UPLOAD_RESULT = "UPLOADED CSV"

type Source = "demo" | "upload"

type AnalysisState =
  | { phase: "loading"; source: Source; filename: string | null }
  | { phase: "ready"; board: BoardResponse; filename: string | null }
  | { phase: "error"; source: Source; code: string; message: string; filename: string | null }

function failure(error: unknown, source: Source, filename: string | null): AnalysisState {
  if (error instanceof AnalysisError) {
    return { phase: "error", source, code: error.code, message: error.message, filename }
  }
  return {
    phase: "error",
    source,
    code: "API_UNEXPECTED",
    message: "The analysis could not be completed.",
    filename,
  }
}

export function App() {
  const [state, setState] = useState<AnalysisState>({ phase: "loading", source: "demo", filename: null })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [csvOpen, setCsvOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [evaluationDate, setEvaluationDate] = useState("")
  const [asOfDate, setAsOfDate] = useState("")
  const generation = useRef(0)

  function track(id: number, source: Source, filename: string | null, request: Promise<BoardResponse>) {
    request
      .then((board) => {
        if (id !== generation.current) {
          return
        }
        // Every completed analysis selects the first returned market.
        setSelectedId(null)
        setState({ phase: "ready", board, filename })
      })
      .catch((error: unknown) => {
        if (id !== generation.current) {
          return
        }
        setState(failure(error, source, filename))
      })
  }

  useEffect(() => {
    const id = ++generation.current
    setState({ phase: "loading", source: "demo", filename: null })
    track(
      id,
      "demo",
      null,
      analyseBoard({
        dataSource: "demo",
        evaluationDate: DEMO_EVALUATION_DATE,
        asOfDate: DEMO_AS_OF_DATE,
      }),
    )
    return () => {
      generation.current += 1
    }
  }, [])

  function analyseUpload() {
    if (!file || clientFileNotice(file) || evaluationDate === "" || asOfDate === "") {
      return
    }
    const id = ++generation.current
    const filename = file.name
    setSelectedId(null)
    setState({ phase: "loading", source: "upload", filename })
    track(
      id,
      "upload",
      filename,
      analyseBoard({
        dataSource: "upload",
        evaluationDate,
        asOfDate,
        prices: file,
      }),
    )
  }

  function returnToDemo() {
    const id = ++generation.current
    setCsvOpen(false)
    setFile(null)
    setEvaluationDate("")
    setAsOfDate("")
    setSelectedId(null)
    setState({ phase: "loading", source: "demo", filename: null })
    track(
      id,
      "demo",
      null,
      analyseBoard({
        dataSource: "demo",
        evaluationDate: DEMO_EVALUATION_DATE,
        asOfDate: DEMO_AS_OF_DATE,
      }),
    )
  }

  const board = state.phase === "ready" ? state.board : null
  const selected = board?.markets.find((market) => market.market_id === selectedId) ?? board?.markets[0] ?? null
  const fileNotice = file ? clientFileNotice(file) : null
  const canAnalyse = file !== null && fileNotice === null && evaluationDate !== "" && asOfDate !== "" && state.phase !== "loading"
  const header = headerView(state)

  return (
    <main className={styles.shell}>
      <ApplicationHeader
        sourceLabel={header.sourceLabel}
        sourceNote={header.sourceNote}
        filename={header.filename}
        asOfDate={header.asOfDate}
        benchmarkId={header.benchmarkId}
        universeSize={header.universeSize}
        validationStatus={header.validationStatus}
      />
      <DataSourceControls
        open={csvOpen}
        busy={state.phase === "loading"}
        fileName={file?.name ?? null}
        fileNotice={fileNotice}
        evaluationDate={evaluationDate}
        asOfDate={asOfDate}
        canAnalyse={canAnalyse}
        errorDescribedBy={state.phase === "error" ? "analysis-error" : null}
        onOpen={() => {
          setCsvOpen(true)
        }}
        onReturn={returnToDemo}
        onFile={setFile}
        onEvaluationDate={setEvaluationDate}
        onAsOfDate={setAsOfDate}
        onAnalyse={analyseUpload}
      />
      {state.phase === "loading" ? <p className={styles.status} role="status">ANALYSING MARKET STATE…</p> : null}
      {state.phase === "error" ? <ValidationErrorState code={state.code} message={state.message} /> : null}
      {board && selected ? (
        <div className={styles.workspace}>
          <MarketStateBoard markets={board.markets} selectedId={selected.market_id} onSelect={setSelectedId} />
          <MarketDetailPanel market={selected} />
        </div>
      ) : null}
    </main>
  )
}

function headerView(state: AnalysisState) {
  if (state.phase === "ready" && state.board.data_source === "upload") {
    return {
      sourceLabel: UPLOAD_RESULT,
      sourceNote: null,
      filename: state.filename,
      asOfDate: state.board.as_of_date,
      benchmarkId: state.board.benchmark_id,
      universeSize: state.board.universe_size,
      validationStatus: state.board.validation_status,
    }
  }
  if (state.phase === "ready") {
    return {
      sourceLabel: state.board.data_label ?? DEMO_LABEL,
      sourceNote: SYNTHETIC_NOTE,
      filename: null,
      asOfDate: state.board.as_of_date,
      benchmarkId: state.board.benchmark_id,
      universeSize: state.board.universe_size,
      validationStatus: state.board.validation_status,
    }
  }
  if (state.source === "upload") {
    return {
      sourceLabel: UPLOAD_CONTEXT,
      sourceNote: null,
      filename: state.filename,
      asOfDate: null,
      benchmarkId: null,
      universeSize: null,
      validationStatus: null,
    }
  }
  return {
    sourceLabel: DEMO_LABEL,
    sourceNote: SYNTHETIC_NOTE,
    filename: null,
    asOfDate: state.phase === "loading" ? DEMO_AS_OF_DATE : null,
    benchmarkId: state.phase === "loading" ? "ACWI" : null,
    universeSize: state.phase === "loading" ? 7 : null,
    validationStatus: null,
  }
}
