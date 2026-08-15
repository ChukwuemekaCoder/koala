import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useLocation, type Location } from "react-router-dom";
import { RequireSession, RequireOnboarded, RedirectIfOnboarded, RedirectIfAuthed } from "../lib/guards";
import { LandingRoute } from "./LandingRoute";
import { AuthRoute } from "./AuthRoute";
import { OnboardingRoute } from "./OnboardingRoute";
import { DashboardRoute } from "./DashboardRoute";
import { NotificationsRoute } from "./NotificationsRoute";

// Outgoing page fades out over 150ms, then the incoming page fades in
// over 200ms with a slight upward rise (DESIGN.md motion spec). React
// Router swaps routed content immediately on navigation, so to get a
// real exit animation we hold the previous location's route tree
// mounted for the 150ms "exiting" phase (via <Routes location={...}>,
// which freezes which route matches) before swapping to the new one.
export function AnimatedRoutes() {
  const location = useLocation();
  const [displayedLocation, setDisplayedLocation] = useState<Location>(location);
  const [phase, setPhase] = useState<"idle" | "exiting" | "entering">("idle");

  useEffect(() => {
    if (location.pathname === displayedLocation.pathname) return;
    setPhase("exiting");
    const exitTimer = setTimeout(() => {
      setDisplayedLocation(location);
      setPhase("entering");
    }, 150);
    return () => clearTimeout(exitTimer);
  }, [location, displayedLocation]);

  useEffect(() => {
    if (phase !== "entering") return;
    const enterTimer = setTimeout(() => setPhase("idle"), 200);
    return () => clearTimeout(enterTimer);
  }, [phase]);

  return (
    <div className={`route-transition route-transition--${phase}`}>
      <Routes location={displayedLocation}>
        <Route element={<RedirectIfAuthed />}>
          <Route path="/" element={<LandingRoute />} />
          <Route path="/auth" element={<AuthRoute />} />
        </Route>

        <Route element={<RequireSession />}>
          <Route element={<RedirectIfOnboarded />}>
            <Route path="/onboarding" element={<OnboardingRoute />} />
          </Route>
          <Route element={<RequireOnboarded />}>
            <Route path="/dashboard" element={<DashboardRoute />} />
            <Route path="/notifications" element={<NotificationsRoute />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
