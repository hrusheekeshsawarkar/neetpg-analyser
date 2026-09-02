import { NextResponse } from "next/server";
import { loadPackMarkdown } from "@/lib/data";
import { createClient, getSessionUser } from "@/lib/supabase/server";

export async function GET(
  _request: Request,
  context: { params: Promise<{ subject: string }> },
) {
  const { subject: slug } = await context.params;
  const configured = Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );

  if (configured) {
    const user = await getSessionUser();
    if (!user) {
      return NextResponse.json({ error: "Sign in required" }, { status: 401 });
    }
    const supabase = await createClient();
    if (supabase) {
      await supabase.from("pack_downloads").insert({
        user_id: user.id,
        subject_slug: slug,
      });
      const { data } = await supabase
        .from("subject_packs")
        .select("markdown,subject_name")
        .eq("subject_slug", slug)
        .maybeSingle();
      if (data?.markdown) {
        return new NextResponse(data.markdown, {
          headers: {
            "Content-Type": "text/markdown; charset=utf-8",
            "Content-Disposition": `attachment; filename="${slug}-revision-pack.md"`,
          },
        });
      }
    }
  }

  // Local / unauthenticated fallback for offline demo (still serves file; UI gates soft)
  const md = loadPackMarkdown(slug);
  if (!md) {
    return NextResponse.json({ error: "Pack not found" }, { status: 404 });
  }
  if (configured) {
    // already returned 401 above if no user
  }
  return new NextResponse(md, {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": `attachment; filename="${slug}-revision-pack.md"`,
    },
  });
}
