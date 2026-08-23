"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"

type Heading = { id: string; label: string }

export function DocsTableOfContents() {
  const pathname = usePathname()
  const [headings, setHeadings] = useState<Heading[]>([])

  useEffect(() => {
    const updateHeadings = () => {
      const found = Array.from(document.querySelectorAll<HTMLElement>("[data-doc-content] h2[id]"))
        .map((heading) => ({ id: heading.id, label: heading.textContent?.trim() ?? "" }))
        .filter((heading) => heading.label)
      setHeadings(found)
    }

    const frame = window.requestAnimationFrame(updateHeadings)
    return () => window.cancelAnimationFrame(frame)
  }, [pathname])

  if (headings.length === 0) return null

  return (
    <aside className="hidden w-56 shrink-0 border-l border-white/10 px-6 py-9 xl:block">
      <div className="sticky top-24">
        <p className="text-sm font-semibold text-white">On this page</p>
        <nav className="mt-4 flex flex-col gap-3" aria-label="On this page">
          {headings.map((heading) => (
            <a key={heading.id} href={`#${heading.id}`} className="text-xs text-white/45 transition-colors hover:text-[#ff7566]">
              {heading.label}
            </a>
          ))}
        </nav>
      </div>
    </aside>
  )
}
