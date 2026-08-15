import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ExamplesPage() {
  return (
    <DocPage eyebrow="004 // EXAMPLES" title="COMMON WORKFLOWS" description="Real EveryCli workflows for command discovery, safer planning, daemon use, and shell integration." href="/docs/examples">
      <DocH2>Find a Git command</DocH2>
      <DocP>Describe the task in natural language and let the local corpus retrieve the command:</DocP>
      <CodeBlock code={'everycli search "undo my last commit without losing my changes"'} label="bash" shell />

      <DocH2>Scope a Docker search</DocH2>
      <DocP>Use a namespace hint in the request when the tool is known:</DocP>
      <CodeBlock code={'everycli search "docker: remove unused images"'} label="bash" shell />

      <DocH2>Inspect several candidates</DocH2>
      <DocP><DocCode>--top</DocCode> returns additional matches; <DocCode>--interactive</DocCode> lets you choose one in the terminal.</DocP>
      <CodeBlock code={'everycli search "create an SSH key" --top 3\neverycli search "create an SSH key" --interactive'} label="bash" shell />

      <DocH2>Keep local search ready</DocH2>
      <CodeBlock code={"everycli daemon --start\neverycli daemon --status"} label="bash" shell />
    </DocPage>
  )
}
