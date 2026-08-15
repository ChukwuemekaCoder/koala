import { Navigate, Outlet } from "react-router-dom";
import { useSession } from "./SessionContext";
import { useOnboarding } from "./OnboardingContext";

// Wraps /onboarding, /dashboard, /notifications. Renders nothing (blank,
// matching the pre-router loading placeholder) until both session and
// onboarding status are resolved.
export function RequireSession() {
  const { session, loadingSession } = useSession();
  const { onboardingComplete } = useOnboarding();

  if (loadingSession) return <div className="auth-page" />;
  if (!session) return <Navigate to="/auth" replace />;
  if (onboardingComplete === null) return <div className="auth-page" />; // still fetching profile

  return <Outlet />;
}

// Wraps /dashboard and /notifications specifically: session is already
// guaranteed by the parent RequireSession route; this just adds the
// "must be onboarded" condition.
export function RequireOnboarded() {
  const { onboardingComplete } = useOnboarding();
  if (!onboardingComplete) return <Navigate to="/onboarding" replace />;
  return <Outlet />;
}

// Wraps /onboarding specifically: bounce to /dashboard if already done,
// so a completed onboarding can't be re-entered via URL.
export function RedirectIfOnboarded() {
  const { onboardingComplete } = useOnboarding();
  if (onboardingComplete) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

// Wraps / and /auth: a logged-in user shouldn't see marketing/auth again.
export function RedirectIfAuthed() {
  const { session, loadingSession } = useSession();
  const { onboardingComplete } = useOnboarding();

  if (loadingSession) return <div className="auth-page" />;
  if (session) {
    if (onboardingComplete === null) return <div className="auth-page" />;
    return <Navigate to={onboardingComplete ? "/dashboard" : "/onboarding"} replace />;
  }
  return <Outlet />;
}
