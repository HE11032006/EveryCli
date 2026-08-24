import { DocPage } from "@/components/docs/doc-page"
import { DocH2, DocP, DocNote, DocCode } from "@/components/docs/doc-content"
import { CodeBlock } from "@/components/code-block"

export default function InstallationPage() {
  return (
    <DocPage
      eyebrow="001 // GET_STARTED"
      title="INSTALLATION"
      description="Install the self-contained EveryCli v1.2.1 release without Rust, Cargo, Python, or a compiler. The bundle includes the CLI, daemon, model, tokenizer, native ONNX Runtime, corpus, and installer."
      href="/docs/installation"
    >
      <DocH2>Linux x86_64 — one command</DocH2>
      <DocP>
        Run the installer from a normal Bash terminal. It downloads the latest Linux release,
        verifies its checksum, installs the binaries and model in your user directories, and
        configures the user-level systemd daemon.
      </DocP>
      <CodeBlock
        code="curl -fsSL https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.sh | bash"
        label="bash"
        shell
      />
      <DocP>
        Open a new terminal, or reload your profile with <DocCode>source ~/.profile</DocCode>, then
        verify the installation:
      </DocP>
      <CodeBlock
        code={'source ~/.profile\neverycli search "undo my last commit" --top 2 -i'}
        label="bash"
        shell
      />

      <DocH2>Windows x86_64 — one command</DocH2>
      <DocP>
        Run the command from PowerShell. It downloads the latest Windows release, verifies the
        archive, installs the CLI and daemon in your user profile, and starts the user-level
        startup mode without requiring administrator rights.
      </DocP>
      <CodeBlock
        code="irm https://raw.githubusercontent.com/HE11032006/EveryCli/main/install.ps1 | iex"
        label="powershell"
        shell
      />
      <DocP>
        Open a new PowerShell window so the updated PATH is loaded, then run:
      </DocP>
      <CodeBlock
        code={'everycli search "undo my last commit" --top 2 -i'}
        label="powershell"
        shell
      />
      <DocP>
        The one-line mode deliberately uses the user-level startup path. If you explicitly want a
        Windows service with automatic restart, download the release archive, inspect the script,
        and run <DocCode>install.ps1</DocCode> from a real local file with administrator elevation.
      </DocP>

      <DocH2>Requirements</DocH2>
      <DocP>
        End users need a 64-bit x86_64 Windows or Linux system, PowerShell or Bash, an HTTPS
        connection for the first download, and roughly 1 GB of free disk space for download and
        extraction. Rust, Cargo, Python, Node.js, and a compiler are not required. The first daemon
        start can take longer while the model is loaded and corpus embeddings are prepared; 4 GB
        of available RAM is a practical minimum and 8 GB is more comfortable.
      </DocP>

      <DocH2>Manual archive installation</DocH2>
      <DocP>
        If you prefer to inspect files before running them, download the Linux or Windows archive
        from <a href="https://github.com/HE11032006/EveryCli/releases">GitHub Releases</a>, verify
        <DocCode>SHA256SUMS</DocCode>, extract it, and run the matching installer included in the
        archive. This route is slower but more inspectable than the one-line command.
      </DocP>

      <DocH2>Uninstall</DocH2>
      <DocP>
        The uninstallers remove the installed binaries, links, PATH entries, and background startup
        mechanism. They preserve your personal configuration and commands by default. Run the
        <DocCode>uninstall.sh</DocCode> or <DocCode>uninstall.ps1</DocCode> shipped with the release
        bundle; use the explicit data-removal option only when you also want to delete your personal
        corpus and configuration.
      </DocP>

      <DocNote>
        EveryCli&apos;s main <DocCode>search</DocCode> path is local and does not need an API key.
        <DocCode>everycli ask</DocCode> is optional and needs an OpenAI-compatible API key only
        when you want an external model to propose a command that is not in the local corpus.
      </DocNote>
    </DocPage>
  )
}
