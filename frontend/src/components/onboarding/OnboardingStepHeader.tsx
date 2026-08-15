interface OnboardingStepHeaderProps {
  step: 1 | 2 | 3;
  onBack?: () => void;
}

export function OnboardingStepHeader({ step, onBack }: OnboardingStepHeaderProps) {
  const progress = (
    <div className="onboarding-step-progress">
      <p className="onboarding-step-label">Step {step} of 3</p>
      <div className="onboarding-step-dots">
        {[1, 2, 3].map((i) => (
          <span
            key={i}
            className={`onboarding-step-dot ${
              i < step
                ? "onboarding-step-dot--completed"
                : i === step
                  ? "onboarding-step-dot--current"
                  : ""
            }`}
          />
        ))}
      </div>
    </div>
  );

  if (!onBack) {
    return progress;
  }

  return (
    <div className="onboarding-progress-row">
      <button type="button" className="onboarding-back" onClick={onBack}>
        Back
      </button>
      {progress}
    </div>
  );
}
