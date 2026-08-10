"use client"

import { useState } from "react"
import { Check, Copy } from "lucide-react"

interface CodeBlockProps {
  code: string
  label?: string
  /** When true, prefixes each line with a shell prompt marker via styling */
  shell?: boolean
}

export function CodeBlock({ code, label = "bash", shell = false }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard not available
    }
  }

  const lines = code.split("\n")

  return (
    <div className="border-2 border-foreground bg-foreground">
      {/* Header */}
      <div className="flex items-center gap-2 border-b-2 border-background/20 px-4 py-2">
        <span className="h-2 w-2 bg-[#ea580c]" />
        <span className="h-2 w-2 bg-background" />
        <span className="h-2 w-2 border border-background" />
        <span className="ml-2 text-[10px] tracking-widest uppercase text-background/60">
          {label}
        </span>
        <button
          onClick={copy}
          className="ml-auto flex items-center gap-1.5 text-[10px] tracking-widest uppercase text-background/60 hover:text-background transition-colors"
          aria-label="Copy code"
        >
          {copied ? <Check size={12} strokeWidth={2} /> : <Copy size={12} strokeWidth={2} />}
          {copied ? "COPIED" : "COPY"}
        </button>
      </div>

      {/* Body */}
      <div className="overflow-x-auto p-4">
        <pre className="font-mono text-xs leading-relaxed text-background">
          {lines.map((line, i) => (
            <div key={i} className="flex">
              {shell && <span className="mr-2 select-none text-[#ea580c]">$</span>}
              <span className="whitespace-pre">{line || " "}</span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  )
}
