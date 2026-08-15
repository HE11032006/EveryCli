import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList, DocCode } from "@/components/docs/doc-content"

export default function HowItWorksPage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="HOW IT WORKS" description="EveryCli combines local lexical and semantic retrieval with a daemon that keeps the model ready." href="/docs/guides/project-structure">
      <DocH2>The local daemon</DocH2>
      <DocP>Loading the semantic model for every request would add unnecessary startup time and CPU work. EveryCli keeps it in a local background daemon and communicates through a local socket.</DocP>
      <DocList items={["The daemon keeps the model loaded in memory.", "The client sends the query and displays the result.", "Warm searches target a response in under 50 ms."]} />

      <DocH2>Hybrid retrieval</DocH2>
      <DocP>EveryCli uses two complementary retrieval strategies. Lexical matching is fast for exact terms such as <DocCode>git</DocCode>; semantic matching understands intent even when the wording differs from the stored command description.</DocP>
      <DocList items={["TF-IDF provides fast keyword matching.", "The multilingual MiniLM model contributes semantic similarity.", "Both signals retrieve commands from the curated local corpus."]} />

      <DocH2>Local command corpus</DocH2>
      <DocP>Command scenarios live in YAML files under <DocCode>everycli/data/commands/</DocCode>. Each scenario carries descriptions, tags, Linux and Windows command variants, explanations, and optional warnings.</DocP>
    </DocPage>
  )
}
