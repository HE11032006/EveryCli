"use client"

import { useState } from "react"
import { Menu, X } from "lucide-react"
import { AnimatePresence, motion } from "framer-motion"
import { DocsSidebar } from "@/components/docs/docs-sidebar"
import { DocsTableOfContents } from "@/components/docs/docs-table-of-contents"

export function DocsShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mx-auto flex w-full max-w-[90rem]">
      {/* Desktop sidebar */}
      <aside className="hidden lg:block w-72 shrink-0 border-r border-white/10 px-6 py-9 xl:w-80 xl:px-8">
        <div className="sticky top-24">
          <DocsSidebar />
        </div>
      </aside>

      {/* Mobile toggle */}
      <div className="lg:hidden fixed bottom-4 right-4 z-40">
        <button
          onClick={() => setOpen(true)}
          className="flex min-h-11 items-center gap-2 border border-white/20 bg-[#0a0908] px-4 py-2.5 text-xs font-mono tracking-widest uppercase"
          aria-label="Open documentation menu"
        >
          <Menu size={14} strokeWidth={2} />
          Menu
        </button>
      </div>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="lg:hidden fixed inset-0 z-40 bg-foreground/40 backdrop-blur-sm"
            />
            <motion.div
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "tween", duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              className="lg:hidden fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] overflow-y-auto border-r border-white/15 bg-[#0a0908] p-6"
            >
              <div className="mb-6 flex items-center justify-between">
                <span className="text-[10px] font-mono tracking-[0.2em] uppercase font-bold">
                  DOCS.INDEX
                </span>
                <button onClick={() => setOpen(false)} aria-label="Close menu">
                  <X size={16} strokeWidth={2} />
                </button>
              </div>
              <DocsSidebar onNavigate={() => setOpen(false)} />
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Content */}
      <div className="min-w-0 flex-1 px-6 py-10 sm:px-10 lg:px-14 lg:py-12">{children}</div>

      <DocsTableOfContents />
    </div>
  )
}
