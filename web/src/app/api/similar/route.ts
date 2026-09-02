import { NextResponse } from "next/server";
import { getQuestion } from "@/lib/data";
import { localSimilar } from "@/lib/local-similar";
import { createClient, getSessionUser } from "@/lib/supabase/server";

export const runtime = "nodejs";

function supabaseConfigured() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const qid = body.qid as string | undefined;
    const text = body.text as string | undefined;
    const k = Math.min(Number(body.k) || 10, 20);
    const filters = body.filters || {};

    const configured = supabaseConfigured();
    const allowLocal =
      process.env.ALLOW_LOCAL_EXPLORE === "1" || !configured;

    if (configured && !allowLocal) {
      const user = await getSessionUser();
      if (!user) {
        return NextResponse.json({ error: "Sign in required" }, { status: 401 });
      }
    }

    // Prefer live hybrid RPC when service has embeddings
    const supabase = await createClient();
    if (supabase && configured && (qid || text)) {
      let queryEmbedding: number[] | null = null;
      let queryText = text || "";
      let filterTopic: string | null = filters.topic || null;

      if (qid) {
        const { data: row } = await supabase
          .from("questions")
          .select(
            "qid,question_text,topic_clean,concept,embedding,subject_clean",
          )
          .eq("qid", qid)
          .maybeSingle();

        if (row) {
          queryText =
            queryText ||
            `${row.topic_clean || ""} ${row.concept || ""} ${row.question_text || ""}`;
          filterTopic = filterTopic || row.topic_clean;
          if (row.embedding) {
            queryEmbedding = row.embedding as number[];
          }
        }
      }

      if (!queryEmbedding && text && process.env.OPENAI_API_KEY) {
        const OpenAI = (await import("openai")).default;
        const oa = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
        const emb = await oa.embeddings.create({
          model: process.env.OPENAI_EMBED_MODEL || "text-embedding-3-small",
          input: text.slice(0, 8000),
        });
        queryEmbedding = emb.data[0].embedding;
        queryText = text;
      }

      if (queryEmbedding || queryText) {
        const { data, error } = await supabase.rpc("match_questions_hybrid", {
          query_embedding: queryEmbedding,
          query_text: queryText,
          match_count: k,
          exclude_qid: qid || null,
          filter_subject: filters.subject || null,
          filter_topic: null, // soft via same_topic flag; don't hard-filter
          year_min: filters.year_min ?? null,
          year_max: filters.year_max ?? null,
        });

        if (!error && data && data.length) {
          const user = await getSessionUser();
          if (user) {
            await supabase.from("explore_events").insert({
              user_id: user.id,
              qid: qid || null,
              query_text: queryText.slice(0, 500),
              result_count: data.length,
            });
          }
          return NextResponse.json({
            mode: queryEmbedding ? "hybrid-pgvector" : "fts",
            results: data.map((r: Record<string, unknown>) => ({
              ...r,
              same_topic:
                Boolean(filterTopic) && r.topic_clean === filterTopic,
            })),
          });
        }
      }
    }

    // Local sparse fallback
    const seed = qid ? getQuestion(qid) : null;
    if (!seed && !text) {
      return NextResponse.json({ error: "qid or text required" }, { status: 400 });
    }

    const results = localSimilar({
      qid,
      text,
      k,
      subject: filters.subject,
      topic: null,
      year_min: filters.year_min,
      year_max: filters.year_max,
    });

    return NextResponse.json({
      mode: "local-bm25",
      results,
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server error" },
      { status: 500 },
    );
  }
}
