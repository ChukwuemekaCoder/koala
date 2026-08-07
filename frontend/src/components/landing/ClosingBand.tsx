interface ClosingBandProps {
  onGetStarted: () => void;
}

export function ClosingBand({ onGetStarted }: ClosingBandProps) {
  return (
    <section className="section closing-band">
      <div className="section-inner">
        <h2 className="two-line-heading closing-band-heading">
          <span className="two-line-heading-1">Stop guessing your way</span>
          <br />
          <span className="two-line-heading-2">to graduation</span>
        </h2>
        <button type="button" className="btn-primary" onClick={onGetStarted}>
          Get started
        </button>
      </div>
    </section>
  );
}
