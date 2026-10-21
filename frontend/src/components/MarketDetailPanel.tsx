import { StateCell } from "./StateCell"
import { formatCount, formatPercent, formatPercentile, formatPrice } from "../design-system/format"
import {
  presentChange,
  presentMomentum,
  presentRelative,
  presentTrend,
  presentVolatility,
  type Presentation,
} from "../design-system/semantics"
import type { ChangeDimension, ChangeReading, MarketReading } from "../types/board"
import styles from "./MarketDetailPanel.module.css"

const DIMENSIONS: ChangeDimension[] = ["direction", "momentum", "volatility", "relative_performance"]
const DIMENSION_LABEL: Record<ChangeDimension, string> = {
  direction: "DIRECTION",
  momentum: "MOMENTUM",
  volatility: "VOLATILITY",
  relative_performance: "RELATIVE PERFORMANCE",
}

function statePresentation(dimension: ChangeDimension, state: string): Presentation {
  if (dimension === "direction") {
    return presentTrend(state as MarketReading["current"]["trend"]["trend_state"])
  }
  if (dimension === "momentum") {
    return presentMomentum(state as MarketReading["current"]["momentum"]["momentum_state"])
  }
  if (dimension === "volatility") {
    return presentVolatility(state as MarketReading["current"]["volatility"]["volatility_regime"])
  }
  return presentRelative(state as MarketReading["current"]["relative_performance"]["relative_performance_state"])
}

function Metrics({ rows }: { rows: Array<[string, string]> }) {
  return (
    <dl className={styles.metrics}>
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function Reason({ code }: { code: string }) {
  return <p className={styles.reason}>{code}</p>
}

function ChangeDetail({ change }: { change: ChangeReading }) {
  const ordered = DIMENSIONS.flatMap((dimension) => change.transitions.filter((item) => item.dimension === dimension))
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionLabel}>WHAT CHANGED</h3>
      <div className={styles.state}>
        <StateCell label={change.status} presentation={presentChange(change.status)} />
      </div>
      {change.status === "UNCHANGED" ? <p className={styles.statement}>NO MARKET-STATE CHANGE SINCE PREVIOUS SESSION</p> : null}
      {change.status === "UNAVAILABLE" ? <p className={styles.statement}>PREVIOUS STATE UNAVAILABLE</p> : null}
      {change.status !== "UNAVAILABLE" && change.previous_as_of_date ? (
        <Metrics rows={[["PREVIOUS OBSERVATION", change.previous_as_of_date]]} />
      ) : null}
      {change.status === "CHANGED" ? (
        <ol className={styles.transitions}>
          {ordered.map((transition) => (
            <li key={transition.dimension}>
              <p className={styles.dimension}>{DIMENSION_LABEL[transition.dimension]}</p>
              <p className={styles.flow}>
                <StateCell
                  label={transition.previous_state}
                  presentation={statePresentation(transition.dimension, transition.previous_state)}
                />
                <span className={styles.arrow}>→</span>
                <StateCell
                  label={transition.current_state}
                  presentation={statePresentation(transition.dimension, transition.current_state)}
                />
              </p>
            </li>
          ))}
        </ol>
      ) : null}
      <Reason code={change.reason_code} />
    </section>
  )
}

export function MarketDetailPanel({ market }: { market: MarketReading }) {
  const trend = market.current.trend
  const momentum = market.current.momentum
  const volatility = market.current.volatility
  const relative = market.current.relative_performance
  return (
    <aside id="market-detail" className={styles.panel}>
      <p className={styles.kicker}>MARKET DETAIL</p>
      <h2 className={styles.name}>{market.display_name}</h2>
      <p className={styles.ticker}>{market.market_id}</p>
      <p className={styles.asOf}>AS OF {trend.as_of_date}</p>
      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>DIRECTION</h3>
        <div className={styles.state}>
          <StateCell label={trend.trend_state} presentation={presentTrend(trend.trend_state)} />
        </div>
        <Metrics
          rows={[
            ["ADJUSTED CLOSE", formatPrice(trend.adjusted_close)],
            ["SMA 50", formatPrice(trend.sma_50)],
            ["SMA 200", formatPrice(trend.sma_200)],
            ["TREND SCORE", formatCount(trend.trend_score)],
          ]}
        />
        <p className={styles.note}>Categorical trend score from -2 to 2. Not a composite regime score.</p>
        <Reason code={trend.reason_code} />
      </section>
      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>MOMENTUM</h3>
        <div className={styles.state}>
          <StateCell label={momentum.momentum_state} presentation={presentMomentum(momentum.momentum_state)} />
        </div>
        <Metrics
          rows={[
            ["ADJUSTED CLOSE", formatPrice(momentum.adjusted_close)],
            ["21-SESSION RETURN", formatPercent(momentum.return_21)],
            ["63-SESSION RETURN", formatPercent(momentum.return_63)],
            ["21-SESSION PACE", formatPercent(momentum.pace_21)],
            ["63-SESSION PACE", formatPercent(momentum.pace_63)],
          ]}
        />
        <Reason code={momentum.reason_code} />
      </section>
      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>VOLATILITY</h3>
        <div className={styles.state}>
          <StateCell label={volatility.volatility_regime} presentation={presentVolatility(volatility.volatility_regime)} />
        </div>
        <Metrics
          rows={[
            ["ADJUSTED CLOSE", formatPrice(volatility.adjusted_close)],
            ["RV21", formatPercent(volatility.realized_volatility_21)],
            ["HISTORICAL PERCENTILE", formatPercentile(volatility.historical_percentile)],
            ["HISTORICAL BELOW COUNT", formatCount(volatility.historical_below_count)],
            ["HISTORICAL EQUAL COUNT", formatCount(volatility.historical_equal_count)],
            ["HISTORICAL REFERENCE SIZE", formatCount(volatility.historical_reference_size)],
          ]}
        />
        <Reason code={volatility.reason_code} />
      </section>
      <section className={styles.section}>
        <h3 className={styles.sectionLabel}>RELATIVE PERFORMANCE</h3>
        <div className={styles.state}>
          <StateCell
            label={relative.relative_performance_state}
            presentation={presentRelative(relative.relative_performance_state)}
          />
        </div>
        <Metrics
          rows={[
            ["BENCHMARK", relative.benchmark_id],
            ["ASSET ADJUSTED CLOSE", formatPrice(relative.adjusted_close)],
            ["BENCHMARK ADJUSTED CLOSE", formatPrice(relative.benchmark_adjusted_close)],
            ["ASSET RETURN 63", formatPercent(relative.asset_return_63)],
            ["BENCHMARK RETURN 63", formatPercent(relative.benchmark_return_63)],
            ["ACTIVE RETURN", formatPercent(relative.active_return_63)],
          ]}
        />
        <Reason code={relative.reason_code} />
      </section>
      <ChangeDetail change={market.change} />
    </aside>
  )
}
