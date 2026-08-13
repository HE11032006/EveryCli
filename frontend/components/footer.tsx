import { site } from "@/lib/site"

const licenseUrl = `${site.github}/blob/main/LICENSE.md`

export function Footer() {
  return (
    <footer className="border-t border-white/10 px-6 py-12 lg:px-12 lg:py-16">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 text-sm text-white/45 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-medium text-white/90">EveryCli</p>
          <p className="mt-2">
            Built by <span className="text-white/80">Euloge</span> &amp; <span className="text-white/80">Karmel</span>
          </p>
        </div>
        <nav aria-label="Footer navigation" className="flex flex-wrap items-center gap-x-7 gap-y-3 text-sm">
          <a href={site.github} target="_blank" rel="noreferrer" className="transition-colors hover:text-white">GitHub</a>
          <a href={licenseUrl} target="_blank" rel="noreferrer" className="transition-colors hover:text-white">MIT License</a>
          <span title="Privacy policy coming soon" className="cursor-default text-white/30">Privacy</span>
          <span title="Terms coming soon" className="cursor-default text-white/30">Terms</span>
        </nav>
      </div>
    </footer>
  )
}
