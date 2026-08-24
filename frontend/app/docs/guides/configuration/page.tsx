import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ShellIntegrationPage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="SHELL INTEGRATION" description="Bring a reviewed EveryCli result into your shell's editable command buffer without automatic execution." href="/docs/guides/configuration">
      <DocH2>Safe shell mode</DocH2>
      <DocP><DocCode>--shell</DocCode> sends only the raw resolved command to standard output, with no trailing newline -- everything else (namespace/id, command, explanation, score) goes to <DocCode>stderr</DocCode>. There is no confirmation prompt in <DocCode>--shell</DocCode> mode itself; a wrapper script decides whether to ask before running it. It cannot be combined with interactive selection, copy, run, error diagnosis, or a result count other than one.</DocP>

<DocH2>Editable, never automatic</DocH2>
      <DocP>A shell integration may place the selected result into an editable command buffer, but it must never execute the command automatically. Review the command and decide yourself whether to press Enter.</DocP>
      <DocNote>Custom integrations can set <DocCode>EVERYCLI_BIN</DocCode> to the full path of the installed executable. The repository does not guarantee an official shell wrapper until each supported shell path has been tested end to end.</DocNote>
    </DocPage>
  )
}
