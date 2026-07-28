/** Mirrors searchable/filterable fields from backend/models/product_model.py */
export type Product = {
    canonical_id: string
    norm_name: string
    companies?: string[]
    cert_bodies?: string[]
    typical_uses?: string[]
    marketplace?: string[]
    category_l1?: string
    category_l2?: string
    halal_status?: string
    sold_in?: string[]
    cert_numbers?: string[]
    health_info?: string[]
    fda_numbers?: string[]
    barcodes?: string[]
    // Web-fallback provenance: verified=false marks an unverified web result,
    // grounding carries per-field source citations from the web search.
    verified?: boolean
    grounding?: FieldGrounding[]
}

export type FieldGrounding = {
    field: string
    citations: { url: string; title?: string }[]
    confidence?: string
}
