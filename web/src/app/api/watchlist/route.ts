import { NextResponse } from "next/server";
import { createClient, getSessionUser } from "@/lib/supabase/server";

export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json(
      { error: "Sign in required to save watchlist items" },
      { status: 401 },
    );
  }
  const supabase = await createClient();
  if (!supabase) {
    return NextResponse.json({ error: "Supabase not configured" }, { status: 503 });
  }
  const body = await request.json();
  const topic = body.topic as string;
  const primary_subject = body.primary_subject as string;
  if (!topic || !primary_subject) {
    return NextResponse.json({ error: "topic and primary_subject required" }, { status: 400 });
  }
  const { error } = await supabase.from("saved_topics").upsert(
    {
      user_id: user.id,
      topic,
      primary_subject,
    },
    { onConflict: "user_id,topic,primary_subject" },
  );
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json({ ok: true });
}

export async function GET() {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "Sign in required" }, { status: 401 });
  }
  const supabase = await createClient();
  if (!supabase) {
    return NextResponse.json({ items: [] });
  }
  const { data, error } = await supabase
    .from("saved_topics")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });
  if (error) {
    return NextResponse.json({ error: error.message }, { status: 400 });
  }
  return NextResponse.json({ items: data });
}
