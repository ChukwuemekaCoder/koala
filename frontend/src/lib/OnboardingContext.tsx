import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useSession } from "./SessionContext";
import { getStudentProfile } from "./api";

interface OnboardingContextValue {
  onboardingComplete: boolean | null; // null = unknown/loading
  setOnboardingComplete: (value: boolean) => void;
}

const OnboardingContext = createContext<OnboardingContextValue | undefined>(undefined);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const { session } = useSession();
  const [onboardingComplete, setOnboardingComplete] = useState<boolean | null>(null);

  useEffect(() => {
    if (!session) {
      setOnboardingComplete(null);
      return;
    }
    getStudentProfile(session.access_token)
      .then((profile) => setOnboardingComplete(profile.onboarding_complete))
      .catch(() => setOnboardingComplete(true)); // fail open to the dashboard's own error state
  }, [session]);

  return (
    <OnboardingContext.Provider value={{ onboardingComplete, setOnboardingComplete }}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding(): OnboardingContextValue {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error("useOnboarding must be used within an OnboardingProvider");
  return ctx;
}
