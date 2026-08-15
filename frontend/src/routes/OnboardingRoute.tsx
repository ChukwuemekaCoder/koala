import { useNavigate } from "react-router-dom";
import { useSession } from "../lib/SessionContext";
import { useOnboarding } from "../lib/OnboardingContext";
import { Onboarding } from "../components/onboarding/Onboarding";

export function OnboardingRoute() {
  const { session } = useSession(); // non-null guaranteed by RequireSession
  const { setOnboardingComplete } = useOnboarding();
  const navigate = useNavigate();

  return (
    <Onboarding
      accessToken={session!.access_token}
      onComplete={() => {
        setOnboardingComplete(true);
        navigate("/dashboard", { replace: true });
      }}
    />
  );
}
