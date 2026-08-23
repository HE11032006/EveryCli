import { Info } from "lucide-react"

function headingId(children: React.ReactNode) {
  if (typeof children !== "string") return undefined
  return children
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
}

export function DocH2({ children }: { children: React.ReactNode }) {
  return (
    <h2 id={headingId(children)} className="mt-6 scroll-mt-24 text-lg font-mono font-bold tracking-widest uppercase text-foreground">
      {children}
    </h2>
  )
}

export function DocH3({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mt-2 text-sm font-mono font-bold tracking-widest uppercase text-[#ea580c]">
      {children}
    </h3>
  )
}

export function DocP({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm font-mono leading-relaxed text-muted-foreground text-pretty">
      {children}
    </p>
  )
}

export function DocList({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-sm font-mono leading-relaxed text-muted-foreground">
          <span className="mt-0.5 select-none text-[#ea580c]">{"—"}</span>
          <span className="text-pretty">{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function DocCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="border border-border bg-muted px-1.5 py-0.5 text-xs font-mono text-foreground">
      {children}
    </code>
  )
}

export function DocNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-3 border-l-2 border-[#ea580c] bg-muted/50 p-4">
      <Info size={16} strokeWidth={2} className="mt-0.5 shrink-0 text-[#ea580c]" />
      <div className="text-sm font-mono leading-relaxed text-foreground text-pretty">
        {children}
      </div>
    </div>
  )
}

interface DocTableProps {
  head: string[]
  rows: React.ReactNode[][]
}

export function DocTable({ head, rows }: DocTableProps) {
  return (
    <div className="overflow-x-auto border-2 border-foreground">
      <table className="w-full border-collapse text-left">
        <thead>
          <tr className="border-b-2 border-foreground bg-foreground text-background">
            {head.map((h) => (
              <th
                key={h}
                className="px-4 py-2 text-[10px] font-mono font-bold tracking-widest uppercase"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-b-0">
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="px-4 py-2.5 align-top text-xs font-mono text-muted-foreground"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
