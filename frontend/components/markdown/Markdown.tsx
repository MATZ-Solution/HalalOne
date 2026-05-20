import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import rehypeRaw from "rehype-raw"

export type Theme = "dark" | "light"

type MarkdownProps = {
    textContent: string | null
    theme?: Theme
}

const Markdown = ({ textContent, theme = "dark" }: MarkdownProps) => {
    const isLight = theme === "light"
    const text = isLight ? "text-black" : "text-white"
    const muted = isLight ? "text-black/60" : "text-white/60"
    const border = isLight ? "border-black/15" : "border-white/15"
    const codeBg = isLight ? "bg-black/5" : "bg-white/10"

    function preprocessContent(content: string) {
        if (!content) return ""
        let processed = content

        processed = processed.replace(/\\n/g, "\n")
        processed = processed.replace(/([^\n])\s*(#{1,6}\s)/g, "$1\n\n$2")
        processed = processed.replace(/(\|[ -]*\|)\s*(?=\|)/g, "$1\n")
        processed = processed.replace(/([^\n])\s*(-\s)/g, "$1\n$2")
        processed = processed.replace(/([^\n])\s*(\d+\.\s)/g, "$1\n$2")

        return processed
    }

    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw]}
            components={{
                h1: ({ node, ...props }) => (
                    <h1 className={`text-3xl font-bold ${text}`} {...props} />
                ),
                h2: ({ node, ...props }) => (
                    <h2 className={`text-2xl font-semibold ${text}`} {...props} />
                ),
                h3: ({ node, ...props }) => (
                    <h3 className={`text-xl font-semibold ${text}`} {...props} />
                ),
                h4: ({ node, ...props }) => (
                    <h4 className={`text-lg font-semibold ${text}`} {...props} />
                ),
                p: ({ node, ...props }) => (
                    <p className={`leading-7 my-2 wrap-break-word ${muted}`} {...props} />
                ),
                strong: ({ node, ...props }) => (
                    <strong className={`font-bold ${text}`} {...props} />
                ),
                em: ({ node, ...props }) => (
                    <em className={`italic ${muted}`} {...props} />
                ),
                ul: ({ node, ...props }) => (
                    <ul className={`list-disc pl-5 my-2 space-y-1 ${muted}`} {...props} />
                ),
                ol: ({ node, ...props }) => (
                    <ol className={`list-decimal pl-5 my-2 space-y-1 ${muted}`} {...props} />
                ),
                li: ({ node, ...props }) => (
                    <li className={muted} {...props} />
                ),
                a: ({ node, ...props }) => (
                    <a
                        className={`underline underline-offset-2 ${text} hover:opacity-70`}
                        target="_blank"
                        rel="noopener noreferrer"
                        {...props}
                    />
                ),
                blockquote: ({ node, ...props }) => (
                    <blockquote
                        className={`border-l-2 pl-4 my-3 italic ${border} ${muted}`}
                        {...props}
                    />
                ),
                code: ({ node, className, children, ...props }) => {
                    const isBlock = className?.includes("language-")
                    if (isBlock) {
                        return (
                            <code className={`block text-sm font-mono ${text}`} {...props}>
                                {children}
                            </code>
                        )
                    }
                    return (
                        <code
                            className={`text-sm font-mono px-1.5 py-0.5 rounded ${codeBg} ${text}`}
                            {...props}
                        >
                            {children}
                        </code>
                    )
                },
                pre: ({ node, ...props }) => (
                    <pre
                        className={`my-3 p-3 rounded-lg overflow-x-auto text-sm ${codeBg} border ${border}`}
                        {...props}
                    />
                ),
                table: ({ node, ...props }) => (
                    <div className="my-3 overflow-x-auto">
                        <table className={`w-full text-sm border-collapse ${muted}`} {...props} />
                    </div>
                ),
                thead: ({ node, ...props }) => (
                    <thead className={isLight ? "bg-black/5" : "bg-white/5"} {...props} />
                ),
                th: ({ node, ...props }) => (
                    <th className={`border px-3 py-2 text-left font-semibold ${border} ${text}`} {...props} />
                ),
                td: ({ node, ...props }) => (
                    <td className={`border px-3 py-2 ${border}`} {...props} />
                ),
                hr: ({ node, ...props }) => (
                    <hr className={`my-4 border-t ${border}`} {...props} />
                ),
            }}
        >
            {preprocessContent(textContent ?? "")}
        </ReactMarkdown>
    )
}

export default Markdown
