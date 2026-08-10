import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function ProjectStructurePage() {
  return (
    <DocPage
      eyebrow="002 // GUIDES"
      title="PROJECT STRUCTURE"
      description="Every FORGE project follows the same predictable layout, so tooling and teammates always know where things live."
      href="/docs/guides/project-structure"
    >
      <DocH2>Default layout</DocH2>
      <CodeBlock
        code={
          "my-app/\n" +
          "├── forge.config.ts   # project configuration\n" +
          "├── src/              # application source\n" +
          "│   └── main.ts\n" +
          "├── tests/            # test suites\n" +
          "├── .forge/           # build cache (git-ignored)\n" +
          "└── dist/             # build output"
        }
        label="tree"
      />

      <DocH2>Directories</DocH2>
      <DocTable
        head={["Path", "Purpose"]}
        rows={[
          [<DocCode key="c">src/</DocCode>, "Your application code. The entry point is resolved from forge.config.ts."],
          [<DocCode key="c">tests/</DocCode>, "Test files. Run with forge test."],
          [<DocCode key="c">.forge/</DocCode>, "Local build cache and metadata. Safe to delete; regenerated on demand."],
          [<DocCode key="c">dist/</DocCode>, "Release artifacts produced by forge build."],
        ]}
      />

      <DocH2>Convention over configuration</DocH2>
      <DocP>
        FORGE resolves the entry point, test glob, and output directory from these conventions
        automatically. Override any of them in <DocCode>forge.config.ts</DocCode> when your project
        needs something different.
      </DocP>
    </DocPage>
  )
}
