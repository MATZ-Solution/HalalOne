import type { Metadata } from "next"
import MarketIntelligenceClient from "./MarketIntelligenceClient"

export const metadata: Metadata = {
  title: "Halal Market Intelligence · HalalOne",
  description:
    "The global halal economy measured — market size, country profiles, sector analysis, trade corridors and the trends shaping a USD 2.1 trillion market.",
}

export default function Page() {
  return <MarketIntelligenceClient />
}
