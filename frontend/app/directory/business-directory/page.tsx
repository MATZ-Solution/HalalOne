import type { Metadata } from "next"
import BusinessDirectoryClient from "./BusinessDirectoryClient"

export const metadata: Metadata = {
  title: "Business Directory · HalalOne",
  description:
    "The verified global halal business directory — manufacturers, exporters, food service, ingredient suppliers, pharma, cosmetics, retail, finance, logistics and certification bodies, with certifier, export markets and verification status.",
}

export default function Page() {
  return <BusinessDirectoryClient />
}
