import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList, DocCode } from "@/components/docs/doc-content"

export default function HowItWorksPage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="HOW IT WORKS" description="EveryCli combines local lexical and semantic retrieval, served by a Rust daemon that keeps the model ready in memory." href="/docs/guides/project-structure">
      <DocH2>The local daemon</DocH2>
      <DocP>Loading the semantic model for every request would add unnecessary startup time and CPU work. EveryCli keeps it loaded in a local background daemon (a native Rust binary, installed as a Windows service or a <DocCode>systemd --user</DocCode> service on Linux) and communicates through a local TCP socket.</DocP>
      <DocList items={["The daemon keeps the ONNX Runtime session and model loaded in memory.", "The client sends the query and displays the result.", "Measured warm-search latency: single-digit milliseconds of inference, ~130-210ms end-to-end from the client."]} />

      <DocH2>Hybrid retrieval</DocH2>
      <DocP>EveryCli combines three signals, not a single search strategy. Lexical matching is fast and precise for exact terms such as <DocCode>git</DocCode>; semantic matching (via ONNX Runtime) understands intent even when the wording differs entirely from the stored command description.</DocP>
      <DocList items={["A custom lexical scorer handles exact keyword overlap.", "A multilingual MiniLM model (fine-tuned on the EveryCli corpus, run locally via ONNX Runtime) contributes semantic similarity.", "A namespace hint (e.g. the word \u201cdocker\u201d in the query) adds a bonus to matching results -- it is never a hard filter, so a personal command added via `everycli add` in a different namespace stays reachable."]} />

      <DocH2>Local command corpus</DocH2>
      <DocP>Command scenarios live in YAML files under <DocCode>everycli/data/commands/</DocCode>. Each scenario carries descriptions, tags, per-platform command variants, explanations, and optional warnings.</DocP>
    </DocPage>
  )
}
