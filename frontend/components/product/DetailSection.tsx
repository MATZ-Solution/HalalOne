import type { ReactNode } from "react"

type DetailSectionProps = {
    label: string
    children: ReactNode
}

export default function DetailSection({ label, children }: DetailSectionProps) {
    return (
        <section className="flex flex-col gap-y-1.5">
            <h3 className="text-[11px] uppercase tracking-wider text-white/30 switzer-500">
                {label}
            </h3>
            <div>{children}</div>
        </section>
    )
}
