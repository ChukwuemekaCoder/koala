import { useNavigate, useSearchParams } from "react-router-dom";
import { AuthCard } from "../components/AuthCard";

export function AuthRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") === "signup" ? "signup" : "signin";

  return (
    <div className="auth-page">
      <AuthCard initialTab={initialTab} onBack={() => navigate("/")} />
    </div>
  );
}
