import { useEffect, useState } from "react";
import { getStudentProfile, updateStandingTerm } from "../../lib/api";
import { OnboardingStepHeader } from "./OnboardingStepHeader";

interface StandingTermStepProps {
  accessToken: string;
  onContinue: () => void;
  onBack: () => void;
}

const CLASS_STANDINGS = [
  { value: "freshman", label: "Freshman" },
  { value: "sophomore", label: "Sophomore" },
  { value: "junior", label: "Junior" },
  { value: "senior", label: "Senior" },
];

const TERMS = [
  { value: "fall", label: "Fall" },
  { value: "spring", label: "Spring" },
];

export function StandingTermStep({ accessToken, onContinue, onBack }: StandingTermStepProps) {
  const [classStanding, setClassStanding] = useState<string | null>(null);
  const [currentTerm, setCurrentTerm] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStudentProfile(accessToken)
      .then((profile) => {
        setClassStanding(profile.class_standing);
        setCurrentTerm(profile.current_term);
      })
      .catch(() => setError("Couldn't load your previous selection — try refreshing."))
      .finally(() => setLoading(false));
  }, [accessToken]);

  async function handleContinue() {
    if (!classStanding || !currentTerm) return;
    setSaving(true);
    setError(null);
    try {
      await updateStandingTerm(accessToken, {
        class_standing: classStanding,
        current_term: currentTerm,
      });
      onContinue();
    } catch {
      setError("Couldn't save that — try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <OnboardingStepHeader step={2} onBack={onBack} />
      <h1 className="onboarding-heading">Where you're at</h1>
      <p className="onboarding-subtext">
        This tells the engine where to start building your schedule from.
      </p>

      <div className="pill-group">
        <p className="pill-group-label">Class standing</p>
        <div className="pill-group-options">
          {CLASS_STANDINGS.map((option) => (
            <button
              type="button"
              key={option.value}
              className={`pill pill--selectable ${
                classStanding === option.value ? "pill--selected" : ""
              }`}
              onClick={() => setClassStanding(option.value)}
              aria-pressed={classStanding === option.value}
              disabled={loading}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="pill-group">
        <p className="pill-group-label">Current term</p>
        <div className="pill-group-options">
          {TERMS.map((option) => (
            <button
              type="button"
              key={option.value}
              className={`pill pill--selectable ${
                currentTerm === option.value ? "pill--selected" : ""
              }`}
              onClick={() => setCurrentTerm(option.value)}
              aria-pressed={currentTerm === option.value}
              disabled={loading}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="auth-error">{error}</p>}

      <div className="onboarding-actions">
        <button
          type="button"
          className="btn-primary"
          onClick={handleContinue}
          disabled={!classStanding || !currentTerm || saving || loading}
        >
          {saving ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}
