import type { Metadata } from "next"
import StandardsLibraryClient from "./StandardsLibraryClient"

export const metadata: Metadata = {
  title: "Standards & Compliance Library · HalalOne",
  description:
    "International, regional and national halal standards with key requirements — OIC/SMIIC, MS, GSO, SNI, SFDA, SANS, PS and TSE — cross-referenced, searchable and filterable by region.",
}

export default function Page() {
  return <StandardsLibraryClient />
}
