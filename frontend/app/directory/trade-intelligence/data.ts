// Representative Trade & Opportunity Intelligence dataset. The original design
// loaded this from an external `trade-data.js`; recreated here as typed data.
// Opportunity scores are illustrative analytical estimates, not guarantees —
// verify tariffs, certification recognition and market access before acting.

export type TradeFlow = {
  id: string
  exporter: string
  importer: string
  category: string
  notes: string
  certBody: string
  value: string // annual corridor value, e.g. "$2.4B"
  yoy: string // year-on-year growth, e.g. "+12%"
  score: number // opportunity score, 0–10
}

export const TRADEFLOWS: TradeFlow[] = [
  {
    id: "HO-TR-0001",
    exporter: "Brazil",
    importer: "Saudi Arabia",
    category: "Poultry & Meat",
    notes:
      "The world's largest halal poultry corridor. FAMBRAS-certified plants supply a market where domestic production covers only a fraction of demand — supply consistently trails consumption.",
    certBody: "FAMBRAS Halal",
    value: "$2.4B",
    yoy: "+9%",
    score: 9,
  },
  {
    id: "HO-TR-0002",
    exporter: "Australia",
    importer: "Indonesia",
    category: "Beef & Livestock",
    notes:
      "Live cattle and boxed beef into the largest Muslim-majority market. Mandatory certification and recognised-body requirements gate access but reward compliant exporters.",
    certBody: "AFIC / recognised by BPJPH",
    value: "$1.6B",
    yoy: "+6%",
    score: 8,
  },
  {
    id: "HO-TR-0003",
    exporter: "India",
    importer: "United Arab Emirates",
    category: "Basmati & Cereals",
    notes:
      "High-volume rice and cereal corridor into a re-export hub. Growth is steady and certification friction is low, though margins are competitive.",
    certBody: "Halal India / ESMA-recognised",
    value: "$1.1B",
    yoy: "+4%",
    score: 7,
  },
  {
    id: "HO-TR-0004",
    exporter: "Malaysia",
    importer: "China",
    category: "Processed Food",
    notes:
      "JAKIM's strong recognition gives Malaysian processed food a trust premium into a fast-growing Chinese halal segment — demand is outpacing certified local supply.",
    certBody: "JAKIM",
    value: "$780M",
    yoy: "+15%",
    score: 9,
  },
  {
    id: "HO-TR-0005",
    exporter: "Türkiye",
    importer: "Germany",
    category: "Confectionery & Bakery",
    notes:
      "Serves a large European Muslim consumer base. HAK/TSE certification eases acceptance; competition is mature so differentiation matters.",
    certBody: "HAK / TSE",
    value: "$540M",
    yoy: "+3%",
    score: 7,
  },
  {
    id: "HO-TR-0006",
    exporter: "Thailand",
    importer: "Malaysia",
    category: "Seafood & Ready Meals",
    notes:
      "CICOT-certified seafood and ready meals into an adjacent, high-standard market. Logistics are short and certification is mutually familiar.",
    certBody: "CICOT",
    value: "$430M",
    yoy: "+8%",
    score: 8,
  },
  {
    id: "HO-TR-0007",
    exporter: "Netherlands",
    importer: "GCC",
    category: "Dairy & Nutrition",
    notes:
      "Infant nutrition and dairy into the GCC, where premium positioning and halal assurance command strong pricing. Recognition of EU certifiers is the key unlock.",
    certBody: "HFC Europe / GSO-recognised",
    value: "$620M",
    yoy: "+7%",
    score: 8,
  },
  {
    id: "HO-TR-0008",
    exporter: "Pakistan",
    importer: "GCC",
    category: "Meat & Livestock",
    notes:
      "Chilled and frozen meat into the Gulf. Cost-competitive with rising volumes, though certifier recognition and cold-chain consistency remain the growth levers.",
    certBody: "SMIIC-aligned (PNAC)",
    value: "$390M",
    yoy: "+11%",
    score: 8,
  },
]
