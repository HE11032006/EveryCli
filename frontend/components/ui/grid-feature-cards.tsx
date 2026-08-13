import React from "react"
import { cn } from "@/lib/utils"

export type GridFeature = {
  title: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  description: string
  pattern: number[][]
}

type FeatureCardProps = React.ComponentProps<"div"> & {
  feature: GridFeature
}

export function FeatureCard({ feature, className, ...props }: FeatureCardProps) {
  const Icon = feature.icon

  return (
    <div className={cn("relative overflow-hidden p-6 sm:p-8", className)} {...props}>
      <div className="pointer-events-none absolute left-1/2 top-0 -ml-20 -mt-2 h-full w-full [mask-image:linear-gradient(white,transparent)]">
        <div className="absolute inset-0 bg-gradient-to-r from-foreground/[0.04] to-foreground/[0.01] [mask-image:radial-gradient(farthest-side_at_top,white,transparent)]">
          <GridPattern width={20} height={20} x="-12" y="4" squares={feature.pattern} className="absolute inset-0 h-full w-full fill-foreground/[0.04] stroke-foreground/20 mix-blend-overlay" />
        </div>
      </div>
      <Icon className="relative z-10 size-6 text-[#ff7566]" strokeWidth={1.25} aria-hidden="true" />
      <h3 className="relative z-10 mt-10 text-sm font-medium tracking-wide text-foreground md:text-base">{feature.title}</h3>
      <p className="relative z-10 mt-2 max-w-xs text-xs leading-6 text-muted-foreground">{feature.description}</p>
    </div>
  )
}

function GridPattern({
  width,
  height,
  x,
  y,
  squares,
  ...props
}: React.ComponentProps<"svg"> & { width: number; height: number; x: string; y: string; squares: number[][] }) {
  const patternId = React.useId()

  return (
    <svg aria-hidden="true" {...props}>
      <defs>
        <pattern id={patternId} width={width} height={height} patternUnits="userSpaceOnUse" x={x} y={y}>
          <path d={`M.5 ${height}V.5H${width}`} fill="none" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" strokeWidth="0" fill={`url(#${patternId})`} />
      <svg x={x} y={y} className="overflow-visible">
        {squares.map(([squareX, squareY], index) => <rect key={index} strokeWidth="0" width={width + 1} height={height + 1} x={squareX * width} y={squareY * height} />)}
      </svg>
    </svg>
  )
}
