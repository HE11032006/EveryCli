import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function InstallationPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="INSTALLATION"
      description="EveryCli ships as a native Rust binary with a background daemon. Use the provided scripts to install the Windows service or the Linux/macOS background process."
      href="/docs/installation"
    >
      <DocH2>Windows — service installation</DocH2>
      <DocP>
        Clone the repository, then run the installer script. It builds the Rust binaries, registers
        the daemon as a Windows service (with UAC auto-elevation), and places{" "}
        <DocCode>everycli.exe</DocCode> on your PATH.
      </DocP>
      <CodeBlock
        code={"git clone https://github.com/HE11032006/EveryCli.git\ncd EveryCli\n.\\install.ps1"}
        label="powershell"
        shell
      />
      <DocP>
        Pass <DocCode>-NoService</DocCode> to fall back to the Windows Startup folder instead of
        a system service if you prefer not to elevate.
      </DocP>

      <DocH2>Linux / macOS — from source</DocH2>
      <CodeBlock
        code={"git clone https://github.com/HE11032006/EveryCli.git\ncd EveryCli\nbash install.sh"}
        label="bash"
        shell
      />

      <DocH2>Requirements</DocH2>
      <DocP>
        The installer handles everything. If you build from source manually, you need{" "}
        <DocCode>cargo</DocCode> (Rust toolchain) and the ONNX Runtime library (
        <DocCode>onnxruntime.dll</DocCode> on Windows, <DocCode>libonnxruntime.so</DocCode> on
        Linux). See the repository README for exact paths.
      </DocP>

      <DocH2>Verify the installation</DocH2>
      <DocP>Once the daemon is running, run a search to confirm everything works:</DocP>
      <CodeBlock code={'everycli search "undo my last commit"'} label="bash" shell />

      <DocNote>
        A public package-manager release is not yet available. Install from source using the
        scripts above.
      </DocNote>
    </DocPage>
  )
}
