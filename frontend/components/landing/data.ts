// Content for the Halal One landing page. Ported verbatim from the design
// export's data script so the marketing copy and demo data stay in one place.

export const heroStats = [
  { value: "2.4M", label: "Products verified" },
  { value: "57", label: "Countries" },
  { value: "180+", label: "Authorities" },
]

export const certAuthorities = [
  "JAKIM · Malaysia", "IFANCA · USA", "ESMA · UAE", "BPJPH · Indonesia",
  "MUIS · Singapore", "SANHA · S. Africa", "GAC · Saudi Arabia", "CICOT · Thailand",
]

export const suggestedPrompts = [
  "Is E471 halal?",
  "Verify a certification number",
  "Which gelatin sources are halal?",
  "Find halal confectionery in the GCC",
]

export const aiCapabilities = [
  { icon: "shield-check", title: "Product verification", desc: "Confirms certificate validity and traceability in real time." },
  { icon: "flask-conical", title: "Ingredient intelligence", desc: "Decodes E-numbers and additives, flagging source-dependent items." },
  { icon: "quote", title: "Cited explanations", desc: "Every answer links back to standards and repository records." },
]

export const products = [
  { brand: "Nestlé", name: "MILO Activ-Go", country: "Malaysia", authority: "JAKIM", confidence: "98%", badge: "verified", statusLabel: "Verified", icon: "cup-soda", summary: "All 14 ingredients cross-referenced; certificate active and traceable to source." },
  { brand: "Al Islami", name: "Beef Burgers", country: "UAE", authority: "ESMA", confidence: "96%", badge: "verified", statusLabel: "Verified", icon: "beef", summary: "Slaughter and processing certified; supply chain fully documented." },
  { brand: "Wall's", name: "Vanilla Ice Cream", country: "Indonesia", authority: "BPJPH", confidence: "92%", badge: "verified", statusLabel: "Verified", icon: "ice-cream", summary: "Emulsifiers confirmed plant-derived; certificate valid through 2026." },
  { brand: "Generic import", name: "Fruit Gummies", country: "Germany", authority: "None on file", confidence: "41%", badge: "warning", statusLabel: "Review", icon: "candy", summary: "Porcine-derived gelatin detected; no active halal certificate on record." },
] as const

export const repoFilters = ["Certification authority", "Country", "Category", "Manufacturer", "Status"]

export const repoData = [
  { name: "MILO Activ-Go 1kg", meta: "Nestlé · Malaysia · Beverages · JAKIM/2024/8821", icon: "package", badge: "verified", statusLabel: "Verified", updated: "2 days ago" },
  { name: "IFANCA Certificate #A-40921", meta: "Certification authority · United States · Active", icon: "stamp", badge: "verified", statusLabel: "Active", updated: "1 week ago" },
  { name: "Mono- and diglycerides (E471)", meta: "Ingredient · Source-dependent · 3,102 products", icon: "flask-conical", badge: "warning", statusLabel: "Review", updated: "4 days ago" },
  { name: "Al Islami Frozen Foods", meta: "Manufacturer · UAE · 214 certified products", icon: "building-2", badge: "verified", statusLabel: "Verified", updated: "3 days ago" },
] as const

export const trending = ["Halal gelatin sources", "E471", "GCC confectionery", "JAKIM certificates", "Plant-based emulsifiers"]

export const scanSteps = [
  { icon: "camera", title: "Capture", desc: "Photograph any product label." },
  { icon: "scan-line", title: "Extract", desc: "OCR reads every listed ingredient." },
  { icon: "git-compare", title: "Cross-reference", desc: "Each item checked against the repository." },
  { icon: "shield-check", title: "Verdict", desc: "Confidence-scored result with cited sources." },
]

export const scanIngredients = [
  { name: "Sugar", icon: "check", color: "var(--green-700)", tag: "Halal" },
  { name: "Cocoa butter", icon: "check", color: "var(--green-700)", tag: "Halal" },
  { name: "Emulsifier (E471)", icon: "alert-triangle", color: "var(--gold-500)", tag: "Verify" },
  { name: "Skimmed milk powder", icon: "check", color: "var(--green-700)", tag: "Halal" },
  { name: "Natural vanilla", icon: "check", color: "var(--green-700)", tag: "Halal" },
]

export const mobileFeatures = [
  { icon: "scan-line", label: "Scan", desc: "Read any label instantly." },
  { icon: "message-circle", label: "Ask", desc: "Chat with the assistant." },
  { icon: "compass", label: "Discover", desc: "Find certified products." },
  { icon: "shield-check", label: "Verify", desc: "Check certificates live." },
  { icon: "clock", label: "History", desc: "Revisit past scans." },
  { icon: "bar-chart-3", label: "Insights", desc: "Track your choices." },
]

export const kpis = [
  { label: "Products verified", value: "2.4M", delta: "+18% YoY" },
  { label: "Countries covered", value: "57", delta: "+6 this year" },
  { label: "Certification authorities", value: "180+", delta: "+24 new" },
  { label: "Ingredients indexed", value: "48K", delta: "+12% QoQ" },
]

export const growthBars = [
  { m: "J", h: "38%" }, { m: "F", h: "44%" }, { m: "M", h: "50%" }, { m: "A", h: "47%" },
  { m: "M", h: "58%" }, { m: "J", h: "64%" }, { m: "J", h: "70%" }, { m: "A", h: "68%" },
  { m: "S", h: "78%" }, { m: "O", h: "84%" }, { m: "N", h: "92%" }, { m: "D", h: "100%" },
]

export const regions = [
  { name: "Southeast Asia", pct: "94%" },
  { name: "GCC & Middle East", pct: "88%" },
  { name: "Europe", pct: "72%" },
  { name: "North America", pct: "65%" },
  { name: "Africa", pct: "58%" },
]

export const trustPillars = [
  { icon: "landmark", title: "ICCD governance", desc: "Developed under the Islamic Chamber of Commerce & Development." },
  { icon: "book-open", title: "Recognised standards", desc: "Aligned to MS1500 and leading national halal standards." },
  { icon: "database", title: "Traceable data", desc: "Every record links to its certifying authority and source." },
  { icon: "users", title: "Serves the ecosystem", desc: "Consumers, business, governments and OIC institutions." },
]

export const socials = ["linkedin", "twitter", "youtube", "globe"]

export const footerCols = [
  { title: "Platform", links: ["AI Assistant", "Repository", "Business Directory", "OCR Scanner", "Mobile app"] },
  { title: "Resources", links: ["Standards", "Certification lookup", "News & alerts", "API"] },
  { title: "Research", links: ["Datasets", "Knowledge graph", "Market intelligence", "Reports"] },
  { title: "Institution", links: ["About ICCD", "Partners", "Contact", "Careers"] },
]
