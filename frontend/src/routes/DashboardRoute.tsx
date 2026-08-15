import { useNavigate } from "react-router-dom";
import { useSession } from "../lib/SessionContext";
import { supabase } from "../lib/supabaseClient";
import { Dashboard } from "../components/dashboard/Dashboard";

export function DashboardRoute() {
  const { session } = useSession(); // non-null guaranteed by RequireSession
  const navigate = useNavigate();

  return (
    <Dashboard
      accessToken={session!.access_token}
      onSignOut={() => supabase.auth.signOut()}
      onNotificationsClick={() => navigate("/notifications")}
    />
  );
}
