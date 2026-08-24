import { DocPage } from "@/components/docs/doc-page"

import { DocH2, DocP, DocList } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function IntroductionPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="EVERYCLI"
      description="EveryCli is a local-first command discovery tool: describe a task in plain language, then review the command before you run it."
      href="/docs"
    >
      <DocP>
        Command line work is powerful. Remembering every flag and exact syntax is not. EveryCli
        keeps useful commands close to your terminal, so you can find the right next step without
        breaking your flow.
      </DocP>

      <DocH2>What it does</DocH2>
      <DocList
        items={[
          "Searches indexed commands from a plain-language description.",
          "Works with Git, Docker, Linux, npm, Composer, SSH, Python, and more.",
          "Keeps search local-first, with a lexical fallback when a semantic model is unavailable.",
          "Lets you review multi-step actions with Sentinel before execution.",
        ]}
      />

      <DocH2>Try a search</DocH2>
      <DocP>Install the self-contained release first (see Installation), then run a local search:</DocP>
      <CodeBlock code={'everycli search "undo my last commit"'} label="bash" shell />

      <DocH2>Where to next</DocH2>
      <DocList
        items={[
          "Installation — one-line release setup for Linux and Windows.",
          "Quick Start — search and inspect a command in minutes.",
          "CLI Commands — the full command reference.",
        ]}
      />
    </DocPage>
  )
}
