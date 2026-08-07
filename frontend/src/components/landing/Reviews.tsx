import { StarRating } from "../StarRating";
import { useScrollReveal } from "../../lib/useScrollReveal";

const reviews = [
  {
    initials: "MT",
    name: "Maya T.",
    role: "Junior, Computer Science + Math minor",
    rating: 5,
    quote:
      "It caught a prerequisite I would've missed until it was too late. Saved me a whole semester.",
  },
  {
    initials: "JK",
    name: "Jordan K.",
    role: "Sophomore, Business",
    rating: 4.5,
    quote:
      "Seeing the actual cost of pushing back graduation made the trade-off obvious instead of abstract.",
  },
  {
    initials: "AR",
    name: "Alex R.",
    role: "Senior, Biology + Christian Ministries minor",
    rating: 5,
    quote:
      "Double major planning used to mean two spreadsheets. Now it's just one plan that accounts for both.",
  },
];

export function Reviews() {
  const containerRef = useScrollReveal<HTMLDivElement>();

  return (
    <section className="section section--white">
      <div className="section-inner">
        <span className="pill section-eyebrow">Reviews</span>
        <p className="problem-text" style={{ marginBottom: 4 }}>
          Sample reviews — koala doesn't have real users yet, so these are
          illustrative, not testimonials from actual students.
        </p>
        <div className="reviews-grid" ref={containerRef}>
          {reviews.map((review) => (
            <div className="card review-card reveal" key={review.name}>
              <div className="review-header">
                <span className="review-avatar">{review.initials}</span>
                <div>
                  <p className="review-name">{review.name}</p>
                  <p className="review-role">{review.role}</p>
                </div>
              </div>
              <StarRating rating={review.rating} />
              <p className="review-quote">"{review.quote}"</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
