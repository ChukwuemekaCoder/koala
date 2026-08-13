import { useState } from "react";
import { updateStandingTerm } from "../../lib/api";

interface StandingTermStepProps {
  accessToken: string;
  onContinue: () => void;
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

export function StandingTermStep({ accessToken, onContinue }: StandingTermStepProps) {
  const [classStanding, setClassStanding] = useState<string | null>(null);
  const [currentTerm, setCurrentTerm] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      <p className="onboarding-step-label">Step 2 of 3</p>
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
          disabled={!classStanding || !currentTerm || saving}
        >
          {saving ? "Saving…" : "Continue"}
        </button>
      </div>
    </div>
  );
}
