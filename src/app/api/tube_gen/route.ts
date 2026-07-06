import OpenAI from "openai";

// Ensure Node.js runtime for compatibility with the OpenAI SDK
export const runtime = "nodejs";

type ContentType = "tutorial" | "vlog" | "review" | "explainer" | "listicle" | "story" | "podcast";
type Tone = "energetic" | "professional" | "casual" | "educational" | "inspirational" | "funny";
type VideoLength = "short" | "standard" | "long";

interface RequestBody {
  topic: string;
  audience?: string;
  tone?: Tone;
  contentType?: ContentType;
  length?: VideoLength;
  keywords?: string;
}

interface TitleIdea {
  title: string;
  reason: string;
}

interface ThumbnailIdea {
  concept: string;
  overlayText: string;
  visualStyle: string;
}

interface Chapter {
  timestamp: string;
  title: string;
}

interface TubeGenPackage {
  titles: TitleIdea[];
  hook: string;
  description: string;
  tags: string[];
  script: string;
  thumbnails: ThumbnailIdea[];
  chapters: Chapter[];
  cta: string;
}

const LENGTH_GUIDE: Record<VideoLength, string> = {
  short: "under 60 seconds (YouTube Short / Reel), punchy and fast-paced",
  standard: "8-12 minutes, the sweet spot for watch time and mid-roll ads",
  long: "20+ minutes, in-depth and comprehensive",
};

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race<T>([
    promise,
    new Promise<T>((_resolve, reject) =>
      setTimeout(() => reject(new Error(`OpenAI timeout after ${ms}ms`)), ms)
    ) as Promise<T>,
  ]);
}

// Deterministic, dependency-free fallback so the tool is usable without an API key.
function buildFallbackPackage(body: Required<Pick<RequestBody, "topic">> & RequestBody): TubeGenPackage {
  const { topic, audience, tone, contentType, keywords } = body;
  const aud = audience?.trim() || "your target audience";
  const kw = (keywords || topic)
    .split(/[,\n]/)
    .map((k) => k.trim().toLowerCase())
    .filter(Boolean);

  const baseTags = Array.from(
    new Set([
      ...kw,
      topic.toLowerCase(),
      contentType || "youtube",
      "how to",
      "tips",
      "guide",
      "2026",
      "tutorial",
      "beginners",
    ])
  ).slice(0, 15);

  return {
    titles: [
      { title: `${topic}: The Complete Guide (${new Date().getFullYear()})`, reason: "Keyword-front-loaded with a year for freshness signals." },
      { title: `I Tried ${topic} For 30 Days — Here's What Happened`, reason: "Curiosity + personal stakes drive strong click-through." },
      { title: `${topic} Explained in Under 10 Minutes`, reason: "Sets a clear, low-friction time expectation." },
      { title: `5 ${topic} Mistakes That Are Costing You (Fix These)`, reason: "Loss aversion + a listicle promise of quick wins." },
      { title: `The Truth About ${topic} Nobody Tells You`, reason: "Contrarian hook that implies insider knowledge." },
    ],
    hook: `What if everything you thought you knew about ${topic} was wrong? In the next few minutes I'm going to show ${aud} exactly how to get results — stick around, because the third point changes everything.`,
    description: `In this video we break down ${topic} for ${aud}. You'll learn the core ideas, the common mistakes to avoid, and a step-by-step approach you can apply today.

⏱️ Timestamps are in the chapters below.
🔔 Subscribe for more videos on ${topic}.
💬 Drop your questions in the comments and I'll answer them.

#${(kw[0] || topic).replace(/\s+/g, "")} #${(contentType || "youtube")} #tutorial`,
    tags: baseTags,
    script: `[HOOK — 0:00]
${`What if everything you knew about ${topic} was wrong?`} Open with a bold claim, then promise a clear payoff.

[INTRO — 0:15]
Introduce yourself briefly and state exactly what ${aud} will walk away with by the end. Tease the most valuable moment so viewers stay.

[SECTION 1 — The Foundation]
Explain the core concept behind ${topic} in plain language. Use one concrete example or analogy.

[SECTION 2 — The How]
Walk through the actual steps. Show, don't just tell. Add on-screen text for each step.

[SECTION 3 — The Mistakes]
Cover the 2-3 most common mistakes people make with ${topic} and how to avoid them.

[PAYOFF]
Deliver the promised "aha" moment from the hook.

[OUTRO / CTA]
Recap the single most important takeaway, then ask viewers to like, subscribe, and watch the next video.`,
    thumbnails: [
      { concept: `Close-up reaction face beside a bold graphic of ${topic}`, overlayText: `${topic.toUpperCase()}?!`, visualStyle: "High-contrast, saturated colors, big expressive face" },
      { concept: `Before / after split screen showing the result of ${topic}`, overlayText: "BEFORE vs AFTER", visualStyle: "Clean split layout with a bright divider line" },
      { concept: `A single striking object representing ${topic} with an arrow`, overlayText: "THIS CHANGES EVERYTHING", visualStyle: "Minimal background, one hero element, bold arrow" },
    ],
    chapters: [
      { timestamp: "0:00", title: "The hook" },
      { timestamp: "0:15", title: "What you'll learn" },
      { timestamp: "1:00", title: "The foundation" },
      { timestamp: "3:30", title: "Step-by-step" },
      { timestamp: "7:00", title: "Common mistakes" },
      { timestamp: "9:00", title: "Final takeaway" },
    ],
    cta: `If this helped you understand ${topic}, hit subscribe and check out the video on screen next — it's the perfect follow-up.`,
  };
}

