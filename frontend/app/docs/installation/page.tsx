import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function InstallationPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="INSTALLATION"
      description="FORGE ships as a single self-contained binary. Pick the method that fits your environment."
      href="/docs/installation"
    >
      <DocH2>Requirements</DocH2>
      <DocP>
        FORGE runs on Linux, macOS, and Windows (x64 and arm64). No runtime is required — the binary
        is fully static. For the npm install method you need Node.js 18 or newer.
      </DocP>

      <DocH2>npm (recommended)</DocH2>
      <CodeBlock code={"npm install -g @forge/cli"} label="npm" shell />

      <DocH2>Homebrew (macOS / Linux)</DocH2>
      <CodeBlock code={"brew install forge-cli/tap/forge"} label="brew" shell />

      <DocH2>Install script</DocH2>
      <CodeBlock code={"curl -fsSL https://forge.dev/install.sh | sh"} label="curl" shell />

      <DocH2>Verify</DocH2>
      <DocP>
        Confirm the install by printing the version. You should see the version string and build
        hash.
      </DocP>
      <CodeBlock code={"forge --version\n# forge 1.4.0 (build a1b2c3d)"} label="bash" shell />

      <DocNote>
        Upgrading later is a single command: <DocCode>forge upgrade</DocCode>. It replaces the
        binary in place and preserves your global config.
      </DocNote>
    </DocPage>
  )
}
