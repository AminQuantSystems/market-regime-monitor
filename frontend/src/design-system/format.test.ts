import { describe, expect, it } from "vitest"
import { formatCount, formatPercent, formatPercentile, formatPrice } from "./format"

describe("presentation formatting", () => {
  it("formats percentages, percentiles, prices, and counts", () => {
    expect(formatPercent(0.03124)).toBe("3.12%")
    expect(formatPercent(0.1845)).toBe("18.45%")
    expect(formatPercent(-0.03124)).toBe("-3.12%")
    expect(formatPercentile(82.738)).toBe("82.7")
    expect(formatPrice(101.5)).toBe("101.50")
    expect(formatCount(252)).toBe("252")
    expect(formatCount(-2)).toBe("-2")
  })

  it("does not display negative zero at the chosen precision", () => {
    expect(formatPercent(-1e-12)).toBe("0.00%")
    expect(formatPercent(-0.00004)).toBe("0.00%")
    expect(formatPercentile(-1e-12)).toBe("0.0")
    expect(formatPrice(-0.001)).toBe("0.00")
  })
})