export async function POST(req: Request) {
  try {
    const body: RequestBody = await req.json();
    const topic = (body.topic || "").trim();

    if (!topic) {
      return Response.json({ error: "A 'topic' is required." }, { status: 400 });
    }

    const tone: Tone = body.tone || "energetic";
    const contentType: ContentType = body.contentType || "explainer";
    const length: VideoLength = body.length || "standard";
    const audience = body.audience?.trim() || "a general YouTube audience";
    const keywords = body.keywords?.trim() || "";

    // Graceful fallback when no key is configured.
    if (!process.env.OPENAI_API_KEY) {
      console.warn("⚠️ OPENAI_API_KEY not set — returning template TubeGen package.");
      return Response.json({
        ...buildFallbackPackage({ topic, audience, tone, contentType, length, keywords }),
        _fallback: true,
      });
    }

    const client = new OpenAI({
      apiKey: process.env.OPENAI_API_KEY,
      baseURL: process.env.OPENAI_API_BASE || "https://api.openai.com/v1",
    });

    const system = `You are TubeGen, an elite YouTube growth strategist and scriptwriter. You generate complete, ready-to-publish content packages that maximize click-through rate, watch time, and SEO.

Return ONLY valid JSON matching this exact TypeScript type (no markdown, no commentary):
{
  "titles": { "title": string, "reason": string }[],   // exactly 5, each under 70 characters, using proven CTR patterns
  "hook": string,                                        // spoken opening 1-2 sentences that stop the scroll
  "description": string,                                 // 3-5 short paragraphs, includes a subscribe nudge and 3-5 hashtags
  "tags": string[],                                      // 12-15 lowercase SEO tags/keywords
  "script": string,                                      // a structured, sectioned script with [LABELS], appropriate to the requested length
  "thumbnails": { "concept": string, "overlayText": string, "visualStyle": string }[], // exactly 3
  "chapters": { "timestamp": string, "title": string }[], // 5-8, timestamps like "0:00"
  "cta": string                                          // a strong closing call-to-action
}`;

    const user = `Create a complete YouTube content package.

Topic: ${topic}
Target audience: ${audience}
Content type: ${contentType}
Tone: ${tone}
Target length: ${LENGTH_GUIDE[length]}
${keywords ? `Focus keywords to weave in: ${keywords}` : ""}

Make titles genuinely clickable but not clickbait-dishonest. Make the script practical and specific to the topic, matching the requested length and tone. Optimize tags and description for YouTube search.`;

    const completion = await withTimeout(
      client.chat.completions.create({
        model: "gpt-4o-mini",
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        temperature: 0.85,
        max_tokens: 2600,
      }),
      45000
    );

    const raw = completion.choices[0]?.message?.content || "{}";
    let parsed: TubeGenPackage;
    try {
      parsed = JSON.parse(raw);
    } catch {
      console.warn("⚠️ Failed to parse model JSON — falling back to template.");
      return Response.json({
        ...buildFallbackPackage({ topic, audience, tone, contentType, length, keywords }),
        _fallback: true,
      });
    }

    return Response.json({ ...parsed, _fallback: false });
  } catch (err) {
    console.error("💥 TubeGen API error:", err);
    return Response.json(
      { error: err instanceof Error ? err.message : "Something went wrong" },
      { status: 500 }
    );
  }
}
