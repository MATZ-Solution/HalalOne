// Representative Halal Market Intelligence dataset. The original design loaded
// this from an external `market-data.js`; recreated here as typed data.
// Aggregated third-party estimates for orientation — not investment advice.

export type BigStat = { v: string; l: string; n: string }
export type TimelinePoint = { y: string; v: string; f?: string; est?: boolean }
export type Country = {
  flag: string; name: string; region: string; size: string; bar: number
  yoy: string; muslim: string; muslimPct: string; perCap: string
  maturity: string; role: string; cats: string
}
export type Sector = { name: string; size: string; pctOfMkt: string; bar: number; cagr: string; topMarkets: string; keyPlayers: string; note: string }
export type Trend = { icon: string; title: string; desc: string }
export type Corridor = { from: string; to: string; category: string; value: string; yoy: string; players: string; notes: string }

export const bigStats: BigStat[] = [
  { v: "$2.1T", l: "Global halal economy", n: "Across food, finance, pharma, cosmetics, travel and media." },
  { v: "$1.4T", l: "Halal food & beverage", n: "The largest single sector by spend." },
  { v: "1.9B", l: "Muslim consumers", n: "≈24% of the world population, growing faster than average." },
  { v: "8.1%", l: "Blended CAGR", n: "Projected annual growth of the halal economy to 2029." },
]

export const timeline: TimelinePoint[] = [
  { y: "2022", v: "1,670" },
  { y: "2023", v: "1,810" },
  { y: "2024", v: "1,960" },
  { y: "2025", v: "2,100", f: "Now", est: true },
  { y: "2026", v: "2,280", f: "Fcst" },
  { y: "2027", v: "2,470", f: "Fcst" },
  { y: "2028", v: "2,680", f: "Fcst" },
  { y: "2029", v: "2,900", f: "Fcst" },
]

export const countries: Country[] = [
  { flag: "🇮🇩", name: "Indonesia", region: "SE Asia", size: "$210B", bar: 100, yoy: "+9.1%", muslim: "242M", muslimPct: "87%", perCap: "$868", maturity: "Mature", role: "Largest consumer market", cats: "Food, modest fashion, finance" },
  { flag: "🇸🇦", name: "Saudi Arabia", region: "Middle East", size: "$168B", bar: 80, yoy: "+7.4%", muslim: "34M", muslimPct: "93%", perCap: "$4,940", maturity: "Mature", role: "High per-capita hub", cats: "Food, pharma, travel" },
  { flag: "🇹🇷", name: "Türkiye", region: "Europe", size: "$155B", bar: 74, yoy: "+8.0%", muslim: "84M", muslimPct: "98%", perCap: "$1,845", maturity: "Mature", role: "Manufacturing & export base", cats: "Food, cosmetics, textiles" },
  { flag: "🇦🇪", name: "United Arab Emirates", region: "Middle East", size: "$92B", bar: 44, yoy: "+10.2%", muslim: "8M", muslimPct: "76%", perCap: "$11,500", maturity: "Mature", role: "Re-export & standards hub", cats: "Food, logistics, finance" },
  { flag: "🇲🇾", name: "Malaysia", region: "SE Asia", size: "$88B", bar: 42, yoy: "+8.8%", muslim: "20M", muslimPct: "63%", perCap: "$4,400", maturity: "Mature", role: "Certification leader (JAKIM)", cats: "Food, pharma, finance" },
  { flag: "🇵🇰", name: "Pakistan", region: "South Asia", size: "$72B", bar: 34, yoy: "+7.9%", muslim: "231M", muslimPct: "96%", perCap: "$312", maturity: "Emerging", role: "High-volume consumer base", cats: "Food, textiles" },
  { flag: "🇪🇬", name: "Egypt", region: "Africa", size: "$61B", bar: 29, yoy: "+6.8%", muslim: "95M", muslimPct: "90%", perCap: "$642", maturity: "Emerging", role: "North Africa gateway", cats: "Food, pharma" },
  { flag: "🇧🇩", name: "Bangladesh", region: "South Asia", size: "$54B", bar: 26, yoy: "+9.6%", muslim: "153M", muslimPct: "91%", perCap: "$353", maturity: "Emerging", role: "Fast-growing demand", cats: "Food, modest fashion" },
  { flag: "🇳🇬", name: "Nigeria", region: "Africa", size: "$43B", bar: 20, yoy: "+11.0%", muslim: "104M", muslimPct: "50%", perCap: "$413", maturity: "Frontier", role: "Sub-Saharan anchor", cats: "Food, cosmetics" },
  { flag: "🇬🇧", name: "United Kingdom", region: "Europe", size: "$28B", bar: 13, yoy: "+6.1%", muslim: "4M", muslimPct: "6.5%", perCap: "$7,000", maturity: "Mature", role: "Western halal benchmark", cats: "Food, finance" },
  { flag: "🇺🇸", name: "United States", region: "Americas", size: "$25B", bar: 12, yoy: "+7.2%", muslim: "4.5M", muslimPct: "1.3%", perCap: "$5,550", maturity: "Emerging", role: "Premium niche growth", cats: "Food, cosmetics" },
  { flag: "🇿🇦", name: "South Africa", region: "Africa", size: "$14B", bar: 7, yoy: "+5.9%", muslim: "1.1M", muslimPct: "1.9%", perCap: "$12,700", maturity: "Emerging", role: "SANHA-certified export base", cats: "Food, logistics" },
]

