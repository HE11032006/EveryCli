import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ExamplesPage() {
  return (
    <DocPage
      eyebrow="004 // EXAMPLES"
      title="COMMON WORKFLOWS"
      description="Real EveryCli workflows for command discovery, safer planning, corpus customisation, and shell integration."
      href="/docs/examples"
    >
      <DocH2>Find a Git command</DocH2>
      <DocP>Describe the task in natural language and let the local corpus retrieve the command:</DocP>
      <CodeBlock code={'everycli search "undo my last commit without losing my changes"'} label="bash" shell />

      <DocH2>Scope a Docker search</DocH2>
      <DocP>Use a namespace hint in the query when the tool is known:</DocP>
      <CodeBlock code={'everycli search "docker: remove unused images"'} label="bash" shell />

      <DocH2>Inspect several candidates</DocH2>
      <DocP>
        <DocCode>--top</DocCode> returns additional matches;{" "}
        <DocCode>--interactive</DocCode> lets you pick one with arrow keys.
      </DocP>
      <CodeBlock
        code={'everycli search "create an SSH key" --top 3\neverycli search "create an SSH key" --interactive'}
        label="bash"
        shell
      />

      <DocH2>Add a custom command</DocH2>
      <DocP>
        Save a command you use often to the local corpus so EveryCli can surface it in future
        searches:
      </DocP>
      <CodeBlock code={"everycli add"} label="bash" shell />

      <DocH2>Plan before a risky action</DocH2>
      <DocP>Sentinel returns risk level and preflight checks — it never runs anything automatically.</DocP>
      <CodeBlock code={'everycli plan "remove unused Docker images safely"'} label="bash" shell />

      <DocH2>Ask an LLM and save to corpus</DocH2>
      <DocP>
        If a command is not yet in your corpus, ask any configured LLM API and optionally save the returned command for instant offline lookup:
      </DocP>
      <CodeBlock
        code={
          '# 1. Configure once\neverycli config set api_key sk-...\n\n# 2. Ask and optionally save into ~/.everycli/commands/\neverycli ask "compress a folder into tar.gz"'
        }
        label="bash"
        shell
      />

      <DocH2>List and remove personal corpus entries</DocH2>
      <CodeBlock code={"everycli list\neverycli remove my_custom_id"} label="bash" shell />
    </DocPage>
  )
}
