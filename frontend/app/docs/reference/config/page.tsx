import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"

export default function ConfigReferencePage() {
  return (
    <DocPage eyebrow="003 // REFERENCE" title="ENVIRONMENT CONFIGURATION" description="Configuration available through environment variables and the local YAML command corpus." href="/docs/reference/config">
      <DocH2>Environment variables</DocH2>
      <DocTable head={["Variable", "Purpose", "Default"]} rows={[
        [<DocCode key="port">EVERYCLI_PORT</DocCode>, "Port used for local client-to-daemon communication.", "51821"],
        [<DocCode key="level">EVERYCLI_LOG_LEVEL</DocCode>, "Daemon log verbosity.", "INFO"],
        [<DocCode key="bin">EVERYCLI_BIN</DocCode>, "Full executable path used by the PowerShell wrapper.", "Not set"],
      ]} />

      <DocH2>Command scenario format</DocH2>
      <DocP>Scenarios are stored in <DocCode>everycli/data/commands/*.yaml</DocCode>. Their fields describe the intent, command variants, explanation, and optional safety warning.</DocP>
      <pre className="overflow-x-auto border border-white/15 bg-black/20 p-4 text-xs leading-6 text-white/70">{`- id: unique_id\n  description: Natural-language task\n  tags: [git, history]\n  commands:\n    linux: "git ..."\n    windows: "git ..."\n  explanation: What the command does\n  warning: Optional safety note`}</pre>

      <DocH2>Daemon data</DocH2>
      <DocP>The daemon listens only on <DocCode>127.0.0.1</DocCode>. Its PID is stored at <DocCode>~/.everycli/daemon.pid</DocCode>.</DocP>
    </DocPage>
  )
}
