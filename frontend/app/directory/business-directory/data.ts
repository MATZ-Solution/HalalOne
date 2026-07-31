// Representative Business Directory dataset.
// The original design loaded this from an external `business-data.js`; recreated
// here as typed data. All entries are illustrative reference records — verify
// certification directly with each business.

export type Business = {
  id: string
  name: string
  location: string
  country: string
  region: "Africa" | "Americas" | "Europe" | "Middle East" | "Oceania" | "SE Asia" | "South Asia"
  type:
    | "Manufacturer"
    | "Pharmaceutical"
    | "Cosmetics"
    | "Food Service"
    | "Retail"
    | "Logistics"
    | "Finance"
    | "Certification Body"
    | "Ingredient Supplier"
  trust: "Verified" | "Self-declared"
  certBody: string
  exportMarkets: string
  categories: string
  notes: string
  url?: string
  urlLabel?: string
}

export const BUSINESSES: Business[] = [
  {
    id: "HO-BIZ-0001",
    name: "Al Islami Foods",
    location: "Dubai, United Arab Emirates",
    country: "United Arab Emirates",
    region: "Middle East",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "ESMA / HALAL UAE",
    exportMarkets: "GCC, KSA, UK, Malaysia, Canada",
    categories: "Frozen poultry, processed meats, ready meals",
    notes:
      "One of the region's largest halal frozen-food producers, operating dedicated halal slaughter and processing lines audited under the UAE national scheme.",
    url: "https://www.alislamifoods.com",
    urlLabel: "alislamifoods.com",
  },
  {
    id: "HO-BIZ-0002",
    name: "Nestlé Malaysia",
    location: "Petaling Jaya, Malaysia",
    country: "Malaysia",
    region: "SE Asia",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "JAKIM",
    exportMarkets: "ASEAN, Middle East, Australia, Japan",
    categories: "Beverages, confectionery, dairy, culinary",
    notes:
      "Operates multiple JAKIM-certified manufacturing sites; among the earliest multinationals to build fully halal supply chains across an ASEAN market.",
    url: "https://www.nestle.com.my",
    urlLabel: "nestle.com.my",
  },
  {
    id: "HO-BIZ-0003",
    name: "BRF (Sadia)",
    location: "São Paulo, Brazil",
    country: "Brazil",
    region: "Americas",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "FAMBRAS Halal",
    exportMarkets: "KSA, UAE, Turkey, Malaysia, Egypt",
    categories: "Poultry, further-processed protein",
    notes:
      "Major global poultry exporter with plants certified for export to OIC markets; certification scope is plant- and product-specific.",
    url: "https://www.brf-global.com",
    urlLabel: "brf-global.com",
  },
  {
    id: "HO-BIZ-0004",
    name: "Simply Halal Wholesale",
    location: "Birmingham, United Kingdom",
    country: "United Kingdom",
    region: "Europe",
    type: "Retail",
    trust: "Self-declared",
    certBody: "—",
    exportMarkets: "United Kingdom, Ireland",
    categories: "Grocery distribution, frozen, ambient",
    notes:
      "Regional wholesaler aggregating certified brands; listing is self-declared and product-level certification varies by supplier.",
  },
  {
    id: "HO-BIZ-0005",
    name: "Pharmaniaga Berhad",
    location: "Shah Alam, Malaysia",
    country: "Malaysia",
    region: "SE Asia",
    type: "Pharmaceutical",
    trust: "Verified",
    certBody: "JAKIM (MS 2424)",
    exportMarkets: "ASEAN, GCC",
    categories: "Generics, halal pharmaceuticals, vaccines logistics",
    notes:
      "Pioneer of halal-certified pharmaceutical manufacturing under the MS 2424 standard for halal medicines.",
    url: "https://www.pharmaniaga.com",
    urlLabel: "pharmaniaga.com",
  },
  {
    id: "HO-BIZ-0006",
    name: "Wardah Cosmetics (Paragon)",
    location: "Jakarta, Indonesia",
    country: "Indonesia",
    region: "SE Asia",
    type: "Cosmetics",
    trust: "Verified",
    certBody: "BPJPH / LPPOM MUI",
    exportMarkets: "Indonesia, Malaysia, GCC, Nigeria",
    categories: "Colour cosmetics, skincare, personal care",
    notes:
      "Halal-certified cosmetics brand certified under Indonesia's national halal assurance system (BPJPH).",
    url: "https://www.wardahbeauty.com",
    urlLabel: "wardahbeauty.com",
  },
  {
    id: "HO-BIZ-0007",
    name: "Kawan Food Berhad",
    location: "Selangor, Malaysia",
    country: "Malaysia",
    region: "SE Asia",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "JAKIM",
    exportMarkets: "North America, Europe, Australia, GCC",
    categories: "Frozen paratha, roti, ready-to-eat",
    notes:
      "Frozen ethnic-food manufacturer exporting to over 40 markets under JAKIM certification.",
    url: "https://www.kawanfood.com",
    urlLabel: "kawanfood.com",
  },
  {
    id: "HO-BIZ-0008",
    name: "Midamar Corporation",
    location: "Cedar Rapids, USA",
    country: "United States",
    region: "Americas",
    type: "Food Service",
    trust: "Verified",
    certBody: "IFANCA",
    exportMarkets: "USA, GCC, SE Asia",
    categories: "Halal meats, food service supply, distribution",
    notes:
      "Long-established US halal food-service supplier working with IFANCA-certified processors.",
    url: "https://www.midamar.com",
    urlLabel: "midamar.com",
  },
  {
    id: "HO-BIZ-0009",
    name: "DP World Halal Logistics",
    location: "Dubai, United Arab Emirates",
    country: "United Arab Emirates",
    region: "Middle East",
    type: "Logistics",
    trust: "Self-declared",
    certBody: "—",
    exportMarkets: "Global",
    categories: "Cold-chain, warehousing, halal segregation",
    notes:
      "Freight and warehousing provider offering segregated halal cold-chain handling; segregation practices are self-declared at facility level.",
  },
  {
    id: "HO-BIZ-0010",
    name: "Bank Islam Malaysia",
    location: "Kuala Lumpur, Malaysia",
    country: "Malaysia",
    region: "SE Asia",
    type: "Finance",
    trust: "Verified",
    certBody: "Shariah Advisory Council (BNM)",
    exportMarkets: "Malaysia",
    categories: "Islamic banking, trade finance, takaful",
    notes:
      "Shariah-compliant banking overseen by the national Shariah Advisory Council; relevant for halal trade financing.",
    url: "https://www.bankislam.com",
    urlLabel: "bankislam.com",
  },
  {
    id: "HO-BIZ-0011",
    name: "Halal Development Corporation",
    location: "Cyberjaya, Malaysia",
    country: "Malaysia",
    region: "SE Asia",
    type: "Certification Body",
    trust: "Verified",
    certBody: "Government agency",
    exportMarkets: "—",
    categories: "Ecosystem development, accreditation support",
    notes:
      "Government-linked body coordinating Malaysia's halal industry development and standards ecosystem.",
    url: "https://www.hdcglobal.com",
    urlLabel: "hdcglobal.com",
  },
  {
    id: "HO-BIZ-0012",
    name: "Kerry Group — Halal Ingredients",
    location: "Tralee, Ireland",
    country: "Ireland",
    region: "Europe",
    type: "Ingredient Supplier",
    trust: "Verified",
    certBody: "HFA / IFANCA (site-specific)",
    exportMarkets: "Europe, GCC, SE Asia, Americas",
    categories: "Flavours, cultures, functional ingredients",
    notes:
      "Global taste-and-nutrition supplier offering halal-certified ingredient ranges from designated sites; certification is facility- and SKU-specific.",
    url: "https://www.kerry.com",
    urlLabel: "kerry.com",
  },
  {
    id: "HO-BIZ-0013",
    name: "Sunbulah Group",
    location: "Jeddah, Saudi Arabia",
    country: "Saudi Arabia",
    region: "Middle East",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "SFDA / GAC",
    exportMarkets: "GCC, Levant, North Africa",
    categories: "Frozen pastry, poultry, dairy",
    notes:
      "Saudi frozen-foods manufacturer operating under national food-authority oversight for the GCC market.",
    url: "https://www.sunbulah.com",
    urlLabel: "sunbulah.com",
  },
  {
    id: "HO-BIZ-0014",
    name: "Cape Halaal Meats",
    location: "Cape Town, South Africa",
    country: "South Africa",
    region: "Africa",
    type: "Food Service",
    trust: "Self-declared",
    certBody: "SANHA (pending renewal)",
    exportMarkets: "South Africa, SADC",
    categories: "Butchery, food-service protein supply",
    notes:
      "Regional butchery and food-service supplier; certification renewal pending, so the listing is treated as self-declared until confirmed.",
  },
  {
    id: "HO-BIZ-0015",
    name: "Byron Bay Halal Provisions",
    location: "New South Wales, Australia",
    country: "Australia",
    region: "Oceania",
    type: "Retail",
    trust: "Self-declared",
    certBody: "AFIC (member supplier)",
    exportMarkets: "Australia, New Zealand",
    categories: "Specialty grocery, imported halal brands",
    notes:
      "Boutique retailer stocking imported certified brands; store-level listing is self-declared.",
  },
  {
    id: "HO-BIZ-0016",
    name: "Al Kabeer Group",
    location: "Sharjah, United Arab Emirates",
    country: "United Arab Emirates",
    region: "Middle East",
    type: "Manufacturer",
    trust: "Verified",
    certBody: "HALAL UAE / ESMA",
    exportMarkets: "GCC, UK, Europe, South Asia",
    categories: "Frozen snacks, seafood, ready meals",
    notes:
      "Established frozen-foods manufacturer with UAE national-scheme certification across its retail ranges.",
    url: "https://www.alkabeer.com",
    urlLabel: "alkabeer.com",
  },
]
