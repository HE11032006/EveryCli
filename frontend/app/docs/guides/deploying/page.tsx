import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList, DocNote } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function BuildFromSourcePage() {
  return (
    <DocPage
      eyebrow="002 // GUIDES"
      title="BUILD FROM SOURCE"
      description="Set up a development environment, compile the Rust binaries, and install EveryCli locally."
      href="/docs/guides/deploying"
    >
      <DocH2>Prerequisites</DocH2>
      <DocList
        items={[
          "Rust toolchain (stable, via rustup.rs).",
          "ONNX Runtime shared library — download the zip for your platform from the microsoft/onnxruntime GitHub releases and unzip it next to the binary (or set ONNXRUNTIME_LIB_PATH).",
          "Git.",
        ]}
      />

      <DocH2>Clone and build</DocH2>
      <CodeBlock
        code={
          "git clone https://github.com/HE11032006/EveryCli.git\ncd EveryCli\\rust\ncargo build --release"
        }
        label="powershell"
        shell
      />

      <DocH2>Install locally (Windows)</DocH2>
      <DocP>
        The installer script copies the compiled binaries, registers the daemon as a Windows
        service, and sets up the PowerShell wrapper automatically:
      </DocP>
      <CodeBlock code={".\\install.ps1"} label="powershell" shell />

      <DocH2>Uninstall</DocH2>
      <CodeBlock code={".\\uninstall.ps1"} label="powershell" shell />

      <DocNote>
        The old Python/PyInstaller daemon has been replaced by a 100% Rust daemon using ONNX
        Runtime. There is no PyInstaller build step anymore.
      </DocNote>
    </DocPage>
  )
}
