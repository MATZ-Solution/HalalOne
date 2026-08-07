import type { Metadata } from "next"
import IngredientDatabaseClient from "./IngredientDatabaseClient"

export const metadata: Metadata = {
  title: "Ingredient & E-Number Database · HalalOne",
  description:
    "Halal classification of food additives, E-numbers and common ingredients — with source origin, reasoning, and side-by-side rulings from JAKIM, IFANCA, SANHA, ESMA and MUI.",
}

export default function Page() {
  return <IngredientDatabaseClient />
}
