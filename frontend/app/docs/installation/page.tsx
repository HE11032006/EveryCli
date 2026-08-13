import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function InstallationPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="INSTALLATION"
      description="EveryCli is currently installed from source. Public package commands will be added when they are ready."
      href="/docs/installation"
    >
      <DocH2>Requirements</DocH2>
      <DocP>
        Use Python 3 and pip, then run the tool from a local checkout of the repository. This keeps
        the current setup explicit while distribution packages are still being prepared.
      </DocP>

      <DocH2>From source</DocH2>
      <CodeBlock
        code={"git clone https://github.com/HE11032006/EveryCli.git\ncd EveryCli\npip install -r requirements.txt"}
        label="bash"
        shell
      />

      <DocH2>Verify with a search</DocH2>
      <DocP>Ask for a command in plain language:</DocP>
      <CodeBlock code={'python -m everycli.everycli search "undo my last commit"'} label="bash" shell />

      <DocNote>
        Releases and package-manager installation commands are not documented here yet, so this page
        never suggests a curl or npm command that does not exist.
      </DocNote>
    </DocPage>
  )
}
