"use client"

import { BrainCircuit, GitBranch, Languages, Search, ShieldCheck, WifiOff } from "lucide-react"
import { motion, useReducedMotion } from "motion/react"
import { FeatureCard, type GridFeature } from "@/components/ui/grid-feature-cards"

const FEATURES: GridFeature[] = [
  {
    title: "Natural language search",
    icon: Search,
    description: "Describe the task in your own words. EveryCli finds the command that matches what you actually want to do.",
    pattern: [[7, 1], [9, 3], [10, 5], [8, 6]],
  },
  {
    title: "Hybrid local search",
    icon: BrainCircuit,
    description: "Semantic and lexical search work together to retrieve useful command candidates from a local corpus.",
    pattern: [[8, 1], [10, 2], [7, 4], [9, 6]],
  },
  {
    title: "Offline ready",
    icon: WifiOff,
    description: "Keep working without a connection: EveryCli can use a local semantic model or fall back to local lexical search.",
    pattern: [[10, 1], [7, 3], [8, 5], [10, 6]],
  },
  {
    title: "Built for your tools",
    icon: Languages,
    description: "Search across Git, Docker, Compose, npm, Composer, SSH, Python, Linux, and more from one CLI.",
    pattern: [[9, 1], [7, 2], [10, 4], [8, 6]],
  },
  {
    title: "Review before running",
    icon: ShieldCheck,
    description: "Sentinel helps you inspect and understand multi-step actions before you execute a command.",
    pattern: [[7, 1], [8, 3], [10, 4], [9, 6]],
  },
  {
    title: "Native terminal speed",
    icon: GitBranch,
    description: "A native Rust client gives fast local command discovery without pulling you away from the terminal.",
    pattern: [[10, 1], [9, 3], [7, 5], [8, 6]],
  },
]

export function FeatureGrid() {
  const reduceMotion = useReducedMotion()

  return (
    <section id="features" className="border-t border-white/10 px-6 py-16 sm:py-20 lg:px-12 lg:py-24" aria-labelledby="features-title">
      <div className="mx-auto max-w-6xl">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.45 }}
          transition={{ duration: 0.5 }}
          className="mx-auto mb-12 max-w-2xl text-center sm:mb-16"
        >
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#f05243]">// FEATURES</p>
          <h2 id="features-title" className="mt-5 font-pixel text-4xl leading-[1.05] tracking-tight text-white sm:text-6xl">Built for the way you already work.</h2>
          <p className="mt-6 text-sm leading-7 text-white/50 sm:text-base">EveryCli keeps command discovery fast, local, and close to the terminal.</p>
        </motion.div>
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 14 }}
          whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.15 }}
          transition={{ duration: 0.55, delay: 0.12 }}
          className="grid grid-cols-1 divide-y divide-dashed divide-white/15 border border-dashed border-white/15 sm:grid-cols-2 sm:divide-x sm:divide-y-0 lg:grid-cols-3"
        >
          {FEATURES.map((feature, index) => (
            <FeatureCard key={feature.title} feature={feature} className={index >= 3 ? "border-t border-dashed border-white/15 sm:border-t-0 lg:border-t" : ""} />
          ))}
        </motion.div>
      </div>
    </section>
  )
}
