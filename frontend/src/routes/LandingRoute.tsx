import { useNavigate } from "react-router-dom";
import { Landing } from "../components/landing/Landing";

export function LandingRoute() {
  const navigate = useNavigate();
  return (
    <Landing
      onSignIn={() => navigate("/auth?tab=signin")}
      onGetStarted={() => navigate("/auth?tab=signup")}
    />
  );
}
