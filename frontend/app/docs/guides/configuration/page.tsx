import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ConfigurationPage() {
  return (
    <DocPage
      eyebrow="002 // GUIDES"
      title="CONFIGURATION"
      description="Configure FORGE with a typed forge.config.ts at the root of your project."
      href="/docs/guides/configuration"
    >
      <DocH2>The config file</DocH2>
      <DocP>
        FORGE reads <DocCode>forge.config.ts</DocCode> from the project root. The
        <DocCode>defineConfig</DocCode> helper gives you full type-checking and autocomplete.
      </DocP>
      <CodeBlock
        code={
          'import { defineConfig } from "@forge/cli"\n\n' +
          "export default defineConfig({\n" +
          '  entry: "src/main.ts",\n' +
          '  outDir: "dist",\n' +
          "  build: {\n" +
          "    minify: true,\n" +
          '    target: "node18",\n' +
          "  },\n" +
          "  deploy: {\n" +
          '    target: "edge",\n' +
          '    region: "auto",\n' +
          "  },\n" +
          "})"
        }
        label="forge.config.ts"
      />

      <DocH2>Environment overrides</DocH2>
      <DocP>
        Any config value can be overridden per environment with the <DocCode>--env</DocCode> flag or
        an environment variable prefixed with <DocCode>FORGE_</DocCode>.
      </DocP>
      <CodeBlock
        code={"forge build --env=production\nFORGE_DEPLOY_TARGET=containers forge deploy"}
        label="bash"
        shell
      />

      <DocNote>
        Run <DocCode>forge config print</DocCode> to see the fully resolved configuration, including
        defaults and environment overrides.
      </DocNote>
    </DocPage>
  )
}
