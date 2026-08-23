"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { Github, Search, X } from "lucide-react"
import { docsFlat, site } from "@/lib/site"

export function DocsNavbar() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault()
        setOpen(true)
      }
      if (event.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  useEffect(() => {
    if (!open) return
    setQuery("")
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }, [open])

  const results = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return docsFlat.slice(0, 6)
    return docsFlat.filter((item) => `${item.title} ${item.href}`.toLowerCase().includes(term))
  }, [query])

  return (
    <>
      <header className="sticky top-0 z-40 h-[66px] border-b border-white/10 bg-[#0a0908]/95 backdrop-blur-md">
        <div className="grid h-full grid-cols-[1fr_auto_1fr] items-center gap-5 px-5 sm:px-8 lg:px-10">
          <Link href="/" className="w-fit text-xl font-semibold tracking-tight text-white transition-colors hover:text-white/80">
            EveryCli
          </Link>

          <button
            type="button"
            onClick={() => setOpen(true)}
            aria-label="Search documentation"
            className="hidden h-12 w-[440px] items-center gap-3 border border-white/15 bg-white/[0.015] px-4 text-left text-sm text-white/75 transition-colors hover:border-white/30 md:flex"
          >
            <Search size={17} strokeWidth={1.75} className="text-white/70" />
            <span className="flex-1">Search documentation</span>
            <kbd className="border border-white/5 bg-white/[0.07] px-2 py-1 text-[11px] font-mono text-white/60">Ctrl K</kbd>
          </button>

          <div className="ml-auto flex items-center gap-2">
            <button onClick={() => setOpen(true)} aria-label="Search documentation" className="flex h-11 w-11 items-center justify-center text-white/75 transition-colors hover:text-white md:hidden">
              <Search size={18} strokeWidth={1.75} />
            </button>
            <a
              href={site.github}
              target="_blank"
              rel="noreferrer"
              aria-label="EveryCli on GitHub"
              className="flex h-11 w-11 items-center justify-center border-l border-white/10 text-white/75 transition-colors hover:text-white"
            >
              <Github size={19} strokeWidth={1.75} />
            </a>
          </div>
        </div>
      </header>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/65 px-4 pt-[12vh] backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Search documentation" onMouseDown={() => setOpen(false)}>
          <div className="w-full max-w-2xl border border-white/20 bg-[#0f0e0d] p-4 shadow-2xl" onMouseDown={(event) => event.stopPropagation()}>
            <div className="flex h-16 items-center gap-3 border border-white/15 bg-black/20 px-4">
              <Search size={20} className="text-white/70" />
              <input
                ref={inputRef}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search the EveryCli documentation"
                className="min-w-0 flex-1 bg-transparent text-base text-white outline-none placeholder:text-white/35"
              />
              <button type="button" onClick={() => setOpen(false)} aria-label="Close search" className="flex h-10 w-10 items-center justify-center text-white/60 transition-colors hover:text-white">
                <X size={21} />
              </button>
            </div>

            <div className="pt-4">
              <p className="px-1 text-[10px] font-mono uppercase tracking-[0.16em] text-white/40">
                {query ? `${results.length} result${results.length === 1 ? "" : "s"}` : "Documentation"}
              </p>
              <div className="mt-3 max-h-[45vh] overflow-y-auto border-t border-white/10">
                {results.length > 0 ? results.map((item) => (
                  <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className="flex items-center justify-between gap-5 border-b border-white/10 px-4 py-4 transition-colors hover:bg-white/[0.045]">
                    <span className="text-sm text-white/85">{item.title}</span>
                    <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.12em] text-white/35">{item.href === "/docs" ? "Overview" : "Docs"}</span>
                  </Link>
                )) : (
                  <p className="px-4 py-8 text-sm text-white/45">No documentation page matches “{query}”.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
