"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { motion } from "framer-motion"
import { CodeBlock } from "@/components/code-block"
import { site } from "@/lib/site"

const ease = [0.22, 1, 0.36, 1] as const

export function HeroSection() {
  return (
    <section className="relative w-full px-6 pt-10 pb-16 lg:px-24 lg:pt-16 lg:pb-24">
      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        {/* version tag */}
        <motion.span
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease }}
          className="mb-6 border border-foreground/30 px-3 py-1 text-[10px] font-mono tracking-[0.2em] uppercase text-muted-foreground"
        >
          {`v${site.version} // STABLE`}
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 30, filter: "blur(8px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.7, ease }}
          className="font-pixel text-4xl sm:text-6xl lg:text-7xl xl:text-8xl tracking-tight text-foreground select-none text-balance"
        >
          {site.tagline}
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.35, ease }}
          className="mt-6 max-w-xl text-xs lg:text-sm text-muted-foreground leading-relaxed font-mono text-pretty"
        >
          {site.description}
        </motion.p>

        {/* Demo command */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5, ease }}
          className="mt-10 w-full max-w-md text-left"
        >
          <CodeBlock code={site.demo} label="try it" shell />
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.65, ease }}
          className="mt-8 flex flex-col sm:flex-row items-center gap-4"
        >
          <Link
            href="/docs"
            className="group flex items-center gap-0 bg-foreground text-background text-sm font-mono tracking-wider uppercase"
          >
            <span className="flex items-center justify-center w-10 h-10 bg-[#ea580c]">
              <ArrowRight size={16} strokeWidth={2} className="text-background transition-transform group-hover:translate-x-1" />
            </span>
            <span className="px-5 py-2.5">Read the Docs</span>
          </Link>
          <Link
            href="/docs/quick-start"
            className="border-2 border-foreground px-5 py-2.5 text-sm font-mono tracking-wider uppercase text-foreground hover:bg-foreground hover:text-background transition-colors duration-200"
          >
            Quick Start
          </Link>
        </motion.div>
      </div>
    </section>
  )
}
