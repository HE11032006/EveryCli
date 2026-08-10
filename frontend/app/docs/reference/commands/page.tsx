import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function CommandsReferencePage() {
  return (
    <DocPage
      eyebrow="003 // REFERENCE"
      title="CLI COMMANDS"
      description="The complete command surface. Every command accepts --json for structured output and --help for usage."
      href="/docs/reference/commands"
    >
      <DocH2>Commands</DocH2>
      <DocTable
        head={["Command", "Description"]}
        rows={[
          [<DocCode key="c">forge init &lt;name&gt;</DocCode>, "Scaffold a new project from a template."],
          [<DocCode key="c">forge dev</DocCode>, "Start a hot-reloading local dev server."],
          [<DocCode key="c">forge build</DocCode>, "Produce a deterministic build artifact."],
          [<DocCode key="c">forge test</DocCode>, "Run the project test suites."],
          [<DocCode key="c">forge deploy</DocCode>, "Deploy the current artifact to a target."],
          [<DocCode key="c">forge config</DocCode>, "Inspect resolved configuration."],
          [<DocCode key="c">forge upgrade</DocCode>, "Update the FORGE binary in place."],
        ]}
      />

      <DocH2>Global flags</DocH2>
      <DocTable
        head={["Flag", "Description"]}
        rows={[
          [<DocCode key="c">--json</DocCode>, "Emit machine-readable JSON instead of formatted text."],
          [<DocCode key="c">--env &lt;name&gt;</DocCode>, "Load the named environment overrides."],
          [<DocCode key="c">--cwd &lt;path&gt;</DocCode>, "Run as if invoked from the given directory."],
          [<DocCode key="c">--verbose</DocCode>, "Print detailed diagnostic logs."],
          [<DocCode key="c">--help</DocCode>, "Show usage for a command."],
        ]}
      />

      <DocH2>forge build</DocH2>
      <DocP>Build accepts these command-specific options:</DocP>
      <CodeBlock
        code={
          "forge build [options]\n\n" +
          "  --release        optimized, minified production build\n" +
          "  --watch          rebuild on file changes\n" +
          "  --out <dir>      override the output directory\n" +
          "  --no-cache       ignore the local build cache"
        }
        label="usage"
      />

      <DocH2>forge deploy</DocH2>
      <CodeBlock
        code={
          "forge deploy [options]\n\n" +
          "  --target <name>  edge | containers | static\n" +
          "  --preview        deploy to an isolated preview URL\n" +
          "  --region <id>    override the deploy region\n" +
          "  rollback --to <id>   revert to a previous deploy"
        }
        label="usage"
      />
    </DocPage>
  )
}
