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
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-[#f05243]">
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

      <div className="my-8 border-t border-white/15" />

      {/* Content */}
      <div data-doc-content className="doc-content flex flex-col gap-6">{children}</div>

      {/* Prev / Next */}
      <div className="mt-14 grid grid-cols-1 gap-3 border-t border-white/15 pt-7 sm:grid-cols-2">
        {prev ? (
          <Link
            href={prev.href}
            className="group flex min-h-24 flex-col gap-1 border border-white/15 p-4 hover:border-[#f05243]/70 hover:bg-white/[0.035] transition-colors"
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
            className="group flex min-h-24 flex-col gap-1 border border-white/15 p-4 text-right hover:border-[#f05243]/70 hover:bg-white/[0.035] transition-colors sm:items-end"
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
