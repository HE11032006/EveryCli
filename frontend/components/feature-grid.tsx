"use client"

import { Zap, Package, GitBranch, Terminal, ShieldCheck, Layers } from "lucide-react"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const FEATURES = [
  {
    icon: Zap,
    title: "Zero Config",
    body: "Run forge init and start immediately. Sensible defaults, overridable when you need them.",
  },
  {
    icon: Package,
    title: "Deterministic Builds",
    body: "Content-hashed artifacts. The same input always produces the exact same output.",
  },
  {
    icon: GitBranch,
    title: "Any Target",
    body: "Ship to edge, containers, or static hosts with a single deploy adapter interface.",
  },
  {
    icon: Terminal,
    title: "Scriptable",
    body: "Every command is composable and returns structured JSON for CI pipelines.",
  },
  {
    icon: ShieldCheck,
    title: "Signed Releases",
    body: "Provenance-attested builds with SLSA-compatible signatures out of the box.",
  },
  {
    icon: Layers,
    title: "Plugin System",
    body: "Extend the pipeline with typed hooks. Publish and share plugins via the registry.",
  },
]

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.5, ease },
  }),
}

export function FeatureGrid() {
  return (
    <section className="w-full px-6 py-20 lg:px-12">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease }}
        className="flex items-center gap-4 mb-8"
      >
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
          {"// SECTION: CAPABILITIES"}
        </span>
        <div className="flex-1 border-t border-border" />
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">001</span>
      </motion.div>

      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 border-t-2 border-l-2 border-foreground"
      >
        {FEATURES.map((f, i) => {
          const Icon = f.icon
          return (
            <motion.div
              key={f.title}
              custom={i}
              variants={cardVariants}
              className="border-r-2 border-b-2 border-foreground p-6 lg:p-8"
            >
              <Icon size={20} strokeWidth={1.5} className="mb-4 text-[#ea580c]" />
              <h3 className="text-sm font-mono font-bold tracking-widest uppercase text-foreground mb-2">
                {f.title}
              </h3>
              <p className="text-xs font-mono leading-relaxed text-muted-foreground">
                {f.body}
              </p>
            </motion.div>
          )
        })}
      </motion.div>
    </section>
  )
}
