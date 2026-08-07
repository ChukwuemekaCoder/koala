import { Nav } from "./Nav";
import { Hero } from "./Hero";
import { ProblemSection } from "./ProblemSection";
import { FeaturesBento } from "./FeaturesBento";
import { Reviews } from "./Reviews";
import { ClosingBand } from "./ClosingBand";
import { Footer } from "./Footer";

interface LandingProps {
  onSignIn: () => void;
  onGetStarted: () => void;
}

export function Landing({ onSignIn, onGetStarted }: LandingProps) {
  return (
    <div className="landing-page">
      <div className="section--sage landing-nav-wrap">
        <Nav onSignIn={onSignIn} onGetStarted={onGetStarted} />
      </div>
      <Hero onGetStarted={onGetStarted} />
      <ProblemSection />
      <FeaturesBento />
      <Reviews />
      <ClosingBand onGetStarted={onGetStarted} />
      <Footer />
    </div>
  );
}
