"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { docsNav } from "@/lib/site"

export function DocsSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname()

  return (
    <nav aria-label="Documentation" className="flex flex-col gap-8">
      {docsNav.map((section) => (
        <div key={section.label} className="flex flex-col gap-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-muted-foreground">
              {section.index}
            </span>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-foreground font-bold">
              {section.label}
            </span>
          </div>
          <ul className="flex flex-col border-l-2 border-border">
            {section.items.map((item) => {
              const active = pathname === item.href
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={`block -ml-0.5 border-l-2 pl-3 py-1.5 text-xs font-mono transition-colors duration-150 ${
                      active
                        ? "border-[#ea580c] text-foreground font-bold"
                        : "border-transparent text-muted-foreground hover:text-foreground hover:border-foreground/40"
                    }`}
                  >
                    {item.title}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
