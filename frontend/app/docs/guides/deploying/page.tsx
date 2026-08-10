import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocTable, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function DeployingPage() {
  return (
    <DocPage
      eyebrow="002 // GUIDES"
      title="DEPLOYING"
      description="Ship a built artifact to any target through a single, consistent deploy interface."
      href="/docs/guides/deploying"
    >
      <DocH2>Targets</DocH2>
      <DocTable
        head={["Target", "Description"]}
        rows={[
          [<DocCode key="c">edge</DocCode>, "Global edge network. Lowest latency, ideal for stateless services."],
          [<DocCode key="c">containers</DocCode>, "OCI image pushed to your registry and rolled out."],
          [<DocCode key="c">static</DocCode>, "Static assets uploaded to a CDN-backed bucket."],
        ]}
      />

      <DocH2>Deploy a release</DocH2>
      <DocP>Build first, then deploy the resulting artifact:</DocP>
      <CodeBlock code={"forge build --release\nforge deploy --target=edge"} label="bash" shell />

      <DocH2>Preview deploys</DocH2>
      <DocP>
        Use <DocCode>--preview</DocCode> to deploy to an isolated URL without affecting production.
        Every preview is content-addressed and immutable.
      </DocP>
      <CodeBlock code={"forge deploy --preview"} label="bash" shell />

      <DocH2>Rollbacks</DocH2>
      <DocP>Because every deploy is immutable, rolling back is instant:</DocP>
      <CodeBlock code={"forge deploy list\nforge deploy rollback --to=a1b2c3d"} label="bash" shell />

      <DocNote>
        Add <DocCode>--json</DocCode> to any deploy command to get machine-readable output for CI
        pipelines, including the deploy id and resolved URL.
      </DocNote>
    </DocPage>
  )
}
