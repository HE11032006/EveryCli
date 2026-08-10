import { DocPage } from "@/components/docs/doc-page"
import { DocCode } from "@/components/docs/doc-content"

const FAQ = [
  {
    q: "forge: command not found after install",
    a: "Your global npm bin directory is not on your PATH. Run `npm bin -g` to find it, then add that directory to your shell profile. Restart your terminal and try `forge --version` again.",
  },
  {
    q: "My builds are not reproducible across machines",
    a: "Non-determinism almost always comes from environment leakage. Pin the build target in forge.config.ts, avoid reading Date.now() or random values at build time, and commit your lockfile. Run `forge build --no-cache` to rule out a stale cache.",
  },
  {
    q: "Deploy fails with 'no target configured'",
    a: "Set a default deploy.target in forge.config.ts, or pass --target explicitly on the command line. Run `forge config print` to confirm which target is being resolved.",
  },
  {
    q: "How do I roll back a bad deploy?",
    a: "Every deploy is immutable and content-addressed. List previous deploys with `forge deploy list`, then run `forge deploy rollback --to=<id>` for an instant revert.",
  },
  {
    q: "Can I use FORGE without Node.js?",
    a: "Yes. The Homebrew and install-script methods provide a fully static binary with zero runtime dependencies. Only the npm install method requires Node.js 18+.",
  },
  {
    q: "Where is the build cache stored and is it safe to delete?",
    a: "In the .forge/ directory at your project root. It is git-ignored and safe to delete at any time — FORGE regenerates it on the next build.",
  },
]

export default function FaqPage() {
  return (
    <DocPage
      eyebrow="005 // HELP"
      title="FAQ & TROUBLESHOOTING"
      description="Answers to the questions and errors developers hit most often."
      href="/docs/faq"
    >
      <div className="flex flex-col border-t-2 border-foreground">
        {FAQ.map((item, i) => (
          <details
            key={i}
            className="group border-b-2 border-foreground [&_summary::-webkit-details-marker]:hidden"
          >
            <summary className="flex cursor-pointer items-center justify-between gap-4 py-4 text-sm font-mono font-bold uppercase tracking-wide text-foreground">
              <span className="flex items-start gap-3 text-pretty">
                <span className="select-none text-[#ea580c]">{`0${i + 1}`}</span>
                {item.q}
              </span>
              <span className="select-none text-lg leading-none text-[#ea580c] transition-transform group-open:rotate-45">
                +
              </span>
            </summary>
            <p className="pb-5 pl-8 text-sm font-mono leading-relaxed text-muted-foreground text-pretty">
              {item.a}
            </p>
          </details>
        ))}
      </div>

      <p className="mt-8 text-xs font-mono leading-relaxed text-muted-foreground">
        Still stuck? Run <DocCode>forge --verbose</DocCode> to capture full diagnostics and open an
        issue on GitHub with the output attached.
      </p>
    </DocPage>
  )
}
