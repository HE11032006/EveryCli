export const site = {
  name: "EveryCli",
  command: "everycli",
  tagline: "DESCRIBE. DON'T SEARCH.",
  description:
    "EveryCli is an AI-powered command-line assistant that instantly finds the exact command you need — just describe it in plain language. Works with Git, Docker, and Linux, without ever leaving your terminal.",
  version: "1.0.0",
  demo: 'everycli "how to undo my last commit"',
  install: "python -m everycli.everycli search \"how to undo my last commit\"",
  github: "https://github.com/HE11032006/EveryCli",
  releases: "https://github.com/HE11032006/EveryCli/releases",
}

export type DocsNavItem = {
  title: string
  href: string
}

export type DocsNavSection = {
  label: string
  index: string
  items: DocsNavItem[]
}

export const docsNav: DocsNavSection[] = [
  {
    label: "GET_STARTED",
    index: "001",
    items: [
      { title: "Introduction", href: "/docs" },
      { title: "Installation", href: "/docs/installation" },
      { title: "Quick Start", href: "/docs/quick-start" },
    ],
  },
  {
    label: "GUIDES",
    index: "002",
    items: [
      { title: "How It Works", href: "/docs/guides/how-it-works" },
      { title: "Sentinel Planner", href: "/docs/guides/sentinel" },
      { title: "Shell Integration", href: "/docs/guides/shell-integration" },
    ],
  },
  {
    label: "REFERENCE",
    index: "003",
    items: [
      { title: "CLI Commands", href: "/docs/reference/commands" },
      { title: "Configuration", href: "/docs/reference/config" },
    ],
  },
  {
    label: "EXAMPLES",
    index: "004",
    items: [{ title: "Code Examples", href: "/docs/examples" }],
  },
  {
    label: "HELP",
    index: "005",
    items: [{ title: "FAQ & Troubleshooting", href: "/docs/faq" }],
  },
]

// Flattened list for prev/next navigation
export const docsFlat: DocsNavItem[] = docsNav.flatMap((s) => s.items)
