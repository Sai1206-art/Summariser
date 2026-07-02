import { NextResponse } from "next/server";
export const runtime = 'nodejs';

const DEBUG = process.env.DEBUG_INSTAGRAM === '1';
const GRAPH_BASE = "https://graph.facebook.com/v21.0";

// ---------- Lead extraction ----------

const INTENT_KEYWORDS: { pattern: RegExp; label: string; weight: number }[] = [
  { pattern: /\b(price|pricing|cost|rate|rates|budget)\b/i, label: "Asked price", weight: 3 },
  { pattern: /\b(interested|i am in|i'm in|count me in)\b/i, label: "Expressed interest", weight: 3 },
  { pattern: /\b(dm|dm me|inbox|pm me|message me)\b/i, label: "Asked for DM", weight: 3 },
  { pattern: /\b(whatsapp|whats app|wa me)\b/i, label: "Asked for WhatsApp", weight: 3 },
  { pattern: /\b(call me|contact me|reach me|my number)\b/i, label: "Asked for call", weight: 3 },
  { pattern: /\b(brochure|floor ?plan|payment plan|site visit|possession)\b/i, label: "Asked for details", weight: 3 },
  { pattern: /\b(details|more info|information|know more|tell me more)\b/i, label: "Asked for info", weight: 2 },
  { pattern: /\b(location|address|where is (this|it)|which (city|area|sector))\b/i, label: "Asked location", weight: 2 },
  { pattern: /\b(book|booking|buy|purchase|invest|investment)\b/i, label: "Buying intent", weight: 2 },
  { pattern: /\b(emi|loan|finance|down payment)\b/i, label: "Financing question", weight: 2 },
  { pattern: /\b(available|availability|units? left|sold out)\b/i, label: "Asked availability", weight: 2 },
  { pattern: /\?/, label: "Asked a question", weight: 1 },
];

const EMAIL_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const PHONE_CANDIDATE_RE = /\+?\d[\d\s\-().]{7,}\d/g;

function extractPhones(text: string): string[] {
  const found = text.match(PHONE_CANDIDATE_RE) || [];
  const phones: string[] = [];
  for (const raw of found) {
    const digits = raw.replace(/\D/g, "");
    if (digits.length >= 10 && digits.length <= 13) phones.push(raw.trim());
  }
  return Array.from(new Set(phones));
}

export type Lead = {
  username: string | null;
  profileUrl: string | null;
  comment: string;
  timestamp: string | null;
  likeCount: number | null;
  signals: string[];
  phones: string[];
  emails: string[];
  score: number;
  grade: "hot" | "warm" | "cold";
};

function analyzeComment(username: string | null, text: string, timestamp: string | null, likeCount: number | null): Lead {
  const signals: string[] = [];
  let score = 0;
  for (const kw of INTENT_KEYWORDS) {
    if (kw.pattern.test(text)) {
      signals.push(kw.label);
      score += kw.weight;
    }
  }
  const phones = extractPhones(text);
  const emails = Array.from(new Set(text.match(EMAIL_RE) || []));
  if (phones.length > 0) { signals.push("Shared phone number"); score += 5; }
  if (emails.length > 0) { signals.push("Shared email"); score += 5; }

  const grade: Lead["grade"] = score >= 5 ? "hot" : score >= 2 ? "warm" : "cold";
  return {
    username,
    profileUrl: username ? `https://www.instagram.com/${username.replace(/^@/, "")}/` : null,
    comment: text,
    timestamp,
    likeCount,
    signals,
    phones,
    emails,
    score,
    grade,
  };
}

// ---------- Instagram Graph API (own posts/reels) ----------

function extractShortcode(postUrl: string): string | null {
  const m = postUrl.match(/(?:reels?|p|tv)\/([A-Za-z0-9_-]+)/);
  return m ? m[1] : null;
}

async function graphGet(path: string, params: Record<string, string>, accessToken: string) {
  const url = new URL(`${GRAPH_BASE}/${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
  url.searchParams.set("access_token", accessToken);
  const res = await fetch(url.toString(), { cache: "no-store" });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = body?.error?.message || `Graph API error ${res.status}`;
    throw new Error(msg);
  }
  return body;
}

async function resolveIgUserId(accessToken: string): Promise<string> {
  const configured = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;
  if (configured) return configured;
  const data = await graphGet("me/accounts", { fields: "instagram_business_account,name" }, accessToken);
  const withIg = (data?.data || []).find((p: any) => p?.instagram_business_account?.id);
  if (!withIg) throw new Error("No Instagram Business account linked to this access token. Set INSTAGRAM_BUSINESS_ACCOUNT_ID or link an IG Business/Creator account to your Facebook Page.");
  return withIg.instagram_business_account.id;
}

async function findMediaIdByShortcode(igUserId: string, shortcode: string, accessToken: string): Promise<string | null> {
  let after: string | null = null;
  // Scan up to 300 recent posts for the matching permalink
  for (let page = 0; page < 6; page++) {
    const params: Record<string, string> = { fields: "id,permalink", limit: "50" };
    if (after) params.after = after;
    const data = await graphGet(`${igUserId}/media`, params, accessToken);
    for (const media of data?.data || []) {
      if (typeof media?.permalink === "string" && media.permalink.includes(`/${shortcode}/`)) return media.id;
    }
    after = data?.paging?.cursors?.after || null;
    if (!after) break;
  }
  return null;
}

async function fetchAllComments(mediaId: string, accessToken: string) {
  const comments: { username: string | null; text: string; timestamp: string | null; likeCount: number | null }[] = [];
  let after: string | null = null;
  for (let page = 0; page < 20; page++) {
    const params: Record<string, string> = {
      fields: "id,text,username,timestamp,like_count,replies{id,text,username,timestamp,like_count}",
      limit: "50",
    };
    if (after) params.after = after;
    const data = await graphGet(`${mediaId}/comments`, params, accessToken);
    for (const c of data?.data || []) {
      if (c?.text) comments.push({ username: c.username ?? null, text: c.text, timestamp: c.timestamp ?? null, likeCount: c.like_count ?? null });
      for (const r of c?.replies?.data || []) {
        if (r?.text) comments.push({ username: r.username ?? null, text: r.text, timestamp: r.timestamp ?? null, likeCount: r.like_count ?? null });
      }
    }
    after = data?.paging?.cursors?.after || null;
    if (!after) break;
  }
  return comments;
}

// ---------- Import mode (PhantomBuster / CSV / JSON exports) ----------

function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else inQuotes = false;
      } else field += ch;
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field); field = "";
    } else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = "";
      if (row.some((f) => f.trim() !== "")) rows.push(row);
      row = [];
    } else field += ch;
  }
  row.push(field);
  if (row.some((f) => f.trim() !== "")) rows.push(row);
  if (rows.length < 2) return [];
  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((r) => {
    const obj: Record<string, string> = {};
    headers.forEach((h, idx) => { obj[h] = r[idx] ?? ""; });
    return obj;
  });
}

function pickField(row: Record<string, any>, candidates: string[]): string | null {
  const keys = Object.keys(row);
  for (const cand of candidates) {
    const key = keys.find((k) => k.toLowerCase() === cand.toLowerCase());
    if (key && row[key] != null && String(row[key]).trim() !== "") return String(row[key]).trim();
  }
  return null;
}

function normalizeImportedRows(rows: Record<string, any>[]) {
  return rows
    .map((row) => {
      const text = pickField(row, ["comment", "commentText", "comment_text", "text", "message", "content", "body"]);
      if (!text) return null;
      const username = pickField(row, ["username", "handle", "userName", "user", "author", "ownerUsername", "profileName", "name"]);
      const timestamp = pickField(row, ["timestamp", "commentDate", "date", "publishedAt", "created_at", "createdAt", "time"]);
      const likesRaw = pickField(row, ["likeCount", "likesCount", "like_count", "likes"]);
      const likeCount = likesRaw != null && !Number.isNaN(Number(likesRaw)) ? Number(likesRaw) : null;
      return { username, text, timestamp, likeCount };
    })
    .filter((r): r is { username: string | null; text: string; timestamp: string | null; likeCount: number | null } => r !== null);
}

// ---------- Route ----------

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const mode = body?.mode;

    let rawComments: { username: string | null; text: string; timestamp: string | null; likeCount: number | null }[] = [];
    let source = "";

    if (mode === "graph") {
      const accessToken = process.env.INSTAGRAM_ACCESS_TOKEN;
      if (!accessToken) {
        return NextResponse.json(
          { error: "Missing INSTAGRAM_ACCESS_TOKEN in environment. Add a Meta Graph API token with instagram_basic + instagram_manage_comments permissions. Note: the Graph API only returns comments for posts/reels on your own IG Business/Creator account — for other accounts' posts use the Import tab." },
          { status: 500 }
        );
      }
      const postUrl = typeof body?.postUrl === "string" ? body.postUrl.trim() : "";
      if (!postUrl) {
        return NextResponse.json({ error: "postUrl is required" }, { status: 400 });
      }

      let mediaId: string | null = null;
      if (/^\d+$/.test(postUrl)) {
        mediaId = postUrl; // allow pasting a raw media ID
      } else {
        const shortcode = extractShortcode(postUrl);
        if (!shortcode) {
          return NextResponse.json({ error: "Could not parse that URL. Paste a link like https://www.instagram.com/reel/XXXX/ or https://www.instagram.com/p/XXXX/" }, { status: 400 });
        }
        const igUserId = await resolveIgUserId(accessToken);
        mediaId = await findMediaIdByShortcode(igUserId, shortcode, accessToken);
        if (!mediaId) {
          return NextResponse.json({ error: "That post was not found in your account's recent media (last ~300 posts). The Graph API can only read comments on your own account's posts — for someone else's post, use the Import tab with a PhantomBuster/CSV export." }, { status: 404 });
        }
      }
      rawComments = await fetchAllComments(mediaId, accessToken);
      source = "instagram_graph_api";
    } else if (mode === "import") {
      const data = body?.data;
      if (typeof data !== "string" || data.trim() === "") {
        return NextResponse.json({ error: "data is required: paste the JSON or CSV contents of your export" }, { status: 400 });
      }
      let rows: Record<string, any>[] = [];
      const trimmed = data.trim();
      if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
        let parsed: any;
        try { parsed = JSON.parse(trimmed); } catch { return NextResponse.json({ error: "Invalid JSON. Paste the raw export contents." }, { status: 400 }); }
        rows = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.data) ? parsed.data : Array.isArray(parsed?.results) ? parsed.results : [];
      } else {
        rows = parseCsv(trimmed);
      }
      if (rows.length === 0) {
        return NextResponse.json({ error: "No rows found in the export. Expected a JSON array or a CSV with headers." }, { status: 400 });
      }
      rawComments = normalizeImportedRows(rows);
      if (rawComments.length === 0) {
        return NextResponse.json({ error: "Could not find a comment text column. Expected one of: comment, commentText, text, message, content." }, { status: 400 });
      }
      source = "import";
    } else {
      return NextResponse.json({ error: "mode must be 'graph' or 'import'" }, { status: 400 });
    }

    const leads = rawComments
      .map((c) => analyzeComment(c.username, c.text, c.timestamp, c.likeCount))
      .sort((a, b) => b.score - a.score);

    const summary = {
      totalComments: rawComments.length,
      hot: leads.filter((l) => l.grade === "hot").length,
      warm: leads.filter((l) => l.grade === "warm").length,
      cold: leads.filter((l) => l.grade === "cold").length,
      withContactInfo: leads.filter((l) => l.phones.length > 0 || l.emails.length > 0).length,
    };

    return NextResponse.json({ source, summary, leads });
  } catch (error: any) {
    if (DEBUG) console.error("Instagram leads error:", error);
    return NextResponse.json({ error: error?.message ?? "Unexpected error" }, { status: 500 });
  }
}
