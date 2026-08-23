import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { WhyItExists } from "@/components/why-it-exists"
import { FeatureGrid } from "@/components/feature-grid"
import { ContributeSection } from "@/components/contribute-section"
import { LocalStats } from "@/components/local-stats"
import { Footer } from "@/components/footer"

export default function Page() {
  return (
    <div className="min-h-screen bg-transparent">
      <Navbar />
      <div className="hero-surface">
        <HeroSection />
      </div>
      <main className="bg-transparent">
        <WhyItExists />
        <FeatureGrid />
        <LocalStats />
        <ContributeSection />
      </main>
      <Footer />
    </div>
  )
}
