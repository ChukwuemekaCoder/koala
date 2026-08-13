import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabaseClient";
import { AuthCard } from "./components/AuthCard";
import { Landing } from "./components/landing/Landing";
import { Dashboard } from "./components/dashboard/Dashboard";
import { Onboarding } from "./components/onboarding/Onboarding";
import { getStudentProfile } from "./lib/api";

type View = "landing" | "auth";
type AuthTab = "signin" | "signup";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [view, setView] = useState<View>("landing");
  const [authTab, setAuthTab] = useState<AuthTab>("signin");
  const [onboardingComplete, setOnboardingComplete] = useState<boolean | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoadingSession(false);
    });

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session);
      },
    );

    return () => subscription.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session) {
      setOnboardingComplete(null);
      return;
    }
    getStudentProfile(session.access_token)
      .then((profile) => setOnboardingComplete(profile.onboarding_complete))
      .catch(() => setOnboardingComplete(true)); // fail open to the dashboard's own error state
  }, [session]);

  if (loadingSession) {
    return <div className="auth-page" />;
  }

  if (session) {
    if (onboardingComplete === null) {
      return <div className="auth-page" />;
    }
    if (!onboardingComplete) {
      return (
        <Onboarding
          accessToken={session.access_token}
          onComplete={() => setOnboardingComplete(true)}
        />
      );
    }
    return (
      <Dashboard
        accessToken={session.access_token}
        onSignOut={() => supabase.auth.signOut()}
      />
    );
  }

  if (view === "auth") {
    return (
      <div className="auth-page">
        <AuthCard
          initialTab={authTab}
          onBack={() => setView("landing")}
        />
      </div>
    );
  }

  return (
    <Landing
      onSignIn={() => {
        setAuthTab("signin");
        setView("auth");
      }}
      onGetStarted={() => {
        setAuthTab("signup");
        setView("auth");
      }}
    />
  );
}

export default App;
