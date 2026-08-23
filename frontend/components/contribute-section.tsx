"use client"

import Link from "next/link"
import { ArrowUpRight, BookOpen, Braces, Github, Plus } from "lucide-react"
import { motion, useReducedMotion } from "motion/react"
import { site } from "@/lib/site"

const indexedCollections = [
  "Bash",
  "Composer",
  "Docker",
  "Docker Compose",
  "Git",
  "Linux",
  "npm",
  "Python",
  "SSH",
]

export function ContributeSection() {
  const reduceMotion = useReducedMotion()

  return (
    <section id="contribute" className="border-t border-white/10 px-6 py-16 sm:py-20 lg:px-12 lg:py-24" aria-labelledby="contribute-title">
      <div className="mx-auto max-w-6xl overflow-hidden border border-white/10 bg-white/[0.015]">
        <div className="grid lg:grid-cols-[0.92fr_1.08fr]">
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, y: 14 }}
            whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.5 }}
            className="p-7 sm:p-10 lg:p-14"
          >
            <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#f05243]">// OPEN TO YOUR WORKFLOW</p>
            <h2 id="contribute-title" className="mt-5 max-w-lg font-pixel text-4xl leading-[1.05] tracking-tight text-white sm:text-5xl">Make EveryCli yours.</h2>
            <p className="mt-7 max-w-lg text-sm leading-7 text-white/55 sm:text-base">Fork it, run it locally, and adapt the command corpus to the work you do every day. Add the commands you want to keep in memory, then help make them useful for everyone else.</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link href="/docs" className="group inline-flex min-h-11 items-center gap-2 border border-[#f05243] bg-[#f05243] px-4 text-xs font-mono uppercase tracking-[0.13em] text-[#161314] transition-colors hover:bg-[#ff7566] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff7566] focus-visible:ring-offset-2 focus-visible:ring-offset-[#161314]">
                <BookOpen size={15} /> Read docs <ArrowUpRight size={14} className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </Link>
              <a href={site.github} target="_blank" rel="noreferrer" className="group inline-flex min-h-11 items-center gap-2 border border-white/15 px-4 text-xs font-mono uppercase tracking-[0.13em] text-white/75 transition-colors hover:border-white/40 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff7566] focus-visible:ring-offset-2 focus-visible:ring-offset-[#161314]">
                <Github size={15} /> GitHub <ArrowUpRight size={14} className="transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </a>
            </div>
          </motion.div>

          <motion.div
            initial={reduceMotion ? false : { opacity: 0, x: 16 }}
            whileInView={reduceMotion ? undefined : { opacity: 1, x: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.55, delay: 0.08 }}
            className="border-t border-white/10 bg-black/10 p-7 sm:p-10 lg:border-l lg:border-t-0 lg:p-14"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 text-[10px] font-mono uppercase tracking-[0.16em] text-white/45"><Braces size={15} className="text-[#f05243]" /> indexed command collections</div>
              <span className="border border-[#f05243]/20 bg-[#f05243]/[0.06] px-2.5 py-1 text-[9px] font-mono uppercase tracking-[0.12em] text-[#ff7566]">{indexedCollections.length} active</span>
            </div>
            <div className="mt-8 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {indexedCollections.map((collection, index) => (
                <div key={collection} className="flex min-h-12 items-center gap-2 border border-white/10 bg-white/[0.025] px-3 text-[11px] font-mono text-white/65">
                  <span className="text-[#f05243]/70">{String(index + 1).padStart(2, "0")}</span>{collection}
                </div>
              ))}
              <div className="flex min-h-12 items-center gap-2 border border-dashed border-[#f05243]/30 px-3 text-[11px] font-mono text-[#ff7566]/80"><Plus size={14} /> yours</div>
            </div>
            <div className="mt-8 border border-white/10 bg-[#161314] p-4 font-mono text-[11px] leading-6 text-white/45">
              <span className="text-[#f05243]">everycli/</span>data/<span className="text-white/75">commands/</span>
              <span className="mt-1 block text-white/30">Add or edit YAML command scenarios locally.</span>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
