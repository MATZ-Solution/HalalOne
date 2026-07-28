import type { Metadata } from "next"
import RegIntelClient from "./RegIntelClient"

export const metadata: Metadata = {
  title: "Regulatory Intelligence · Country Data · HalalOne",
  description:
    "Import rules and halal compliance, country by country — national standards, accepted certification bodies, labelling requirements and import documentation across OIC and key non-OIC export markets.",
}

export default function Page() {
  return <RegIntelClient />
}
