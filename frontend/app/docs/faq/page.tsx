import { DocPage } from "@/components/docs/doc-page"
import { DocCode } from "@/components/docs/doc-content"

const FAQ = [
  { q: "The daemon does not respond", a: "Check its current state with `everycli daemon --status`. Start it with `everycli daemon --start`, or run a search with `--no-daemon` to force direct local retrieval." },
  { q: "Can I work without a connection?", a: "Yes. EveryCli is local-first. The semantic model is used when it is available locally, and lexical retrieval remains available as a fallback." },
  { q: "Does Sentinel execute the command it suggests?", a: "No. `everycli plan` only returns a command, risk level, and checks. It never runs a shell command." },
  { q: "How do I add a command to the corpus?", a: "Run `everycli add` for the interactive flow, or edit a YAML scenario in `everycli/data/commands/`. The daemon is notified when the corpus is updated." },
  { q: "How do I use the PowerShell helper?", a: "Source `everycli.ps1` in your session, then use `evc`. The result goes into PSReadLine's editable command buffer; it is not executed automatically." },
]

export default function FaqPage() {
  return (
    <DocPage eyebrow="005 // HELP" title="FAQ & TROUBLESHOOTING" description="Answers based on the current local-first EveryCli workflow." href="/docs/faq">
      <div className="flex flex-col border-t border-white/15">
        {FAQ.map((item, index) => (
          <details key={item.q} className="group border-b border-white/15 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer items-center justify-between gap-4 py-4 text-sm font-mono font-bold uppercase tracking-wide text-foreground">
              <span className="flex items-start gap-3 text-pretty"><span className="select-none text-[#f05243]">{String(index + 1).padStart(2, "0")}</span>{item.q}</span>
              <span className="select-none text-lg leading-none text-[#f05243] transition-transform group-open:rotate-45">+</span>
            </summary>
            <p className="pb-5 pl-9 text-sm font-mono leading-relaxed text-muted-foreground text-pretty">{item.a}</p>
          </details>
        ))}
      </div>
      <p className="mt-8 text-xs font-mono leading-relaxed text-muted-foreground">Still blocked? Open an issue on GitHub with the output of <DocCode>everycli daemon --status</DocCode> and the command you were trying to run.</p>
    </DocPage>
  )
}
