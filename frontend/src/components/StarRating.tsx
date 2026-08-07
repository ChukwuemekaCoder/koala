interface StarRatingProps {
  rating: number;
  starCount?: number;
}

export function StarRating({ rating, starCount = 5 }: StarRatingProps) {
  const pct = Math.max(0, Math.min(100, (rating / starCount) * 100));
  const stars = "★".repeat(starCount);

  return (
    <span
      className="star-rating"
      role="img"
      aria-label={`${rating} out of ${starCount} stars`}
    >
      <span className="star-rating-bg" aria-hidden="true">
        {stars}
      </span>
      <span
        className="star-rating-fg"
        aria-hidden="true"
        style={{ width: `${pct}%` }}
      >
        {stars}
      </span>
    </span>
  );
}
