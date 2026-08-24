"use client"

import { motion } from "framer-motion"
import { CodeBlock } from "@/components/code-block"

const ease = [0.22, 1, 0.36, 1] as const

const STEPS = [
  {
    n: "01",
    title: "Install",
    desc: "Install a self-contained release in one command. No Rust, Python, or compiler required.",
    code: "curl -fsSL https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.sh | bash",
  },
  {
    n: "02",
    title: "Search",
    desc: "Describe the task in plain language. The hybrid local engine keeps the search inside your terminal.",
    code: 'everycli search "git: squash last 3 commits"',
  },
  {
    n: "03",
    title: "Extend",
    desc: "Save a command you use often to your personal corpus so EveryCli surfaces it in future searches.",
    code: "everycli add",
  },
]

export function CommandShowcase() {
  return (
    <section className="w-full px-6 py-20 lg:px-12">
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease }}
        className="flex items-center gap-4 mb-10"
      >
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
          {"// SECTION: WORKFLOW"}
        </span>
        <div className="flex-1 border-t border-border" />
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">002</span>
      </motion.div>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-3 lg:gap-8">
        {STEPS.map((s, i) => (
          <motion.div
            key={s.n}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ delay: i * 0.12, duration: 0.5, ease }}
            className="flex flex-col gap-4"
          >
            <div className="flex items-baseline gap-3">
              <span className="font-pixel text-2xl text-[#ea580c]">{s.n}</span>
              <h3 className="text-sm font-mono font-bold tracking-widest uppercase text-foreground">
                {s.title}
              </h3>
            </div>
            <p className="text-xs font-mono leading-relaxed text-muted-foreground min-h-[2.5rem]">
              {s.desc}
            </p>
            <CodeBlock code={s.code} label={`step_${s.n}`} shell />
          </motion.div>
        ))}
      </div>
    </section>
  )
}
