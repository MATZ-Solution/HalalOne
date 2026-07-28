import type { Authority, Region } from "./authorities"

/** Filter buckets. Coarser than `Authority["type"]`, which is free text. */
export type TypeGroup = "Government" | "NGO" | "Standards" | "Commercial"

export const DOTS: Record<Region, string> = {
  "SE Asia": "#1A6B4A",
  "South Asia": "#2F6D8C",
  "Middle East": "#B8860B",
  Europe: "#6B5CA5",
  Africa: "#B5642E",
  Americas: "#2E8C7E",
  Oceania: "#8A5A9E",
  "East Asia": "#4A5568",
  International: "#37507A",
}

export const dotFor = (region: Region): string => DOTS[region] ?? "#4A5568"

/**
 * Bucket a free-text `type` into a filter group.
 *
 * Note the ordering: "Standards" is tested first, so ESMA — typed
 * "Government (Accreditation & Standards Body)" — groups under Standards rather
 * than Government. That is deliberate and matches the source design; the
 * "Government bodies" hero stat counts it separately via its own regex.
 */
export function typeGroup(t: string): TypeGroup {
  if (/Standards|Regional|Intergovernmental|Coordination/i.test(t)) return "Standards"
  if (/Commercial/i.test(t)) return "Commercial"
  if (/Government/i.test(t)) return "Government"
  return "NGO"
}

export type TypeStyle = { label: string; bg: string; fg: string }

export function typeStyle(g: TypeGroup): TypeStyle {
  if (g === "Government") return { label: "Government", bg: "#E4F0E9", fg: "#1A6B4A" }
  if (g === "Standards") return { label: "Standards", bg: "#ECEEF0", fg: "#41505A" }
  if (g === "Commercial") return { label: "Commercial", bg: "#E9EFF3", fg: "#345066" }
  return { label: "NGO / Religious", bg: "#FBF2DB", fg: "#94711A" }
}

/** Leading token of the name — "JISM (Bahrain)" → "JISM". */
export const codeOf = (name: string): string => name.split(/[\s(]/)[0]

/** Shrink the hex-badge code so longer ones still fit. */
export function codeSize(code: string): string {
  const n = code.length
  if (n <= 3) return "text-[20px]"
  if (n === 4) return "text-[17px]"
  if (n <= 6) return "text-[13.5px]"
  return "text-[11px]"
}

/** Condense `validity` prose into something that fits the card's stat cell. */
export function shortValidity(v: string): string {
  if (/N\/A|does not/i.test(v)) return "N/A"
  const m = v.match(/(\d[\d–\-\s]*year[s]?)/i)
  if (m) return m[1].replace(/\s+/g, " ").trim()
  if (/consignment/i.test(v)) return "Per import"
  return v.split(/[;(]/)[0].trim().slice(0, 16)
}

/** Split a "·"-separated field into its parts. */
export const segs = (str: string): string[] =>
  String(str || "")
    .split(/[·]/)
    .map((s) => s.trim())
    .filter(Boolean)

export function recText(a: Authority, group: TypeGroup): string {
  if (group === "Standards") return "Reference standards body"
  const n = segs(a.recognised).length
  if (n >= 3) return `Recognised in ${n}+ markets`
  if (n === 2) return "Recognised in key markets"
  return "Regional recognition"
}

/** Fields the free-text search scans. */
export const searchable = (a: Authority): string =>
  `${a.name} ${a.fullName} ${a.country} ${a.region} ${a.standard} ${a.scope} ${a.recognised} ${a.type}`.toLowerCase()