export const sectors: Sector[] = [
  { name: "Food & Beverage", size: "$1.4T", pctOfMkt: "67% of market", bar: 100, cagr: "7.9%", topMarkets: "Indonesia, Saudi Arabia, Türkiye", keyPlayers: "Nestlé, BRF, Al Islami, Kawan", note: "The anchor sector; certification recognition is the primary route to market access." },
  { name: "Islamic Finance", size: "$3.9T*", pctOfMkt: "Assets under mgmt", bar: 78, cagr: "10.1%", topMarkets: "GCC, Malaysia, Iran", keyPlayers: "Al Rajhi, Bank Islam, Dubai Islamic", note: "Measured by AUM rather than spend; underpins halal trade financing." },
  { name: "Modest Fashion", size: "$318B", pctOfMkt: "15% of market", bar: 45, cagr: "6.2%", topMarkets: "Türkiye, Indonesia, UAE", keyPlayers: "Modanisa, Hijup, regional brands", note: "Fast-growing lifestyle segment with strong e-commerce penetration." },
  { name: "Pharma & Cosmetics", size: "$196B", pctOfMkt: "9% of market", bar: 32, cagr: "9.4%", topMarkets: "Malaysia, Indonesia, GCC", keyPlayers: "Pharmaniaga, Wardah, Simplysiti", note: "Halal certification of medicines (MS 2424) is an emerging differentiator." },
  { name: "Halal Travel", size: "$189B", pctOfMkt: "9% of market", bar: 30, cagr: "8.7%", topMarkets: "Saudi Arabia, Malaysia, Türkiye", keyPlayers: "OTAs, Muslim-friendly hotels", note: "Umrah/Hajj plus leisure; rebounded strongly post-pandemic." },
  { name: "Media & Recreation", size: "$247B", pctOfMkt: "Adjacent spend", bar: 38, cagr: "7.0%", topMarkets: "Indonesia, GCC, Egypt", keyPlayers: "Streaming, gaming, publishing", note: "Values-aligned content; an adjacent rather than certified category." },
]

export const trends: Trend[] = [
  { icon: "🌐", title: "Standards convergence", desc: "SMIIC alignment and mutual-recognition deals are reducing duplicate certification across markets." },
  { icon: "🔗", title: "Traceability tech", desc: "Blockchain and digital certificates are being piloted to verify halal integrity end-to-end." },
  { icon: "📱", title: "Consumer apps", desc: "Ingredient scanners and verification apps are shifting trust from labels to real-time checks." },
  { icon: "🧪", title: "Ingredient scrutiny", desc: "Source-dependent additives (gelatin, E471) are driving demand for transparent supply chains." },
  { icon: "🏦", title: "Finance integration", desc: "Islamic trade finance is increasingly bundled with halal certification and logistics." },
  { icon: "🚢", title: "Cold-chain halal", desc: "Segregated logistics and warehousing are becoming a competitive requirement for exporters." },
  { icon: "🌱", title: "Plant-based shift", desc: "Plant-derived emulsifiers and proteins simplify halal compliance and appeal to younger buyers." },
  { icon: "🛰️", title: "Emerging markets", desc: "Sub-Saharan Africa and Central Asia are the fastest-growing frontier demand centres." },
]

export const corridors: Corridor[] = [
  { from: "Brazil", to: "Saudi Arabia", category: "Poultry & Meat", value: "$2.4B", yoy: "+9%", players: "BRF, Sadia", notes: "The world's largest halal poultry corridor; demand consistently outpaces domestic supply." },
  { from: "Australia", to: "Indonesia", category: "Beef & Livestock", value: "$1.6B", yoy: "+6%", players: "Australian exporters", notes: "Live cattle and boxed beef into the largest Muslim-majority market; gated by recognised certification." },
  { from: "India", to: "UAE", category: "Basmati & Cereals", value: "$1.1B", yoy: "+4%", players: "Rice exporters", notes: "High-volume staple corridor into a re-export hub; low certification friction." },
  { from: "Malaysia", to: "China", category: "Processed Food", value: "$780M", yoy: "+15%", players: "Kawan, Nestlé MY", notes: "JAKIM recognition gives a trust premium into a fast-growing Chinese halal segment." },
  { from: "Türkiye", to: "Germany", category: "Confectionery & Bakery", value: "$540M", yoy: "+3%", players: "Turkish manufacturers", notes: "Serves a large European Muslim consumer base; mature and competitive." },
  { from: "Netherlands", to: "GCC", category: "Dairy & Nutrition", value: "$620M", yoy: "+7%", players: "EU dairy majors", notes: "Premium infant nutrition and dairy; EU certifier recognition is the key unlock." },
  { from: "Thailand", to: "Malaysia", category: "Seafood & Ready Meals", value: "$430M", yoy: "+8%", players: "CICOT-certified firms", notes: "Short-logistics corridor with mutually familiar certification." },
  { from: "Pakistan", to: "GCC", category: "Meat & Livestock", value: "$390M", yoy: "+11%", players: "Chilled-meat exporters", notes: "Cost-competitive with rising volumes; cold-chain consistency is the growth lever." },
]
