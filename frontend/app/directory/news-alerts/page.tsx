import type { Metadata } from "next"
import NewsAlertsClient from "./NewsAlertsClient"

export const metadata: Metadata = {
  title: "Industry News & Alerts · HalalOne",
  description:
    "Verified halal industry news and regulatory alerts — certification changes, standard updates, market moves and recall advisories, curated from ministry announcements, cert-body bulletins and OIC/SMIIC releases.",
}

export default function Page() {
  return <NewsAlertsClient />
}
