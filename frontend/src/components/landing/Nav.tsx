interface NavProps {
  onSignIn: () => void;
  onGetStarted: () => void;
}

export function Nav({ onSignIn, onGetStarted }: NavProps) {
  return (
    <nav className="section-inner landing-nav">
      <p className="wordmark landing-nav-wordmark">koala</p>
      <div className="landing-nav-actions">
        <button type="button" className="btn-secondary" onClick={onSignIn}>
          Sign in
        </button>
        <button type="button" className="btn-primary" onClick={onGetStarted}>
          Get started
        </button>
      </div>
    </nav>
  );
}
