import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ConfigReferencePage() {
  return (
    <DocPage
      eyebrow="003 // REFERENCE"
      title="CONFIG FILE"
      description="Full reference for every field accepted by forge.config.ts."
      href="/docs/reference/config"
    >
      <DocH2>Top-level fields</DocH2>
      <DocTable
        head={["Field", "Type", "Default"]}
        rows={[
          [<DocCode key="c">entry</DocCode>, "string", '"src/main.ts"'],
          [<DocCode key="c">outDir</DocCode>, "string", '"dist"'],
          [<DocCode key="c">build</DocCode>, "BuildOptions", "{}"],
          [<DocCode key="c">deploy</DocCode>, "DeployOptions", "{}"],
          [<DocCode key="c">plugins</DocCode>, "Plugin[]", "[]"],
        ]}
      />

      <DocH2>BuildOptions</DocH2>
      <DocTable
        head={["Field", "Type", "Default"]}
        rows={[
          [<DocCode key="c">minify</DocCode>, "boolean", "false"],
          [<DocCode key="c">target</DocCode>, "string", '"node18"'],
          [<DocCode key="c">sourcemap</DocCode>, "boolean", "true"],
        ]}
      />

      <DocH2>DeployOptions</DocH2>
      <DocTable
        head={["Field", "Type", "Default"]}
        rows={[
          [<DocCode key="c">target</DocCode>, "string", '"edge"'],
          [<DocCode key="c">region</DocCode>, "string", '"auto"'],
        ]}
      />

      <DocH2>Example</DocH2>
      <DocP>A complete configuration using every top-level field:</DocP>
      <CodeBlock
        code={
          'import { defineConfig } from "@forge/cli"\n' +
          'import analytics from "@forge/plugin-analytics"\n\n' +
          "export default defineConfig({\n" +
          '  entry: "src/main.ts",\n' +
          '  outDir: "dist",\n' +
          "  build: { minify: true, target: \"node18\", sourcemap: true },\n" +
          '  deploy: { target: "edge", region: "iad1" },\n' +
          "  plugins: [analytics()],\n" +
          "})"
        }
        label="forge.config.ts"
      />
    </DocPage>
  )
}
