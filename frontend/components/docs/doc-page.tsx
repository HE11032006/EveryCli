import Link from "next/link"
import { ArrowLeft, ArrowRight } from "lucide-react"
import { docsFlat } from "@/lib/site"

interface DocPageProps {
  eyebrow: string
  title: string
  description: string
  href: string
  children: React.ReactNode
}

export function DocPage({ eyebrow, title, description, href, children }: DocPageProps) {
  const index = docsFlat.findIndex((i) => i.href === href)
  const prev = index > 0 ? docsFlat[index - 1] : null
  const next = index >= 0 && index < docsFlat.length - 1 ? docsFlat[index + 1] : null

  return (
    <article className="mx-auto max-w-3xl">
      {/* Eyebrow */}
      <div className="flex items-center gap-3 mb-6">
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#ea580c]">
          {eyebrow}
        </span>
        <div className="flex-1 border-t border-border" />
      </div>

      {/* Title */}
      <h1 className="font-pixel text-3xl sm:text-4xl lg:text-5xl tracking-tight text-foreground text-balance">
        {title}
      </h1>
      <p className="mt-4 text-sm font-mono leading-relaxed text-muted-foreground text-pretty">
        {description}
      </p>

      <div className="my-8 border-t-2 border-foreground" />

      {/* Content */}
      <div className="doc-content flex flex-col gap-6">{children}</div>

      {/* Prev / Next */}
      <div className="mt-16 grid grid-cols-1 gap-4 border-t-2 border-foreground pt-8 sm:grid-cols-2">
        {prev ? (
          <Link
            href={prev.href}
            className="group flex flex-col gap-1 border-2 border-foreground p-4 hover:bg-foreground hover:text-background transition-colors"
          >
            <span className="flex items-center gap-1.5 text-[10px] font-mono tracking-widest uppercase text-muted-foreground group-hover:text-background/70">
              <ArrowLeft size={12} strokeWidth={2} /> Previous
            </span>
            <span className="text-sm font-mono font-bold">{prev.title}</span>
          </Link>
        ) : (
          <div />
        )}
        {next ? (
          <Link
            href={next.href}
            className="group flex flex-col gap-1 border-2 border-foreground p-4 text-right hover:bg-foreground hover:text-background transition-colors sm:items-end"
          >
            <span className="flex items-center gap-1.5 text-[10px] font-mono tracking-widest uppercase text-muted-foreground group-hover:text-background/70">
              Next <ArrowRight size={12} strokeWidth={2} />
            </span>
            <span className="text-sm font-mono font-bold">{next.title}</span>
          </Link>
        ) : (
          <div />
        )}
      </div>
    </article>
  )
}
