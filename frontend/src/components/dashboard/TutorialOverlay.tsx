import { useState } from "react";
import {
  IconCalendarStats,
  IconChartBar,
  IconArrowsExchange,
  IconFlag,
} from "@tabler/icons-react";
import { completeTutorial } from "../../lib/api";

interface Slide {
  icon: typeof IconCalendarStats;
  headline: string;
  body: string;
}

const SLIDES: Slide[] = [
  {
    icon: IconCalendarStats,
    headline: "Your plan, mapped out",
    body: "Every semester you need to graduate, laid out on one timeline — click any semester below to see its full schedule.",
  },
  {
    icon: IconChartBar,
    headline: "Track credits and graduation",
    body: "See what's done, in progress, and remaining, plus a graduation estimate that updates as your plan changes.",
  },
  {
    icon: IconArrowsExchange,
    headline: "Swap or add a course anytime",
    body: "Click a course on the calendar to change it, or add a new one from the semester header — the rest of your plan re-checks itself automatically.",
  },
  {
    icon: IconFlag,
    headline: "We'll flag anything worth a second look",
    body: "If an edit causes a real problem — a conflict, a delay — you'll see it flagged with a plain-language reason, right where it happened.",
  },
];

interface TutorialOverlayProps {
  accessToken: string;
  onDismiss: () => void;
}

export function TutorialOverlay({ accessToken, onDismiss }: TutorialOverlayProps) {
  const [slideIndex, setSlideIndex] = useState(0);
  const isLast = slideIndex === SLIDES.length - 1;
  const slide = SLIDES[slideIndex];
  const SlideIcon = slide.icon;

  function dismiss() {
    onDismiss();
    // Fire-and-forget: if this fails, has_completed_tutorial stays false
    // server-side, so the overlay just shows again on the next load —
    // the correct fallback rather than losing the signal silently, and
    // strictly better than persisting client-side (CLAUDE.md).
    completeTutorial(accessToken).catch(() => {});
  }

  function handleNext() {
    if (isLast) {
      dismiss();
    } else {
      setSlideIndex((i) => i + 1);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="card modal tutorial-modal">
        <div className="tutorial-icon">
          <SlideIcon size={26} stroke={1.75} />
        </div>

        <h2 className="tutorial-headline">{slide.headline}</h2>
        <p className="tutorial-body">{slide.body}</p>

        <div className="tutorial-dots">
          {SLIDES.map((_, i) => (
            <span
              key={i}
              className={`tutorial-dot ${
                i === slideIndex
                  ? "tutorial-dot--current"
                  : i < slideIndex
                    ? "tutorial-dot--completed"
                    : ""
              }`}
            />
          ))}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={dismiss}>
            Skip
          </button>
          <button type="button" className="btn-primary" onClick={handleNext}>
            {isLast ? "Got it" : "Next"}
          </button>
        </div>
      </div>
    </div>
  );
}
