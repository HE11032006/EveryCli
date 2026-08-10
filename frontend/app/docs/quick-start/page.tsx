import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function QuickStartPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="QUICK START"
      description="Go from an empty folder to a deployed application in three commands."
      href="/docs/quick-start"
    >
      <DocH2>1. Scaffold a project</DocH2>
      <DocP>
        Create a new project from a template. The <DocCode>service</DocCode> template sets up a
        production-ready HTTP service with tests and a CI workflow.
      </DocP>
      <CodeBlock code={"forge init my-app --template=service\ncd my-app"} label="step_01" shell />

      <DocH2>2. Build</DocH2>
      <DocP>
        Produce a deterministic release artifact. The build is content-hashed, so identical source
        always yields the same output.
      </DocP>
      <CodeBlock code={"forge build --release"} label="step_02" shell />

      <DocH2>3. Ship</DocH2>
      <DocP>Deploy the artifact to your default target:</DocP>
      <CodeBlock code={"forge deploy --target=edge"} label="step_03" shell />

      <DocH2>The whole loop</DocH2>
      <CodeBlock
        code={"forge init my-app --template=service\ncd my-app\nforge build --release\nforge deploy --target=edge"}
        label="bash"
        shell
      />

      <DocNote>
        Run <DocCode>forge dev</DocCode> while developing for a hot-reloading local server that
        mirrors the production build pipeline.
      </DocNote>
    </DocPage>
  )
}
