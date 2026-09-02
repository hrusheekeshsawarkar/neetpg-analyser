"use client";

import { createClient, isSupabaseConfigured } from "@/lib/supabase/client";
import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";

export function useUser() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const configured = isSupabaseConfigured();

  useEffect(() => {
    if (!configured) {
      setLoading(false);
      return;
    }
    const supabase = createClient();
    if (!supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getUser().then(({ data }) => {
      setUser(data.user ?? null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, [configured]);

  return { user, loading, configured };
}

export async function signInWithGoogle() {
  const supabase = createClient();
  if (!supabase) {
    alert("Supabase is not configured. Add NEXT_PUBLIC_SUPABASE_URL and ANON_KEY.");
    return;
  }
  await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });
}

export async function signOut() {
  const supabase = createClient();
  if (!supabase) return;
  await supabase.auth.signOut();
}
