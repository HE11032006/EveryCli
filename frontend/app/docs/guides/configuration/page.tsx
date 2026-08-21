import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ShellIntegrationPage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="SHELL INTEGRATION" description="Bring a reviewed EveryCli result into your shell's editable command buffer without automatic execution." href="/docs/guides/configuration">
      <DocH2>Safe shell mode</DocH2>
      <DocP><DocCode>--shell</DocCode> sends only the raw resolved command to standard output, with no trailing newline -- everything else (namespace/id, command, explanation, score) goes to <DocCode>stderr</DocCode>. There is no confirmation prompt in <DocCode>--shell</DocCode> mode itself; a wrapper script decides whether to ask before running it. It cannot be combined with interactive selection, copy, run, error diagnosis, or a result count other than one.</DocP>

      <DocH2>PowerShell</DocH2>
      <DocP>During local development, load the PowerShell integration once in the terminal:</DocP>
      <CodeBlock code={". D:\\EveryCli\\everycli.ps1\nevc \"annuler mon dernier commit sans perdre mes changements\""} label="powershell" shell />

      <DocH2>Editable, never automatic</DocH2>
      <DocP>The <DocCode>evc</DocCode> helper asks PSReadLine to place the selected result into the editable command buffer. You can change it, or choose whether to press Enter yourself.</DocP>
      <DocNote>For a packaged executable, set <DocCode>EVERYCLI_BIN</DocCode> to its full path before loading the wrapper.</DocNote>
    </DocPage>
  )
}
