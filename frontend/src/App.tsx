import { useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabaseClient";
import { AuthCard } from "./components/AuthCard";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loadingSession, setLoadingSession] = useState(true);

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

  return (
    <div className="auth-page">
      {session ? (
        <div className="auth-card auth-signed-in">
          <p className="auth-wordmark">koala</p>
          <p>
            Signed in as <strong>{session.user.email}</strong>
          </p>
          <button
            className="auth-submit"
            type="button"
            onClick={() => supabase.auth.signOut()}
          >
            Sign out
          </button>
        </div>
      ) : (
        <AuthCard />
      )}
    </div>
  );
}

export default App;
