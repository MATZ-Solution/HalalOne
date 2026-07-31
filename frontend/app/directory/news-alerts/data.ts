// Representative newsroom dataset (seed content). The original design loaded
// this from an external `newsalerts-data.js`; recreated here as typed data.
// Illustrative reference items — verify against official sources before relying.

export type Priority = "HIGH" | "MEDIUM" | "LOW"

export type ArticleType =
  | "Regulatory Alert"
  | "Product Recall"
  | "Certification Update"
  | "Standard Change"
  | "Market Update"
  | "Trade News"
  | "Industry News"

export type Block = { label?: string; text?: string; bullets?: string[] }

export type Article = {
  id: string
  type: ArticleType
  priority: Priority
  date: string
  expires?: string
  title: string
  summary: string
  countries: string[]
  certBodies: string[]
  blocks: Block[]
  sourceUrl: string
  sourceLabel: string
  tags: string[]
}

export const ARTICLES: Article[] = [
  {
    id: "HO-NA-0001",
    type: "Regulatory Alert",
    priority: "HIGH",
    date: "15 Jan 2025",
    expires: "15 Apr 2025",
    title: "Indonesia begins phased mandatory halal certification for imported food & beverage",
    summary:
      "BPJPH confirms the next enforcement phase requires imported processed food and beverage products to carry recognised halal certification, tightening acceptance of foreign certificate bodies.",
    countries: ["Indonesia"],
    certBodies: ["BPJPH", "LPPOM MUI"],
    blocks: [
      {
        label: "What changed",
        text: "The mandatory halal certification obligation now extends to a broader set of imported processed food and beverage categories, with a defined grace window before border enforcement tightens.",
      },
      {
        label: "Action for exporters",
        bullets: [
          "Confirm your certifier is recognised by BPJPH under a current mutual-recognition arrangement.",
          "Re-check product-category scope on existing certificates before shipping.",
          "Budget lead time for re-certification where the certifier is not yet recognised.",
        ],
      },
    ],
    sourceUrl: "https://bpjph.halal.go.id",
    sourceLabel: "BPJPH announcement",
    tags: ["imports", "mandatory-certification", "food-beverage", "asean"],
  },
  {
    id: "HO-NA-0002",
    type: "Product Recall",
    priority: "HIGH",
    date: "9 Jan 2025",
    expires: "9 Feb 2025",
    title: "Recall advisory: undeclared porcine-derived gelatin in imported confectionery line",
    summary:
      "A confectionery batch distributed across several GCC markets was withdrawn after testing indicated undeclared porcine-derived gelatin, invalidating its halal claim.",
    countries: ["United Arab Emirates", "Saudi Arabia", "Qatar"],
    certBodies: ["ESMA", "SFDA"],
    blocks: [
      {
        label: "Summary",
        text: "Authorities issued a withdrawal notice for a specific batch range after laboratory analysis flagged an undeclared animal-derived ingredient inconsistent with the product's halal certification.",
      },
      {
        label: "Recommended checks",
        bullets: [
          "Quarantine affected batch codes pending confirmation from the distributor.",
          "Verify gelatin source documentation across your confectionery SKUs.",
        ],
      },
    ],
    sourceUrl: "https://www.sfda.gov.sa",
    sourceLabel: "SFDA recall notice",
    tags: ["recall", "gelatin", "gcc", "confectionery"],
  },
  {
    id: "HO-NA-0003",
    type: "Standard Change",
    priority: "MEDIUM",
    date: "3 Jan 2025",
    title: "SMIIC revises general halal food standard; alignment window opens for OIC members",
    summary:
      "OIC/SMIIC published a revision to its general requirements for halal food, prompting national bodies to review alignment of their schemes and certificate templates.",
    countries: ["OIC members"],
    certBodies: ["SMIIC"],
    blocks: [
      {
        text: "The revision refines terminology and traceability expectations. National accreditation bodies typically map their schemes to SMIIC references, so downstream certificate criteria may be updated over the coming cycle.",
      },
      {
        label: "Who should track this",
        bullets: [
          "Certification bodies maintaining SMIIC-referenced schemes.",
          "Exporters relying on cross-recognition into SMIIC-aligned markets.",
        ],
      },
    ],
    sourceUrl: "https://www.smiic.org",
    sourceLabel: "SMIIC standards portal",
    tags: ["smiic", "standards", "oic", "traceability"],
  },
  {
    id: "HO-NA-0004",
    type: "Certification Update",
    priority: "MEDIUM",
    date: "28 Dec 2024",
    title: "JAKIM updates list of recognised foreign halal certification bodies",
    summary:
      "JAKIM published its periodic revision of recognised foreign certification bodies, adding, renewing and removing several entries that affect market access into Malaysia.",
    countries: ["Malaysia"],
    certBodies: ["JAKIM"],
    blocks: [
      {
        label: "Impact",
        text: "Products certified by a body that has been removed or lapsed may face rejection at import; newly recognised bodies open fresh routes to the Malaysian market.",
      },
      {
        label: "Do this now",
        bullets: [
          "Cross-check your certifier against the latest JAKIM recognised list.",
          "Flag any certificates issued by bodies pending renewal.",
        ],
      },
    ],
    sourceUrl: "https://www.halal.gov.my",
    sourceLabel: "JAKIM recognised bodies list",
    tags: ["jakim", "recognition", "market-access", "malaysia"],
  },
  {
    id: "HO-NA-0005",
    type: "Market Update",
    priority: "LOW",
    date: "20 Dec 2024",
    title: "Global halal food trade projected to keep double-digit growth into 2026",
    summary:
      "Trade analysts point to sustained demand across Southeast Asia, the GCC and emerging African markets, with ingredients and pharmaceuticals among the faster-growing segments.",
    countries: ["Global"],
    certBodies: [],
    blocks: [
      {
        text: "Growth is attributed to population trends, rising middle-class demand, and broader adoption of halal assurance beyond food into pharma, cosmetics and logistics. Figures are indicative and vary by source methodology.",
      },
    ],
    sourceUrl: "https://www.salaamgateway.com",
    sourceLabel: "Industry market brief",
    tags: ["market", "growth", "trade", "outlook"],
  },
  {
    id: "HO-NA-0006",
    type: "Trade News",
    priority: "LOW",
    date: "12 Dec 2024",
    title: "New mutual-recognition talks between Gulf and Southeast Asian halal authorities",
    summary:
      "Authorities signalled intent to streamline cross-border certificate acceptance, which could reduce duplicate audits for exporters operating across both regions.",
    countries: ["GCC", "Malaysia", "Indonesia"],
    certBodies: ["ESMA", "JAKIM", "BPJPH"],
    blocks: [
      {
        label: "Why it matters",
        text: "Mutual recognition reduces cost and lead time by cutting duplicate certification. Any agreement typically phases in with defined scope and transition rules.",
      },
    ],
    sourceUrl: "https://www.salaamgateway.com",
    sourceLabel: "Trade press coverage",
    tags: ["mutual-recognition", "gcc", "asean", "exporters"],
  },
]
