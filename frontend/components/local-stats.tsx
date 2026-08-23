import { WifiOff } from "lucide-react"

const stats = [
  { label: "LATENCY", value: "<50ms", note: "Warm local responses" },
  { label: "PRIVACY", value: "Local-first", note: "No required round-trip" },
  { label: "API COST", value: "Optional", note: "Local search works without one" },
  { label: "UPTIME", value: "Local", note: "Your terminal, your workflow" },
]

export function LocalStats() {
  return (
    <section className="border-t border-white/10 px-6 lg:px-12" aria-label="EveryCli local-first properties">
      <div className="mx-auto grid max-w-7xl border-x border-white/10 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <article key={stat.label} className={`min-h-48 border-b border-white/10 px-7 py-10 sm:px-10 lg:border-b-0 lg:py-11 ${index < stats.length - 1 ? "lg:border-r lg:border-white/10" : ""}`}>
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#f05243]">{index === 1 ? <><WifiOff className="mr-2 inline size-3" />{stat.label}</> : stat.label}</p>
            <p className="mt-5 text-4xl font-medium tracking-tight text-white sm:text-5xl">{stat.value}</p>
            <p className="mt-4 font-mono text-xs text-white/45">{stat.note}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
