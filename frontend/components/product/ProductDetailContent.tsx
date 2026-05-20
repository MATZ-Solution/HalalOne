import type { Product } from "@/types/product"
import { statusBadge, statusDot } from "@/utils/halalStatus"
import DetailSection from "./DetailSection"
import TagList from "./TagList"

type ProductDetailContentProps = {
    product: Product
}

function hasItems(items?: string[]) {
    return items && items.length > 0
}

export default function ProductDetailContent({ product }: ProductDetailContentProps) {
    const status = product.halal_status ?? "Unknown"
    const categories = [product.category_l1, product.category_l2].filter(Boolean) as string[]

    return (
        <div className="flex flex-col gap-y-5">
            {/* Status */}
            <div className="flex items-center gap-x-2">
                <span
                    className={`inline-flex items-center gap-x-1.5 text-xs switzer-500 px-2.5 py-1 rounded-full ${statusBadge(status)}`}
                >
                    <span className={`w-1.5 h-1.5 rounded-full ${statusDot(status)}`} />
                    {status}
                </span>
            </div>

            {categories.length > 0 && (
                <DetailSection label="Category">
                    <TagList items={categories} />
                </DetailSection>
            )}

            {hasItems(product.companies) && (
                <DetailSection label="Companies">
                    <p className="text-sm text-white/70 switzer-400 leading-relaxed">
                        {product.companies?.map(company =>
                            company.charAt(0).toUpperCase() + company.slice(1).toLowerCase()
                        ).join(" · ")}
                    </p>
                </DetailSection>
            )}

            {hasItems(product.typical_uses) && (
                <DetailSection label="Typical Uses">
                    <TagList items={product.typical_uses!} />
                </DetailSection>
            )}

            {hasItems(product.health_info) && (
                <DetailSection label="Health Info">
                    <ul className="flex flex-col gap-y-2">
                        {product.health_info!.map((info, i) => (
                            <li
                                key={i}
                                className="text-sm text-white/60 switzer-400 leading-relaxed pl-3 border-l border-white/10"
                            >
                                {info}
                            </li>
                        ))}
                    </ul>
                </DetailSection>
            )}

            {(hasItems(product.cert_bodies) || hasItems(product.cert_numbers)) && (
                <DetailSection label="Certification">
                    <div className="flex flex-col gap-y-2">
                        {hasItems(product.cert_bodies) && (
                            <TagList items={product.cert_bodies!} variant="cert" />
                        )}
                        {hasItems(product.cert_numbers) && (
                            <p className="text-xs text-white/40 switzer-400">
                                {product.cert_numbers!.join(" · ")}
                            </p>
                        )}
                    </div>
                </DetailSection>
            )}

            {(hasItems(product.sold_in) || hasItems(product.marketplace)) && (
                <DetailSection label="Availability">
                    <div className="flex flex-col gap-y-2">
                        {hasItems(product.sold_in) && (
                            <div className="flex flex-col gap-y-1">
                                <span className="text-[10px] text-white/25 switzer-400">Sold in</span>
                                <TagList items={product.sold_in!} />
                            </div>
                        )}
                        {hasItems(product.marketplace) && (
                            <div className="flex flex-col gap-y-1">
                                <span className="text-[10px] text-white/25 switzer-400">Marketplace</span>
                                <TagList items={product.marketplace!} />
                            </div>
                        )}
                    </div>
                </DetailSection>
            )}

            {(hasItems(product.fda_numbers) || hasItems(product.barcodes)) && (
                <DetailSection label="Identifiers">
                    <div className="flex flex-col gap-y-2 text-xs switzer-400 text-white/40">
                        {hasItems(product.fda_numbers) && (
                            <p>
                                <span className="text-white/25">FDA </span>
                                {product.fda_numbers!.join(" · ")}
                            </p>
                        )}
                        {hasItems(product.barcodes) && (
                            <p>
                                <span className="text-white/25">Barcode </span>
                                {product.barcodes!.join(" · ")}
                            </p>
                        )}
                    </div>
                </DetailSection>
            )}
        </div>
    )
}
