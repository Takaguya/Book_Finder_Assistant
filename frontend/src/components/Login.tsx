import { FirebaseError } from "firebase/app";
import { useEffect, useState } from "react";
import { getRedirectSignInError, signInWithGoogle } from "../lib/firebase";
import { BrandMark } from "./BrandMark";

// Turns Firebase's error codes into something a person can act on. Returns null when there's
// nothing to report, e.g. the person closed the Google window themselves.
function signInErrorMessage(err: unknown): string | null {
  const code = err instanceof FirebaseError ? err.code : "";
  switch (code) {
    case "auth/popup-closed-by-user":
    case "auth/cancelled-popup-request":
    case "auth/user-cancelled":
      return null;
    case "auth/network-request-failed":
      return "Couldn't reach Google. Check your connection and try again.";
    case "auth/user-disabled":
      return "This account has been disabled.";
    case "auth/unauthorized-domain":
      return "Sign-in isn't set up for this web address yet.";
    case "auth/operation-not-supported-in-this-environment":
    case "auth/web-storage-unsupported":
      return "This browser can't complete Google sign-in. Open the site in Safari or Chrome instead.";
    default:
      return "Sign-in didn't complete. Try again.";
  }
}

// Decorative shelf on the sign-in screen: [height %, width px, colour var, lean deg]
const SPINES: [number, number, string, number][] = [
  [78, 26, "--cloth", 0],
  [92, 34, "--stamp", 0],
  [70, 22, "--brass", 0],
  [86, 30, "--oxblood", 0],
  [96, 38, "--navy", 0],
  [74, 24, "--cloth-2", 0],
  [88, 28, "--stamp", 0],
  [66, 30, "--oxblood", -9],
];

export function Login() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Coming back from a redirect sign-in that failed: show why.
  useEffect(() => {
    let cancelled = false;
    getRedirectSignInError().then((err) => {
      if (!cancelled && err) setError(signInErrorMessage(err));
    });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSignIn() {
    setError(null);
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch (err) {
      console.error("Google sign-in failed", err);
      setError(signInErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-screen">
      <div className="login-inner">
        <div className="login-brand">
          <BrandMark size={26} />
          <span>Book Finder</span>
        </div>

        <h1 className="login-title">Tell it what you loved. It finds what to read next.</h1>
        <p className="login-body">
          Describe a mood, a favourite book, or a subject, and get real books you can open and start
          reading.
        </p>

        <div className="login-shelf" aria-hidden="true">
          {SPINES.map(([h, w, color, lean], i) => (
            <span
              key={i}
              className="spine"
              style={{
                height: `${h}%`,
                width: w,
                background: `var(${color})`,
                transform: lean ? `rotate(${lean}deg)` : undefined,
                animationDelay: `${i * 55}ms`,
              }}
            />
          ))}
        </div>

        <button className="google-btn" onClick={handleSignIn} disabled={loading}>
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
            <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
            <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
            <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
          </svg>
          {loading ? "Signing in…" : "Sign in with Google"}
        </button>
        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}
