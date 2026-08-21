import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode, DocNote } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function CommandsReferencePage() {
  return (
    <DocPage
      eyebrow="003 // REFERENCE"
      title="CLI COMMANDS"
      description="The full EveryCli command surface: search, safe planning, corpus management, and daemon control."
      href="/docs/reference/commands"
    >
      <DocH2>Commands</DocH2>
      <DocTable
        head={["Command", "Description"]}
        rows={[
          [<DocCode key="search">everycli search &lt;query&gt;</DocCode>, "Find command candidates from a natural-language task description."],
          [<DocCode key="plan">everycli plan &lt;query&gt;</DocCode>, "Prepare a corpus-grounded command with risk level and preflight checks."],
          [<DocCode key="add">everycli add</DocCode>, "Interactively add a command scenario to the local corpus."],
          [<DocCode key="list">everycli list</DocCode>, "List all command scenarios stored in the local user corpus."],
          [<DocCode key="remove">everycli remove &lt;id&gt;</DocCode>, "Remove a command scenario from the local corpus (prompts for confirmation)."],
        ]}
      />

      <DocH2>Search options</DocH2>
      <DocTable
        head={["Option", "Description"]}
        rows={[
          [<DocCode key="top">--top, -t</DocCode>, "Return a chosen number of command candidates (default: 1)."],
          [<DocCode key="env">--env</DocCode>, "Hint a namespace such as git or docker to boost relevant results."],
          [<DocCode key="interactive">--interactive, -i</DocCode>, "Choose among returned candidates with arrow keys."],
          [<DocCode key="copy">--copy, -c</DocCode>, "Copy the selected command to the clipboard."],
          [<DocCode key="no-daemon">--no-daemon</DocCode>, "Force direct local search without contacting the daemon."],
          [<DocCode key="error">--error &lt;msg&gt;</DocCode>, "Find a command that fixes a given error message."],
        ]}
      />

      <DocH2>Plan</DocH2>
      <DocP>The planner never runs a shell command. Use <DocCode>--local</DocCode> to force the offline planner.</DocP>
      <CodeBlock code={'everycli plan "remove unused Docker images safely"\neverycli plan --local "see which branch I am on"'} label="usage" />

      <DocH2>Daemon management</DocH2>
      <DocP>
        The daemon is a Windows service installed by <DocCode>install.ps1</DocCode>. Manage it
        with the standard Windows service control commands:
      </DocP>
      <CodeBlock
        code={
          "# Start\nsc.exe start EveryCliDaemon\n\n# Stop\nsc.exe stop EveryCliDaemon\n\n# Query status\nsc.exe query EveryCliDaemon\n\n# Uninstall\n.\\uninstall.ps1"
        }
        label="powershell"
      />

      <DocNote>
        There is no <DocCode>everycli daemon</DocCode> sub-command. Daemon lifecycle is handled
        by <DocCode>install.ps1</DocCode> / <DocCode>uninstall.ps1</DocCode> and{" "}
        <DocCode>sc.exe</DocCode>.
      </DocNote>
    </DocPage>
  )
}
