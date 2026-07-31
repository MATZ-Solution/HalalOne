import type { Metadata } from "next"
import TradeIntelligenceClient from "./TradeIntelligenceClient"

export const metadata: Metadata = {
  title: "Trade & Opportunity Intelligence · HalalOne",
  description:
    "Halal trade corridors scored for opportunity — exporter-to-importer flows with annual value, year-on-year growth and the certification that unlocks market access.",
}

export default function Page() {
  return <TradeIntelligenceClient />
}
