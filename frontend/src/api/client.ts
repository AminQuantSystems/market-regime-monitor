import type { ApiErrorBody, BoardResponse } from "../types/board"

export class AnalysisError extends Error {
  readonly code: string
  readonly category: string

  constructor(code: string, message: string, category: string) {
    super(message)
    this.name = "AnalysisError"
    this.code = code
    this.category = category
  }
}

export async function analyseBoard(input: {
  dataSource: "demo" | "upload"
  evaluationDate: string
  asOfDate: string
  prices?: File
}): Promise<BoardResponse> {
  const body = new FormData()
  body.set("data_source", input.dataSource)
  body.set("evaluation_date", input.evaluationDate)
  body.set("as_of_date", input.asOfDate)
  if (input.prices) {
    body.set("prices", input.prices)
  }
  const response = await fetch("/api/v1/market-regime/analyse", { method: "POST", body })
  const payload: BoardResponse | ApiErrorBody = await response.json()
  if (!response.ok) {
    const error = (payload as ApiErrorBody).error
    throw new AnalysisError(error.code, error.message, error.category)
  }
  return payload as BoardResponse
}
