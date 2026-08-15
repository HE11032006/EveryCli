import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function SentinelPage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="SENTINEL PLANNER" description="Turn a task into a reviewable, corpus-grounded plan before you paste a command into a terminal." href="/docs/guides/sentinel">
      <DocH2>What Sentinel returns</DocH2>
      <DocP><DocCode>everycli plan</DocCode> retrieves candidates from the existing local corpus and produces a plan you can inspect.</DocP>
      <DocList items={["The selected command from the curated corpus.", "A deterministic risk level: low, medium, or high.", "Preflight checks and a confirmation requirement where applicable.", "A guarantee that planning never runs a shell command."]} />

      <DocH2>Plan a task</DocH2>
      <CodeBlock code={'everycli plan "remove unused Docker images safely"'} label="bash" shell />

      <DocH2>Use the local planner</DocH2>
      <DocP>Use <DocCode>--local</DocCode> when you want the offline planner explicitly, without requiring an API key or network connection.</DocP>
      <CodeBlock code={'everycli plan --local "see which branch I am on"'} label="bash" shell />

      <DocNote>Sentinel can explain and rank retrieved candidates, but it does not invent commands or execute them for you.</DocNote>
    </DocPage>
  )
}
