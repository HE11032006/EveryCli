import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"

export default function ConfigReferencePage() {
  return (
    <DocPage
      eyebrow="003 // REFERENCE"
      title="ENVIRONMENT CONFIGURATION"
      description="Configuration available through environment variables and the local YAML command corpus."
      href="/docs/reference/config"
    >
      <DocH2>Environment variables</DocH2>
      <DocTable
        head={["Variable", "Purpose", "Default"]}
        rows={[
          [<DocCode key="port">EVERYCLI_PORT</DocCode>, "Port used for local client-to-daemon TCP communication.", "51821"],
          [<DocCode key="data">EVERYCLI_DATA_DIR</DocCode>, "Directory containing the built-in YAML corpus.", "../everycli/data/commands (relative to the daemon's launch directory)"],
          [<DocCode key="userdata">EVERYCLI_USER_DATA_DIR</DocCode>, "Directory containing your personal commands (everycli add).", "~/.everycli/commands"],
          [<DocCode key="model">EVERYCLI_MODEL_DIR</DocCode>, "Directory containing model.onnx and tokenizer.json.", "onnx-bench/models/everycli-minilm-ft"],
          [<DocCode key="dylib">EVERYCLI_ONNXRUNTIME_DYLIB</DocCode>, "Path to the ONNX Runtime shared library.", "onnx-bench/runtime/onnxruntime.dll (or .so)"],
          [<DocCode key="bin">EVERYCLI_BIN</DocCode>, "Full path to the everycli executable used by the PowerShell wrapper.", "Not set"],
        ]}
      />

      <DocH2>Command scenario format</DocH2>
      <DocP>
        Scenarios are stored in <DocCode>everycli/data/commands/*.yaml</DocCode>. Their fields
        describe the intent, command variants, explanation, and optional safety warning. The
        filename (without extension) is the <em>namespace</em> for all scenarios it contains.
      </DocP>
      <pre className="overflow-x-auto border border-white/15 bg-black/20 p-4 text-xs leading-6 text-white/70">{`- id: unique_id\n  description: Natural-language task\n  tags: [git, history]\n  commands:\n    linux: "git ..."\n    windows: "git ..."\n    macos: "git ..."\n  explanation: What the command does\n  warning: Optional safety note`}</pre>

      <DocH2>Local user corpus</DocH2>
      <DocP>
        Commands added with <DocCode>everycli add</DocCode> are written to{" "}
        <DocCode>~/.everycli/commands/&lt;namespace&gt;.yaml</DocCode>. They are merged with the
        built-in corpus at search time.
      </DocP>

      <DocH2>Daemon communication</DocH2>
      <DocP>
        The daemon listens only on <DocCode>127.0.0.1:{"{EVERYCLI_PORT}"}</DocCode>. It accepts
        JSON messages line-by-line (actions: <DocCode>search</DocCode>,{" "}
        <DocCode>ping</DocCode>, <DocCode>reload</DocCode>).
      </DocP>
    </DocPage>
  )
}
