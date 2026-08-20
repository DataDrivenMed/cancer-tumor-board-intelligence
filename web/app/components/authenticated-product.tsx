"use client";

import { useEffect, useState } from "react";

type Session = {
  authenticated: boolean;
  mode: "local" | "oidc";
  user: { name?: string; email?: string; organization?: string } | null;
};

export function AuthenticatedProduct({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    fetch("/api/auth/session", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Session check failed.");
        return response.json() as Promise<Session>;
      })
      .then((value) => { if (active) setSession(value); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, []);

  if (!session && !failed) {
    return <main className="access-gate" role="status"><div className="access-mark" aria-hidden="true">TB</div><h1>Opening your secure workspace</h1><p>Confirming the authenticated product session…</p></main>;
  }
  if (failed) {
    return <main className="access-gate"><div className="access-mark" aria-hidden="true">TB</div><h1>The secure session could not be checked</h1><p>Refresh the page. If the problem continues, contact the product administrator.</p><button type="button" onClick={() => window.location.reload()}>Retry</button></main>;
  }
  if (!session?.authenticated) {
    return (
      <main className="access-gate">
        <div className="access-mark" aria-hidden="true">TB</div>
        <p className="micro-label">Private clinical intelligence workspace</p>
        <h1>Sign in to Tumor Board Intelligence</h1>
        <p>Your cases, evidence decisions, workflow results, and human judgments remain inside your authorized workspace.</p>
        <a className="access-button" href="/api/auth/login">Sign in securely</a>
        <small>Only properly de-identified clinical information may be entered.</small>
      </main>
    );
  }
  return <>{children}</>;
}
