import type { Metadata } from "next"
import { Footer } from "@/components/footer"
import { DocsShell } from "@/components/docs/docs-shell"
import { DocsNavbar } from "@/components/docs/docs-navbar"

export const metadata: Metadata = {
  title: "Documentation // EveryCli",
  description:
    "EveryCli documentation: installation, quick start, guides, CLI reference, code examples, and troubleshooting.",
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <DocsNavbar />
      <div className="flex-1">
        <DocsShell>{children}</DocsShell>
      </div>
      <Footer />
    </div>
  )
}
