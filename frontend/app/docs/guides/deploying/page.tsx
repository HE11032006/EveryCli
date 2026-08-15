import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocList, DocNote } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function BuildFromSourcePage() {
  return (
    <DocPage eyebrow="002 // GUIDES" title="BUILD FROM SOURCE" description="Set up a development environment, test EveryCli locally, and generate a packaged daemon with PyInstaller." href="/docs/guides/deploying">
      <DocH2>Prepare the environment</DocH2>
      <CodeBlock code={"git clone https://github.com/HE11032006/EveryCli.git\ncd EveryCli\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"} label="bash" shell />

      <DocH2>Test locally</DocH2>
      <CodeBlock code={'python3 -m everycli.everycli daemon --start\npython3 -m everycli.everycli search "git commit"'} label="bash" shell />

      <DocH2>Build the daemon</DocH2>
      <DocP>PyInstaller uses the repository specification to package the full CPU daemon into the <code>dist/</code> directory.</DocP>
      <CodeBlock code="pyinstaller everycli-daemon.spec --clean" label="bash" shell />
      <DocNote>Check that the distribution folder contains both the wrapper and the packaged daemon before distributing it.</DocNote>
    </DocPage>
  )
}
