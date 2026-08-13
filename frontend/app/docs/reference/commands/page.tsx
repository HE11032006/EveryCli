import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function CommandsReferencePage() {
  return (
    <DocPage
      eyebrow="003 // REFERENCE"
      title="CLI COMMANDS"
      description="The current EveryCli command surface for search, safe planning, local corpus additions, and daemon control."
      href="/docs/reference/commands"
    >
      <DocH2>Commands</DocH2>
      <DocTable
        head={["Command", "Description"]}
        rows={[
          [<DocCode key="search">everycli search &lt;query&gt;</DocCode>, "Find command candidates from a natural-language task."],
          [<DocCode key="plan">everycli plan &lt;query&gt;</DocCode>, "Prepare a corpus-grounded command with risk and preflight checks."],
          [<DocCode key="daemon">everycli daemon</DocCode>, "Start, stop, inspect, or read logs from the local daemon."],
          [<DocCode key="add">everycli add</DocCode>, "Interactively add a command scenario to the local corpus."],
        ]}
      />

      <DocH2>Search options</DocH2>
      <DocTable
        head={["Option", "Description"]}
        rows={[
          [<DocCode key="top">--top, -t</DocCode>, "Return a chosen number of command candidates."],
          [<DocCode key="env">--env</DocCode>, "Filter candidates by environment, such as git or docker."],
          [<DocCode key="interactive">--interactive, -i</DocCode>, "Choose among returned candidates interactively."],
          [<DocCode key="copy">--copy, -c</DocCode>, "Copy the selected command to the clipboard."],
          [<DocCode key="no-daemon">--no-daemon</DocCode>, "Force direct local search without the daemon."],
        ]}
      />

      <DocH2>Plan</DocH2>
      <DocP>The planner never runs a shell command. Use <DocCode>--local</DocCode> to force the local planner.</DocP>
      <CodeBlock code={'everycli plan "remove unused Docker images safely" --local'} label="usage" />

      <DocH2>Daemon</DocH2>
      <CodeBlock
        code={"everycli daemon --start\neverycli daemon --status\neverycli daemon --logs\neverycli daemon --stop"}
        label="usage"
      />
    </DocPage>
  )
}
