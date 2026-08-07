// Representative Standards Library dataset. The original design loaded this from
// an external `standards-data.js`; recreated here as typed data. Summaries are
// for orientation only — consult the official published standard for full text.

export type Region = "International" | "SE Asia" | "Middle East" | "Africa" | "South Asia" | "Europe"

export type Standard = {
  id: string
  code: string
  region: Region
  status: string
  access?: string
  year?: string
  supersedes?: string
  title: string
  orgCountry: string
  tags: string[]
  description: string
  requirements: string[]
  adoptedBy: string[]
  related: string[]
  languages?: string
  note?: string
}

export const STANDARDS: Standard[] = [
  {
    id: "HO-STD-0001",
    code: "OIC/SMIIC 1:2019",
    region: "International",
    status: "In force",
    access: "Purchase",
    year: "2019",
    supersedes: "OIC/SMIIC 1:2011",
    title: "General Requirements for Halal Food",
    orgCountry: "SMIIC · OIC (57 member states)",
    tags: ["Food", "General", "Traceability"],
    description:
      "The reference international halal food standard developed under the OIC, defining requirements for sourcing, slaughter, processing, storage and traceability that national schemes commonly align to.",
    requirements: [
      "Animals must be lawful (halal) species and slaughtered per Islamic rules",
      "Complete segregation from non-halal materials across the supply chain",
      "Prohibition of najs (impurities) and cross-contamination controls",
      "Traceability from source to finished product",
      "Competent Muslim supervision at critical control points",
      "Labelling that does not mislead on halal status",
    ],
    adoptedBy: ["SMIIC members", "GSO (aligned)", "Multiple national bodies"],
    related: ["OIC/SMIIC 2", "OIC/SMIIC 3", "GSO 2055-1"],
    languages: "English, Arabic",
    note: "Widely used as the alignment reference for mutual recognition between OIC member states.",
  },
  {
    id: "HO-STD-0002",
    code: "MS 1500:2019",
    region: "SE Asia",
    status: "In force",
    access: "Purchase",
    year: "2019",
    supersedes: "MS 1500:2009",
    title: "Halal Food — General Requirements (Third Revision)",
    orgCountry: "Department of Standards Malaysia · JAKIM · Malaysia",
    tags: ["Food", "National", "Slaughter"],
    description:
      "Malaysia's national halal food standard underpinning JAKIM certification — one of the most internationally recognised national schemes.",
    requirements: [
      "Halal slaughter by a competent Muslim slaughterman",
      "Dedicated halal lines or verified cleansing (sertu) where required",
      "Good hygiene and GMP practices throughout",
      "Ingredient-level halal verification and documentation",
      "No contamination with non-halal or najs materials",
    ],
    adoptedBy: ["JAKIM", "State religious authorities (Malaysia)"],
    related: ["MS 2400", "OIC/SMIIC 1", "MS 2424"],
    languages: "Malay, English",
  },
  {
    id: "HO-STD-0003",
    code: "GSO 2055-1:2015",
    region: "Middle East",
    status: "In force",
    access: "Purchase",
    year: "2015",
    title: "Halal Food — General Requirements",
    orgCountry: "GSO · GCC Standardization Organization",
    tags: ["Food", "Regional", "GCC"],
    description:
      "The GCC regional halal food standard applied across member states, closely aligned with the OIC/SMIIC reference.",
    requirements: [
      "Only halal-permitted animals and ingredients",
      "Islamic slaughter requirements for meat and poultry",
      "Segregation and dedicated handling of halal products",
      "Import certificate acceptance from recognised bodies",
      "Conformity assessment and market surveillance",
    ],
    adoptedBy: ["Saudi Arabia", "UAE", "Kuwait", "Qatar", "Bahrain", "Oman"],
    related: ["GSO 2055-2", "OIC/SMIIC 1", "SFDA.FD"],
    languages: "Arabic, English",
    note: "Certificate acceptance in GCC markets often references GSO conformity alongside national schemes.",
  },
  {
    id: "HO-STD-0004",
    code: "SNI 99001:2016",
    region: "SE Asia",
    status: "In force",
    access: "Free",
    year: "2016",
    title: "Halal Management System",
    orgCountry: "BSN (National Standardization Agency) · Indonesia",
    tags: ["Management System", "National"],
    description:
      "Indonesia's halal management system standard supporting the national mandatory certification framework administered by BPJPH.",
    requirements: [
      "Documented halal assurance system (SJH)",
      "Appointment of a halal supervisor / internal halal team",
      "Ingredient approval and traceability procedures",
      "Internal audit and management review",
      "Corrective action for halal non-conformities",
    ],
    adoptedBy: ["BPJPH", "LPPOM MUI"],
    related: ["OIC/SMIIC 1", "MS 1500"],
    languages: "Indonesian, English",
  },
  {
    id: "HO-STD-0005",
    code: "SFDA.FD 2210",
    region: "Middle East",
    status: "In force",
    access: "Purchase",
    year: "2018",
    title: "Requirements for Halal Food Products",
    orgCountry: "Saudi Food & Drug Authority · Saudi Arabia",
    tags: ["Food", "National", "Import"],
    description:
      "The Saudi technical requirements applied by SFDA for halal food placed on the market and imported into the Kingdom.",
    requirements: [
      "Compliance with Islamic slaughter and ingredient rules",
      "Recognised certificate body accreditation for imports",
      "Labelling and Arabic language requirements",
      "Laboratory verification where flagged",
    ],
    adoptedBy: ["SFDA"],
    related: ["GSO 2055-1", "OIC/SMIIC 1"],
    languages: "Arabic, English",
  },
  {
    id: "HO-STD-0006",
    code: "SANS 1948:2012",
    region: "Africa",
    status: "In force",
    access: "Purchase",
    year: "2012",
    title: "Halaal Products and Services",
    orgCountry: "South African Bureau of Standards · South Africa",
    tags: ["Food", "Services", "National"],
    description:
      "South Africa's national halal standard covering products and services, referenced by local certifiers such as SANHA and NIHT.",
    requirements: [
      "Halal slaughter and processing controls",
      "Segregation from prohibited materials",
      "Certifier oversight and record-keeping",
      "Cleansing procedures for shared equipment",
    ],
    adoptedBy: ["SANHA", "NIHT", "MJC (aligned)"],
    related: ["OIC/SMIIC 1"],
    languages: "English",
  },
  {
    id: "HO-STD-0007",
    code: "PS 3733:2016",
    region: "South Asia",
    status: "In force",
    access: "Purchase",
    year: "2016",
    title: "Halal Food Management System — Requirements",
    orgCountry: "Pakistan Standards & Quality Control Authority · Pakistan",
    tags: ["Management System", "National"],
    description:
      "Pakistan's halal food management system standard supporting national certification and export compliance efforts.",
    requirements: [
      "Halal control points across production",
      "Documented halal assurance procedures",
      "Competent supervision and staff training",
      "Traceability and recall readiness",
    ],
    adoptedBy: ["PSQCA", "PNAC (accreditation)"],
    related: ["OIC/SMIIC 1", "MS 1500"],
    languages: "English, Urdu",
  },
  {
    id: "HO-STD-0008",
    code: "TS OIC/SMIIC 1",
    region: "Europe",
    status: "In force",
    access: "Purchase",
    year: "2020",
    title: "General Requirements for Halal Food (Turkish adoption)",
    orgCountry: "Turkish Standards Institution (TSE) · Türkiye",
    tags: ["Food", "National", "SMIIC-aligned"],
    description:
      "Türkiye's national adoption of the OIC/SMIIC halal food standard, operated via TSE and the HAK accreditation body.",
    requirements: [
      "Alignment with OIC/SMIIC 1 requirements",
      "Islamic slaughter and ingredient conformity",
      "Accredited certification via HAK-recognised bodies",
      "Segregation and contamination controls",
    ],
    adoptedBy: ["TSE", "HAK (Halal Accreditation Agency)"],
    related: ["OIC/SMIIC 1", "GSO 2055-1"],
    languages: "Turkish, English",
    note: "Türkiye hosts SMIIC and its Halal Accreditation Agency (HAK), giving this adoption broad recognition.",
  },
]
