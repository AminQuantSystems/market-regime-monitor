import { ChangeCell } from "./ChangeCell"
import { StateCell } from "./StateCell"
import { presentMomentum, presentRelative, presentTrend, presentVolatility } from "../design-system/semantics"
import type { MarketReading } from "../types/board"
import styles from "./MarketStateBoard.module.css"

const WIDTHS = ["24%", "15%", "18%", "11%", "22%", "10%"]

interface MarketStateBoardProps {
  markets: MarketReading[]
  selectedId: string
  onSelect: (marketId: string) => void
}

export function MarketStateBoard({ markets, selectedId, onSelect }: MarketStateBoardProps) {
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption className={styles.caption}>Market state for the seven configured markets</caption>
        <colgroup>
          {WIDTHS.map((width) => (
            <col key={width} style={{ width }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            {["MARKET", "DIRECTION", "MOMENTUM", "VOL", "RELATIVE", "CHANGE"].map((heading) => (
              <th key={heading} scope="col">
                {heading}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {markets.map((market) => (
            <tr key={market.market_id} data-selected={market.market_id === selectedId ? "true" : "false"}>
              <th scope="row">
                <button
                  type="button"
                  className={styles.select}
                  aria-pressed={market.market_id === selectedId}
                  aria-controls="market-detail"
                  onClick={() => onSelect(market.market_id)}
                >
                  <span className={styles.market}>{market.display_name}</span> <span className={styles.ticker}>{market.market_id}</span>
                </button>
              </th>
              <td>
                <StateCell label={market.current.trend.trend_state} presentation={presentTrend(market.current.trend.trend_state)} />
              </td>
              <td>
                <StateCell
                  label={market.current.momentum.momentum_state}
                  presentation={presentMomentum(market.current.momentum.momentum_state)}
                />
              </td>
              <td>
                <StateCell
                  label={market.current.volatility.volatility_regime}
                  presentation={presentVolatility(market.current.volatility.volatility_regime)}
                />
              </td>
              <td>
                <StateCell
                  label={market.current.relative_performance.relative_performance_state}
                  presentation={presentRelative(market.current.relative_performance.relative_performance_state)}
                />
              </td>
              <td>
                <ChangeCell change={market.change} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
