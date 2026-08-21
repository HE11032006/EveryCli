import { DocPage } from "@/components/docs/doc-page"
import { DocCode } from "@/components/docs/doc-content"

const FAQ = [
  {
    q: "The daemon does not respond",
    a: "The daemon runs as a Windows service. Check its status with `sc.exe query EveryCliDaemon`. If it is not running, start it with `sc.exe start EveryCliDaemon`, or run a search with `--no-daemon` to force direct local retrieval.",
  },
  {
    q: "Can I work without a connection?",
    a: "Yes. EveryCli is local-first. The semantic model runs entirely on your machine; lexical retrieval is always available as a fallback when the daemon is not running.",
  },
  {
    q: "Does Sentinel execute the command it suggests?",
    a: "No. `everycli plan` only returns a command, risk level, and checks. It never runs a shell command.",
  },
  {
    q: "How do I add a command to the corpus?",
    a: "Run `everycli add` for the interactive flow. Your entry is saved to `~/.everycli/commands/<namespace>.yaml` and merged with the built-in corpus at search time.",
  },
  {
    q: "How do I list or remove my custom commands?",
    a: "Use `everycli list` to see all personal corpus entries and `everycli remove <id>` to delete one (the tool prompts for confirmation).",
  },
  {
    q: "How do I use the PowerShell helper?",
    a: "Source `everycli.ps1` in your session, then use `evc`. The result goes into PSReadLine's editable command buffer; it is not executed automatically.",
  },
  {
    q: "How do I install or uninstall the daemon service?",
    a: "Run `.\\install.ps1` to register the daemon as a Windows service (UAC elevation is handled automatically). Run `.\\uninstall.ps1` to remove it.",
  },
]

export default function FaqPage() {
  return (
    <DocPage
      eyebrow="005 // HELP"
      title="FAQ & TROUBLESHOOTING"
      description="Answers based on the current EveryCli workflow."
      href="/docs/faq"
    >
      <div className="flex flex-col border-t border-white/15">
        {FAQ.map((item, index) => (
          <details key={item.q} className="group border-b border-white/15 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer items-center justify-between gap-4 py-4 text-sm font-mono font-bold uppercase tracking-wide text-foreground">
              <span className="flex items-start gap-3 text-pretty">
                <span className="select-none text-[#f05243]">{String(index + 1).padStart(2, "0")}</span>
                {item.q}
              </span>
              <span className="select-none text-lg leading-none text-[#f05243] transition-transform group-open:rotate-45">+</span>
            </summary>
            <p className="pb-5 pl-9 text-sm font-mono leading-relaxed text-muted-foreground text-pretty">{item.a}</p>
          </details>
        ))}
      </div>
      <p className="mt-8 text-xs font-mono leading-relaxed text-muted-foreground">
        Still blocked? Open an issue on GitHub with the output of{" "}
        <DocCode>sc.exe query EveryCliDaemon</DocCode> and the command you were trying to run.
      </p>
    </DocPage>
  )
}
