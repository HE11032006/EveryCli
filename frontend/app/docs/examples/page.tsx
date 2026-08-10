import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ExamplesPage() {
  return (
    <DocPage
      eyebrow="004 // EXAMPLES"
      title="CODE EXAMPLES"
      description="Copy-paste recipes for the most common FORGE workflows."
      href="/docs/examples"
    >
      <DocH2>GitHub Actions CI</DocH2>
      <DocP>Build, test, and deploy on every push to main:</DocP>
      <CodeBlock
        code={
          "name: ci\n" +
          "on:\n" +
          "  push:\n" +
          "    branches: [main]\n" +
          "jobs:\n" +
          "  ship:\n" +
          "    runs-on: ubuntu-latest\n" +
          "    steps:\n" +
          "      - uses: actions/checkout@v4\n" +
          "      - run: npm install -g @forge/cli\n" +
          "      - run: forge test\n" +
          "      - run: forge build --release\n" +
          "      - run: forge deploy --target=edge"
        }
        label=".github/workflows/ci.yml"
      />

      <DocH2>Parsing JSON output</DocH2>
      <DocP>
        Pipe the <DocCode>--json</DocCode> output of a deploy into <DocCode>jq</DocCode> to grab the
        resulting URL:
      </DocP>
      <CodeBlock
        code={'URL=$(forge deploy --preview --json | jq -r ".url")\necho "Deployed to $URL"'}
        label="bash"
        shell
      />

      <DocH2>Authoring a plugin</DocH2>
      <DocP>A minimal plugin that logs the build duration via typed hooks:</DocP>
      <CodeBlock
        code={
          'import { definePlugin } from "@forge/cli"\n\n' +
          "export default definePlugin({\n" +
          '  name: "timing",\n' +
          "  setup(hooks) {\n" +
          "    let start = 0\n" +
          "    hooks.onBuildStart(() => { start = Date.now() })\n" +
          "    hooks.onBuildEnd(() => {\n" +
          "      console.log(`built in ${Date.now() - start}ms`)\n" +
          "    })\n" +
          "  },\n" +
          "})"
        }
        label="plugin.ts"
      />

      <DocH2>Multi-target matrix</DocH2>
      <DocP>Deploy the same artifact to several targets in one script:</DocP>
      <CodeBlock
        code={
          "forge build --release\n" +
          "for t in edge containers static; do\n" +
          "  forge deploy --target=$t\n" +
          "done"
        }
        label="bash"
        shell
      />
    </DocPage>
  )
}
