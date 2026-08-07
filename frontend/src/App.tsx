import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabaseClient";
import { AuthCard } from "./components/AuthCard";
import { Landing } from "./components/landing/Landing";
import { Dashboard } from "./components/dashboard/Dashboard";

type View = "landing" | "auth";
type AuthTab = "signin" | "signup";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [view, setView] = useState<View>("landing");
  const [authTab, setAuthTab] = useState<AuthTab>("signin");

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

  if (loadingSession) {
    return <div className="auth-page" />;
  }

  if (session) {
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
