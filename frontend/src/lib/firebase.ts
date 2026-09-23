import { FirebaseError, initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  getAuth,
  getRedirectResult,
  signInWithPopup,
  signInWithRedirect,
  signOut,
} from "firebase/auth";

// Google sign-in finishes on `https://<authDomain>/__/auth/handler`. When that's a different site
// from the page (firebaseapp.com while the app runs on web.app), phone browsers keep the two
// sites' storage apart, the result never reaches the page, and a completed sign-in fails with
// auth/popup-closed-by-user. Firebase Hosting serves the handler on each of the project's hosting
// domains, so there the page's own domain is used. Each such domain's handler must be listed
// under "Authorized redirect URIs" on the project's Google OAuth client.
const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID;
const hostingDomains = [`${projectId}.web.app`, `${projectId}.firebaseapp.com`];
const authDomain = hostingDomains.includes(window.location.hostname)
  ? window.location.hostname
  : import.meta.env.VITE_FIREBASE_AUTH_DOMAIN;

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain,
  projectId,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

const googleProvider = new GoogleAuthProvider();

// Touch-screen devices get a full-page redirect: popups there open as separate tabs that are easy
// to lose, and some in-app browsers block them. Computers keep the popup, falling back to a
// redirect if the browser blocks it.
const prefersRedirect = window.matchMedia("(pointer: coarse)").matches;

export async function signInWithGoogle(): Promise<void> {
  if (prefersRedirect) {
    await signInWithRedirect(auth, googleProvider);
    return;
  }
  try {
    await signInWithPopup(auth, googleProvider);
  } catch (err) {
    if (err instanceof FirebaseError && err.code === "auth/popup-blocked") {
      await signInWithRedirect(auth, googleProvider);
      return;
    }
    throw err;
  }
}

// After a redirect sign-in, Firebase signs the user in by itself when the page loads. This only
// reports an error from that attempt (e.g. a disabled account) so the sign-in screen can show it.
export async function getRedirectSignInError(): Promise<unknown> {
  try {
    await getRedirectResult(auth);
    return null;
  } catch (err) {
    return err;
  }
}

export async function signOutUser() {
  return signOut(auth);
}
