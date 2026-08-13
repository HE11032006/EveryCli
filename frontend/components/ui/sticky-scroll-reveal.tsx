"use client"

import React, { useRef, useState } from "react"
import { motion, useMotionValueEvent, useScroll } from "motion/react"
import { cn } from "@/lib/utils"

type StickyScrollItem = {
  label?: string
  title: string
  description: string
  content?: React.ReactNode
}

export function StickyScroll({
  content,
  contentClassName,
}: {
  content: StickyScrollItem[]
  contentClassName?: string
}) {
  const [activeCard, setActiveCard] = useState(0)
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start 65%", "end 60%"],
  })

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    const breakpoints = content.map((_, index) => index / content.length)
    const nextActiveCard = breakpoints.reduce((closest, breakpoint, index) => (
      Math.abs(latest - breakpoint) < Math.abs(latest - breakpoints[closest]) ? index : closest
    ), 0)
    setActiveCard(nextActiveCard)
  })

  return (
    <div ref={ref} className="relative grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,0.8fr)_minmax(480px,1.2fr)] lg:gap-20">
      <div className="min-w-0">
        {content.map((item, index) => (
          <motion.article
            key={item.title}
            animate={{ opacity: activeCard === index ? 1 : 0.28 }}
            transition={{ duration: 0.28 }}
            className="flex min-h-[52vh] flex-col justify-center py-12 first:pt-0 lg:min-h-[68vh] lg:py-20"
          >
            {item.label && <p className="mb-5 text-[10px] font-mono uppercase tracking-[0.2em] text-emerald-400">{item.label}</p>}
            <h2 className="max-w-xl font-pixel text-4xl leading-[1.06] tracking-tight text-white sm:text-5xl">
              {item.title}
            </h2>
            <p className="mt-7 max-w-lg text-sm leading-7 text-white/55 sm:text-base">
              {item.description}
            </p>
            <div className={cn("mt-9 h-[17rem] overflow-hidden rounded-lg border border-white/10 lg:hidden", contentClassName)}>
              {item.content ?? null}
            </div>
          </motion.article>
        ))}
      </div>
      <div className="sticky top-24 hidden h-[min(72vh,620px)] overflow-hidden rounded-xl lg:block">
        <motion.div
          key={activeCard}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.32 }}
          className={cn("h-full w-full overflow-hidden", contentClassName)}
        >
          {content[activeCard]?.content ?? null}
        </motion.div>
      </div>
    </div>
  )
}
