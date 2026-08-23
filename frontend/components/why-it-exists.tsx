"use client"

import { motion, useReducedMotion } from "motion/react"

const problems = [
  {
    number: "001",
    label: "COMMAND RECALL",
    title: "The syntax slips away.",
    body: "The commands you need most are often the ones you use least. Flags, order, and exact syntax disappear when the task cannot wait.",
  },
  {
    number: "002",
    label: "CONTEXT SWITCHING",
    title: "Search breaks your flow.",
    body: "Terminal, browser, online chat, terminal again. Finding one command should not pull you out of the work you are already doing.",
  },
  {
    number: "003",
    label: "CONNECTION DEPENDENCY",
    title: "Help should not need a signal.",
    body: "When your answer lives online, latency and connectivity get to decide whether you can keep moving. Local work deserves local answers.",
  },
  {
    number: "004",
    label: "EXECUTION DOUBT",
    title: "A command needs context.",
    body: "Before Enter, you still need to know what changes, what could break, and whether the command matches the intent you had in mind.",
  },
]

function ProblemStatement() {
  return (
    <div className="flex min-h-[310px] flex-col justify-between overflow-hidden p-8 sm:min-h-[390px]" aria-label="EveryCli problem statement">
      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#f05243]">The friction</span>
      <p className="max-w-sm font-pixel text-3xl leading-[1.04] tracking-tight text-white sm:text-4xl">Command line work is powerful. Remembering everything is not.</p>
      <p className="max-w-xs border-l border-[#f05243]/40 pl-4 text-sm leading-6 text-white/50">EveryCli keeps useful command knowledge close, searchable, and ready when the syntax is not.</p>
    </div>
  )
}

export function WhyItExists() {
  const reduceMotion = useReducedMotion()

  return (
    <section id="why" className="border-t border-white/10 px-6 py-16 sm:py-20 lg:px-12 lg:py-24" aria-labelledby="why-title">
      <div className="mx-auto max-w-7xl border-x border-white/10">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 16 }}
          whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.35 }}
          transition={{ duration: 0.55 }}
          className="border-y border-white/10 px-7 py-16 sm:px-12 sm:py-20 lg:px-16 lg:py-24"
        >
          <div className="mx-auto w-fit border border-[#f05243]/40 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[#f05243]">× Why EveryCli?</div>
          <h2 id="why-title" className="mt-8 max-w-6xl font-pixel text-5xl leading-[0.96] tracking-tight text-white sm:text-6xl lg:text-[5.1rem]">The terminal should not make you stop.</h2>
        </motion.div>

        <div className="grid border-b border-white/10 lg:grid-cols-[minmax(290px,0.82fr)_minmax(0,1.18fr)]">
          <div className="border-b border-white/10 lg:border-b-0 lg:border-r">
            <ProblemStatement />
          </div>
          <div className="grid sm:grid-cols-2">
            {problems.map((problem, index) => (
              <motion.article
                key={problem.number}
                initial={reduceMotion ? false : { opacity: 0, y: 14 }}
                whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.45, delay: index * 0.06 }}
                className={`relative min-h-[235px] px-7 py-9 sm:px-10 sm:py-10 ${index % 2 === 0 ? "sm:border-r sm:border-white/10" : ""} ${index < 2 ? "border-b border-white/10" : ""}`}
              >
                <span className="absolute right-7 top-9 font-mono text-[10px] tracking-[0.15em] text-white/25 sm:right-10 sm:top-10">{problem.number}</span>
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#f05243]">{problem.label}</p>
                <h3 className="mt-4 max-w-xs text-2xl font-medium leading-tight text-white sm:text-[1.7rem]">{problem.title}</h3>
                <p className="mt-4 max-w-sm text-sm leading-6 text-white/55">{problem.body}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
