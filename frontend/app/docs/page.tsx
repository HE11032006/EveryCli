import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function IntroductionPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="INTRODUCTION"
      description="FORGE is a zero-config command-line tool that scaffolds projects, runs deterministic builds, and ships to any target — all from a single binary."
      href="/docs"
    >
      <DocP>
        FORGE unifies the three phases of the developer loop — scaffold, build, ship — behind one
        consistent, scriptable interface. It has no runtime dependencies, produces reproducible
        artifacts, and returns structured output that is trivial to wire into CI.
      </DocP>

      <DocH2>Why FORGE</DocH2>
      <DocList
        items={[
          "Zero configuration — sensible defaults that you can override only when needed.",
          "Deterministic builds — the same input always produces the exact same output hash.",
          "Any target — deploy to edge, containers, or static hosts with one adapter interface.",
          "Scriptable — every command returns JSON with the --json flag for pipelines.",
        ]}
      />

      <DocH2>Install in one line</DocH2>
      <DocP>Install the CLI globally and verify it is on your PATH:</DocP>
      <CodeBlock code={"npm install -g @forge/cli\nforge --version"} label="bash" shell />

      <DocH2>Where to next</DocH2>
      <DocList
        items={[
          "Installation — every supported install method and platform.",
          "Quick Start — go from empty folder to deployed app in three commands.",
          "Guides — project structure, configuration, and deploy targets in depth.",
        ]}
      />
    </DocPage>
  )
}
