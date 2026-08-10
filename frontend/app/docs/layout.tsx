import type { Metadata } from "next"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { DocsShell } from "@/components/docs/docs-shell"

export const metadata: Metadata = {
  title: "Documentation // FORGE",
  description:
    "FORGE documentation: installation, quick start, guides, CLI reference, code examples, and troubleshooting.",
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen dot-grid-bg flex flex-col">
      <Navbar />
      <div className="flex-1">
        <DocsShell>{children}</DocsShell>
      </div>
      <Footer />
    </div>
  )
}
