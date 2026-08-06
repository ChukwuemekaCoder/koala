import { useState, type FormEvent } from "react";
import { supabase } from "../lib/supabaseClient";
import { createStudentProfile } from "../lib/api";

type Tab = "signin" | "signup";
type SignupStep = "form" | "verify";

const ORU_EMAIL_RE = /^[^@\s]+@oru\.edu$/i;

function mapAuthError(message: string): string {
  if (/invalid login credentials/i.test(message)) {
    return "That email or password doesn't match our records.";
  }
  if (/user already registered/i.test(message)) {
    return "An account with that email already exists — sign in instead.";
  }
  if (/password should be at least/i.test(message)) {
    return message.replace(/\.$/, "") + ".";
  }
  return message;
}

export function AuthCard() {
  const [tab, setTab] = useState<Tab>("signin");

  // Sign in state
  const [signinEmail, setSigninEmail] = useState("");
  const [signinPassword, setSigninPassword] = useState("");

  // Sign up state
  const [signupStep, setSignupStep] = useState<SignupStep>("form");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupEmailTouched, setSignupEmailTouched] = useState(false);
  const [signupPassword, setSignupPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signupEmailValid = ORU_EMAIL_RE.test(signupEmail);

  function switchTab(next: Tab) {
    setTab(next);
    setError(null);
  }

  async function handleSignIn(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email: signinEmail,
      password: signinPassword,
    });
    setLoading(false);
    if (error) setError(mapAuthError(error.message));
  }

  async function handleSignUp(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!signupEmailValid) {
      setSignupEmailTouched(true);
      return;
    }
    if (signupPassword !== confirmPassword) {
      setError("Those passwords don't match — check and try again.");
      return;
    }

    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email: signupEmail,
      password: signupPassword,
      options: {
        data: { first_name: firstName, last_name: lastName },
      },
    });
    setLoading(false);

    if (error) {
      setError(mapAuthError(error.message));
      return;
    }
    if (!data.session) {
      setSignupStep("verify");
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { data, error } = await supabase.auth.verifyOtp({
      email: signupEmail,
      token: code,
      type: "signup",
    });
    if (error) {
      setLoading(false);
      setError(mapAuthError(error.message));
      return;
    }

    // First sign-in after verification: create the student profile row.
    // Session existing already proves auth succeeded, so a failure here
    // is non-blocking — the account exists either way.
    if (data.session) {
      try {
        await createStudentProfile(
          data.session.access_token,
          firstName,
          lastName,
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    }
    setLoading(false);
  }

  async function handleResend() {
    setError(null);
    const { error } = await supabase.auth.resend({
      type: "signup",
      email: signupEmail,
    });
    if (error) setError(mapAuthError(error.message));
  }

  if (tab === "signup" && signupStep === "verify") {
    return (
      <div className="auth-card">
        <p className="auth-wordmark">koala</p>
        <h1 className="auth-verify-heading">Check your email</h1>
        <p className="auth-verify-subtext">
          We sent a code to <strong>{signupEmail}</strong>
        </p>
        <form className="auth-form" onSubmit={handleVerify}>
          <div className="auth-field">
            <label htmlFor="code">Verification code</label>
            <input
              id="code"
              className="auth-code-input"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              required
            />
          </div>
          {error && <p className="auth-error">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading}>
            Verify email
          </button>
          <button
            type="button"
            className="auth-ghost"
            onClick={handleResend}
            disabled={loading}
          >
            Resend code
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="auth-card">
      <p className="auth-wordmark">koala</p>

      <div className="auth-tabs">
        <button
          type="button"
          className={`auth-tab ${tab === "signin" ? "auth-tab--active" : ""}`}
          onClick={() => switchTab("signin")}
        >
          Sign in
        </button>
        <button
          type="button"
          className={`auth-tab ${tab === "signup" ? "auth-tab--active" : ""}`}
          onClick={() => switchTab("signup")}
        >
          Create account
        </button>
      </div>

      {tab === "signin" ? (
        <form className="auth-form" onSubmit={handleSignIn}>
          <div className="auth-field">
            <label htmlFor="signin-email">School email</label>
            <input
              id="signin-email"
              type="email"
              autoComplete="email"
              value={signinEmail}
              onChange={(e) => setSigninEmail(e.target.value)}
              required
            />
          </div>
          <div className="auth-field">
            <label htmlFor="signin-password">Password</label>
            <input
              id="signin-password"
              type="password"
              autoComplete="current-password"
              value={signinPassword}
              onChange={(e) => setSigninPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="auth-error">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading}>
            Sign in
          </button>
        </form>
      ) : (
        <form className="auth-form" onSubmit={handleSignUp}>
          <div className="auth-field-row">
            <div className="auth-field">
              <label htmlFor="first-name">First name</label>
              <input
                id="first-name"
                autoComplete="given-name"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
            <div className="auth-field">
              <label htmlFor="last-name">Last name</label>
              <input
                id="last-name"
                autoComplete="family-name"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="auth-field">
            <label htmlFor="school">School</label>
            <input id="school" value="Oral Roberts University" disabled />
          </div>
          <div className="auth-field">
            <label htmlFor="signup-email">School email</label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              value={signupEmail}
              onChange={(e) => setSignupEmail(e.target.value)}
              onBlur={() => setSignupEmailTouched(true)}
              required
            />
            {signupEmailTouched && !signupEmailValid && (
              <p className="auth-hint">Please use your ORU email</p>
            )}
          </div>
          <div className="auth-field">
            <label htmlFor="signup-password">Password</label>
            <input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              value={signupPassword}
              onChange={(e) => setSignupPassword(e.target.value)}
              required
            />
          </div>
          <div className="auth-field">
            <label htmlFor="confirm-password">Confirm password</label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="auth-error">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading}>
            Create account
          </button>
        </form>
      )}
    </div>
  );
}
