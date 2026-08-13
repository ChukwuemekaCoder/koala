import { useState } from "react";
import { optimizeSchedule } from "../../lib/api";
import { ProgramSelectStep } from "./ProgramSelectStep";
import { StandingTermStep } from "./StandingTermStep";
import { CourseHistoryStep } from "./CourseHistoryStep";

interface OnboardingProps {
  accessToken: string;
  onComplete: () => void;
}

export function Onboarding({ accessToken, onComplete }: OnboardingProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [finishing, setFinishing] = useState(false);

  async function handleCourseHistoryDone() {
    setFinishing(true);
    try {
      await optimizeSchedule(accessToken);
    } catch {
      // Onboarding itself already succeeded (progress was confirmed and
      // onboarding_completed_at is set) — the dashboard re-attempts
      // optimize on load if the plan comes back empty, so a failure
      // here just falls through to that retry instead of stalling here.
    } finally {
      onComplete();
    }
  }

  return (
    <div className="onboarding-page">
      <div className="card onboarding-card">
        <p className="onboarding-wordmark">koala</p>
        {finishing ? (
          <p className="onboarding-subtext">Generating your first schedule…</p>
        ) : (
          <>
            {step === 1 && (
              <ProgramSelectStep accessToken={accessToken} onContinue={() => setStep(2)} />
            )}
            {step === 2 && (
              <StandingTermStep accessToken={accessToken} onContinue={() => setStep(3)} />
            )}
            {step === 3 && (
              <CourseHistoryStep
                accessToken={accessToken}
                onComplete={handleCourseHistoryDone}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
