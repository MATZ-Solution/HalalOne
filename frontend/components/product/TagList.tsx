type TagListProps = {
    items: string[]
    variant?: "default" | "cert" | "muted"
}

const variantStyles = {
    default: "text-white/60 bg-white/[0.05] border-white/[0.08]",
    cert: "text-green-400/70 bg-green-500/[0.08] border-green-500/20",
    muted: "text-white/45 bg-white/[0.03] border-white/[0.06]",
}

export default function TagList({ items, variant = "default" }: TagListProps) {
    return (
        <div className="flex flex-wrap gap-1.5">
            {items.map((item, i) => (
                <span
                    key={`${item}-${i}`}
                    className={`text-xs switzer-400 border px-2 py-0.5 rounded-md ${variantStyles[variant]}`}
                >
                    {item}
                </span>
            ))}
        </div>
    )
}
