"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowUpRight, Check, Copy } from "lucide-react"
import { motion } from "framer-motion"
import { Terminal } from "@/components/ui/terminal"
import { site } from "@/lib/site"

const installMethods = [
  { label: "Python", command: 'python -m everycli.everycli search "undo my last commit"' },
  { label: "Source", command: "git clone https://github.com/HE11032006/EveryCli.git" },
  { label: "Try it", command: 'everycli search "undo my last commit"' },
]

const terminalCommands = [
  'everycli search "undo my last commit"',
  'everycli search "remove unused Docker images"',
  'everycli plan "remove unused Docker images safely"',
  "everycli daemon --status",
]

const terminalOutputs = {
  0: ["-> intent: undo last commit", "git reset --soft HEAD~1", "OK changes preserved in working tree"],
  1: ["-> intent: remove unused Docker images", "docker image prune -a", "OK reclaimed 1.84 GB"],
  2: ["-> Sentinel review", "command: docker image prune -a", "risk: medium - review before executing", "OK no command will be run"],
  3: ["daemon: running", "mode: local hybrid search", "warm response target: <50ms"],
}

export function HeroSection() {
  const [activeMethod, setActiveMethod] = useState(0)
  const [copied, setCopied] = useState(false)
  const method = installMethods[activeMethod]

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(method.command)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  return (
    <section className="relative overflow-hidden px-6 pb-16 pt-9 sm:pb-20 sm:pt-12 lg:px-12 lg:pb-20 lg:pt-14">
      <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-12 lg:grid-cols-[minmax(0,0.92fr)_minmax(460px,1.08fr)] lg:gap-14">
        <div className="max-w-2xl">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} className="mb-7 flex items-center gap-3 text-[10px] font-mono uppercase tracking-[0.24em] text-[#f05243]">
            <span className="h-px w-8 bg-[#f05243]/70" />
            Natural language for your terminal
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.65, delay: 0.08 }} className="max-w-3xl font-pixel text-5xl leading-[0.98] tracking-tight text-white sm:text-7xl lg:text-[5.7rem]">
            Describe the task.
            <span className="block text-white/45">Get the command.</span>
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.24 }} className="mt-7 max-w-xl text-sm leading-7 text-white/60 sm:text-base">
            {site.description} EveryCli turns intent into a command you can understand, review, and run.
          </motion.p>
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.34 }} className="mt-9 max-w-xl">
            <div className="flex gap-1 border-b border-white/10" role="tablist" aria-label="Installation methods">
              {installMethods.map((item, index) => (
                <button key={item.label} type="button" role="tab" aria-selected={activeMethod === index} onClick={() => { setActiveMethod(index); setCopied(false) }} className={`min-h-11 px-3 text-[11px] font-mono uppercase tracking-[0.14em] transition-colors sm:px-4 ${activeMethod === index ? "border-b border-[#f05243] text-[#ff7566]" : "text-white/40 hover:text-white/75"}`}>
                  {item.label}
                </button>
              ))}
            </div>
            <div className="mt-4 flex min-h-14 items-center justify-between gap-4 border border-white/10 bg-black/30 px-4 py-3">
              <code className="min-w-0 overflow-x-auto whitespace-nowrap text-[11px] leading-5 text-white/75 sm:text-xs"><span className="mr-2 text-[#f05243]">$</span>{method.command}</code>
              <button type="button" onClick={copyCommand} aria-label={copied ? "Command copied" : "Copy command"} className="flex h-10 w-10 shrink-0 items-center justify-center border border-white/10 text-white/50 transition-colors hover:border-[#f05243]/60 hover:text-[#ff7566] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f05243]">
                {copied ? <Check size={15} /> : <Copy size={15} />}
              </button>
            </div>
            <p className="mt-3 text-[10px] font-mono uppercase tracking-[0.12em] text-white/30">Installation details live in the docs - public package coming soon</p>
          </motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.48 }} className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs font-mono uppercase tracking-[0.15em]">
            <Link href="/docs" className="group flex min-h-11 items-center gap-2 text-white transition-colors hover:text-[#ff7566]">Read the docs <ArrowUpRight size={14} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" /></Link>
            <span className="text-white/20">{`v${site.version}`}</span>
          </motion.div>
        </div>
        <motion.div initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.7, delay: 0.18 }} className="relative">
          <div className="relative border border-white/10 bg-[#171314]/90 p-2 sm:p-3">
            <Terminal commands={terminalCommands} outputs={terminalOutputs} username="everycli" typingSpeed={38} delayBetweenCommands={900} initialDelay={700} enableSound={false} className="max-w-none px-0 text-[11px] sm:text-xs" />
          </div>
          <p className="mt-4 text-right text-[10px] font-mono uppercase tracking-[0.16em] text-white/25">local command discovery</p>
        </motion.div>
      </div>
    </section>
  )
}
