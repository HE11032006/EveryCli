import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function QuickStartPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="QUICK START"
      description="Find a command, inspect it, and prepare a safer multi-step action from your terminal."
      href="/docs/quick-start"
    >
      <DocH2>1. Search by intent</DocH2>
      <DocP>Describe the task rather than trying to recall the exact syntax:</DocP>
      <CodeBlock code={'python -m everycli.everycli search "remove unused Docker images"'} label="step_01" shell />

      <DocH2>2. Narrow the results when needed</DocH2>
      <DocP>
        Ask for more candidates or restrict the search to an environment with <DocCode>--top</DocCode>
        and <DocCode>--env</DocCode>.
      </DocP>
      <CodeBlock code={'python -m everycli.everycli search "undo my last commit" --env git --top 3'} label="step_02" shell />

      <DocH2>3. Plan before you run</DocH2>
      <DocP>Sentinel returns a command, its risk level, and checks to make before execution.</DocP>
      <CodeBlock code={'python -m everycli.everycli plan "remove unused Docker images safely" --local'} label="step_03" shell />

      <DocH2>Keep the daemon warm</DocH2>
      <CodeBlock code={"python -m everycli.everycli daemon --start\npython -m everycli.everycli daemon --status"} label="bash" shell />

      <DocNote>
        EveryCli finds and explains commands. Review the result yourself; a search is not an automatic execution.
      </DocNote>
    </DocPage>
  )
}
