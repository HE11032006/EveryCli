"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import { site } from "@/lib/site"

const NAV_LINKS = [
  { label: "Why", href: "/#why" },
  { label: "Features", href: "/#features" },
  { label: "Contribute", href: "/#contribute" },
  { label: "Docs", href: "/docs" },
]

export function Navbar() {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-40 w-full border-b border-white/10 bg-[#0a0908]/90 backdrop-blur-md"
    >
      <nav className="mx-auto w-full max-w-[90rem] px-5 py-3 sm:px-6 lg:px-10">
        <div className="flex min-h-11 items-center justify-between">
          <Link href="/" className="text-xl font-semibold tracking-tight text-white transition-colors hover:text-white/80">
            {site.name}
          </Link>

          <div className="hidden lg:flex items-center gap-7">
            {NAV_LINKS.map((link, i) => (
              <motion.div
                key={link.label}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.06, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                <Link
                  href={link.href}
                  className="relative py-5 text-xs font-mono tracking-widest uppercase text-muted-foreground transition-colors duration-200 hover:text-white after:absolute after:bottom-2 after:left-0 after:h-px after:w-full after:origin-left after:scale-x-0 after:bg-white after:transition-transform after:duration-200 hover:after:scale-x-100"
                >
                  {link.label}
                </Link>
              </motion.div>
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="flex items-center gap-4"
          >
            <a
              href={site.github}
              target="_blank"
              rel="noreferrer"
              className="hidden sm:block text-xs font-mono tracking-widest uppercase text-muted-foreground hover:text-foreground transition-colors duration-200"
            >
              GitHub
            </a>
          </motion.div>
        </div>
      </nav>
    </motion.header>
  )
}
