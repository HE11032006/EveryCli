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
      <CodeBlock code={'everycli search "remove unused Docker images"'} label="step_01" shell />

      <DocH2>2. Narrow the results when needed</DocH2>
      <DocP>
        Ask for more candidates or scope the search to a specific environment with{" "}
        <DocCode>--top</DocCode> and <DocCode>--env</DocCode>.
      </DocP>
      <CodeBlock
        code={'everycli search "undo my last commit" --env git --top 3'}
        label="step_02"
        shell
      />

      <DocH2>3. Choose interactively</DocH2>
      <DocP>
        Add <DocCode>--interactive</DocCode> to navigate candidates with arrow keys and select
        one in the terminal.
      </DocP>
      <CodeBlock
        code={'everycli search "create an SSH key" --interactive'}
        label="step_03"
        shell
      />

      <DocH2>4. Plan before you run</DocH2>
      <DocP>Sentinel returns a command, its risk level, and checks to make before execution.</DocP>
      <CodeBlock
        code={'everycli plan "remove unused Docker images safely"'}
        label="step_04"
        shell
      />

      <DocH2>5. Add a personal command</DocH2>
      <DocP>
        Extend the local corpus with a command you use often. Your personal entries stay separate
        from the built-in corpus and survive normal updates and uninstall:
      </DocP>
      <CodeBlock
        code={"everycli add\neverycli list\neverycli remove"}
        label="bash / powershell"
        shell
      />

      <DocNote>
        EveryCli finds and explains commands. Review the result yourself; a search is not an
        automatic execution.
      </DocNote>
    </DocPage>
  )
}
