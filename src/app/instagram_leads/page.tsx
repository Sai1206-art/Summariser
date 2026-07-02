"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";
import { Copy, Download, Instagram, Upload } from "lucide-react";
import { AILoader } from "@/components/ui/ai-loader";

type Lead = {
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

type Summary = {
  totalComments: number;
  hot: number;
  warm: number;
  cold: number;
  withContactInfo: number;
};

function ElegantShape({
  className,
  delay = 0,
  width = 400,
  height = 100,
  rotate = 0,
  gradient = "from-white/[0.08]",
}: {
  className?: string;
  delay?: number;
  width?: number;
  height?: number;
  rotate?: number;
  gradient?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -150, rotate: rotate - 15 }}
      animate={{ opacity: 1, y: 0, rotate: rotate }}
      transition={{ duration: 2.4, delay, ease: [0.23, 0.86, 0.39, 0.96], opacity: { duration: 1.2 } }}
      className={`absolute ${className}`}
    >
      <motion.div
        animate={{ y: [0, 15, 0] }}
        transition={{ duration: 12, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }}
        style={{ width, height }}
        className="relative"
      >
        <div
          className={`absolute inset-0 rounded-full bg-gradient-to-r to-transparent ${gradient} backdrop-blur-[2px] border-2 border-white/[0.15] shadow-[0_8px_32px_0_rgba(255,255,255,0.1)] after:absolute after:inset-0 after:rounded-full after:bg-[radial-gradient(circle_at_50%_50%,rgba(255,255,255,0.2),transparent_70%)]`}
        />
      </motion.div>
    </motion.div>
  );
}

const GRADE_STYLES: Record<Lead["grade"], string> = {
  hot: "bg-rose-500/20 text-rose-300 border-rose-500/40",
  warm: "bg-amber-500/20 text-amber-300 border-amber-500/40",
  cold: "bg-sky-500/15 text-sky-300/80 border-sky-500/30",
};

export default function InstagramLeadsPage() {
  const [mode, setMode] = useState<"graph" | "import">("graph");
  const [postUrl, setPostUrl] = useState("");
  const [importData, setImportData] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [gradeFilter, setGradeFilter] = useState<"all" | Lead["grade"]>("all");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const copyToClipboard = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (e) {
      console.error("Copy failed", e);
    }
  }, []);

  const handleFile = useCallback(async (file: File) => {
    const text = await file.text();
    setImportData(text);
  }, []);

  const runScrape = async () => {
    setLoading(true);
    setError(null);
    setLeads([]);
    setSummary(null);
    try {
      const payload = mode === "graph" ? { mode, postUrl } : { mode, data: importData };
      const res = await fetch("/api/instagram_leads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.error || `Request failed (${res.status})`);
        return;
      }
      setLeads(data.leads || []);
      setSummary(data.summary || null);
    } catch (e: any) {
      setError(e?.message || "Unexpected error");
    } finally {
      setLoading(false);
    }
  };

  const visibleLeads = useMemo(
    () => (gradeFilter === "all" ? leads : leads.filter((l) => l.grade === gradeFilter)),
    [leads, gradeFilter]
  );

  const downloadCsv = useCallback(() => {
    const esc = (v: string | number | null) => {
      const s = v == null ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const header = ["username", "profile_url", "comment", "grade", "score", "signals", "phones", "emails", "timestamp", "likes"];
    const lines = [header.join(",")];
    for (const l of visibleLeads) {
      lines.push([
        esc(l.username), esc(l.profileUrl), esc(l.comment), esc(l.grade), esc(l.score),
        esc(l.signals.join("; ")), esc(l.phones.join("; ")), esc(l.emails.join("; ")),
        esc(l.timestamp), esc(l.likeCount),
      ].join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "instagram_leads.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, [visibleLeads]);

  const canRun = mode === "graph" ? postUrl.trim().length > 0 : importData.trim().length > 0;

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#030303] pt-24 pb-16">
      <div className="absolute inset-0 bg-gradient-to-br from-rose-500/[0.05] via-transparent to-purple-500/[0.05] blur-3xl" />
      <div className="absolute inset-0 overflow-hidden">
        <ElegantShape delay={0.3} width={500} height={120} rotate={12} gradient="from-rose-500/[0.15]" className="left-[-10%] top-[10%]" />
        <ElegantShape delay={0.5} width={400} height={100} rotate={-15} gradient="from-purple-500/[0.15]" className="right-[-5%] top-[65%]" />
        <ElegantShape delay={0.4} width={250} height={70} rotate={-8} gradient="from-violet-500/[0.15]" className="left-[5%] bottom-[5%]" />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-6xl px-4 md:px-6">
        <div className="text-center mb-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.08] mb-6"
          >
            <Instagram className="h-4 w-4 text-rose-400" />
            <span className="text-sm text-white/60 tracking-wide">Instagram Comment Leads</span>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-4xl sm:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-white/70"
          >
            Turn comments into leads
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-4 text-white/40 max-w-2xl mx-auto"
          >
            Pull the comment section of a reel or post, detect buying intent, phone numbers and emails,
            and export a ranked lead list as CSV.
          </motion.p>
        </div>

        <div className="flex justify-center gap-2 mb-6">
          <Button
            variant={mode === "graph" ? "default" : "outline"}
            onClick={() => setMode("graph")}
            className={mode === "graph" ? "" : "bg-transparent text-white/70 border-white/20 hover:bg-white/10 hover:text-white"}
          >
            My post / reel (official API)
          </Button>
          <Button
            variant={mode === "import" ? "default" : "outline"}
            onClick={() => setMode("import")}
            className={mode === "import" ? "" : "bg-transparent text-white/70 border-white/20 hover:bg-white/10 hover:text-white"}
          >
            Import export (PhantomBuster / CSV / JSON)
          </Button>
        </div>

        <Card className="bg-white/[0.03] border-white/[0.08]">
          <CardContent className="p-6">
            {mode === "graph" ? (
              <div className="flex flex-col gap-3">
                <div className="flex flex-col sm:flex-row gap-3">
                  <Input
                    placeholder="https://www.instagram.com/reel/XXXXXXXXXXX/"
                    value={postUrl}
                    onChange={(e) => setPostUrl(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && canRun && !loading) runScrape(); }}
                    className="bg-white/[0.05] border-white/[0.1] text-white placeholder:text-white/30"
                  />
                  <Button onClick={runScrape} disabled={!canRun || loading} className="shrink-0">
                    {loading ? "Scraping…" : "Extract leads"}
                  </Button>
                </div>
                <p className="text-xs text-white/35">
                  Uses the official Instagram Graph API, so it works for posts and reels on your own connected
                  Business/Creator account. For someone else&apos;s post, use the Import tab.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <textarea
                  placeholder='Paste a PhantomBuster export here (JSON array or CSV with a "comment"/"text" column and a "username" column)…'
                  value={importData}
                  onChange={(e) => setImportData(e.target.value)}
                  rows={7}
                  className="w-full rounded-md bg-white/[0.05] border border-white/[0.1] text-white placeholder:text-white/30 p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-white/20"
                />
                <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.json,.txt"
                    className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
                  />
                  <Button
                    variant="outline"
                    onClick={() => fileInputRef.current?.click()}
                    className="bg-transparent text-white/70 border-white/20 hover:bg-white/10 hover:text-white"
                  >
                    <Upload className="h-4 w-4 mr-2" /> Upload CSV / JSON
                  </Button>
                  <Button onClick={runScrape} disabled={!canRun || loading}>
                    {loading ? "Analyzing…" : "Extract leads"}
                  </Button>
                  <p className="text-xs text-white/35">
                    Works with PhantomBuster &quot;Instagram Post Commenters&quot; exports or any CSV/JSON of comments.
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {loading && (
          <div className="flex justify-center mt-10">
            <AILoader />
          </div>
        )}

        {error && (
          <div className="mt-6 rounded-md border border-rose-500/40 bg-rose-500/10 text-rose-200 text-sm p-4">
            {error}
          </div>
        )}

        {summary && !loading && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-8">
            {[
              { label: "Comments", value: summary.totalComments },
              { label: "Hot leads", value: summary.hot },
              { label: "Warm leads", value: summary.warm },
              { label: "Cold", value: summary.cold },
              { label: "With contact info", value: summary.withContactInfo },
            ].map((s) => (
              <Card key={s.label} className="bg-white/[0.03] border-white/[0.08]">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-white">{s.value}</div>
                  <div className="text-xs text-white/40 mt-1">{s.label}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {leads.length > 0 && !loading && (
          <div className="mt-8">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex gap-2">
                {(["all", "hot", "warm", "cold"] as const).map((g) => (
                  <button
                    key={g}
                    onClick={() => setGradeFilter(g)}
                    className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                      gradeFilter === g
                        ? "bg-white text-black border-white"
                        : "bg-transparent text-white/60 border-white/20 hover:bg-white/10"
                    }`}
                  >
                    {g === "all" ? "All" : g.charAt(0).toUpperCase() + g.slice(1)}
                  </button>
                ))}
              </div>
              <Button
                variant="outline"
                onClick={downloadCsv}
                className="bg-transparent text-white/70 border-white/20 hover:bg-white/10 hover:text-white"
              >
                <Download className="h-4 w-4 mr-2" /> Download CSV ({visibleLeads.length})
              </Button>
            </div>

            <Card className="bg-white/[0.03] border-white/[0.08] overflow-hidden">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/[0.08] text-left text-white/50">
                        <th className="p-3 font-medium">
                          <div className="flex items-center gap-2">
                            <span>Username</span>
                            <button
                              onClick={() => copyToClipboard(visibleLeads.map((l) => l.username || "").filter(Boolean).join("\n"))}
                              className="p-1 rounded hover:bg-white/10 text-white/50 hover:text-white"
                              aria-label="Copy usernames"
                              title="Copy username column"
                            >
                              <Copy size={14} />
                            </button>
                          </div>
                        </th>
                        <th className="p-3 font-medium">Comment</th>
                        <th className="p-3 font-medium">Grade</th>
                        <th className="p-3 font-medium">Signals</th>
                        <th className="p-3 font-medium">
                          <div className="flex items-center gap-2">
                            <span>Contact</span>
                            <button
                              onClick={() => copyToClipboard(visibleLeads.flatMap((l) => [...l.phones, ...l.emails]).join("\n"))}
                              className="p-1 rounded hover:bg-white/10 text-white/50 hover:text-white"
                              aria-label="Copy contact info"
                              title="Copy contact column"
                            >
                              <Copy size={14} />
                            </button>
                          </div>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleLeads.map((l, i) => (
                        <tr key={i} className="border-b border-white/[0.05] align-top hover:bg-white/[0.02]">
                          <td className="p-3 whitespace-nowrap">
                            {l.username ? (
                              <a href={l.profileUrl ?? undefined} target="_blank" rel="noopener noreferrer" className="text-rose-300 hover:underline">
                                @{l.username.replace(/^@/, "")}
                              </a>
                            ) : (
                              <span className="text-white/30">unknown</span>
                            )}
                          </td>
                          <td className="p-3 text-white/80 max-w-md">{l.comment}</td>
                          <td className="p-3">
                            <span className={`inline-block px-2 py-0.5 rounded-full text-xs border ${GRADE_STYLES[l.grade]}`}>
                              {l.grade} · {l.score}
                            </span>
                          </td>
                          <td className="p-3 text-white/50 text-xs max-w-xs">{l.signals.join(", ") || "—"}</td>
                          <td className="p-3 text-white/80 text-xs whitespace-nowrap">
                            {[...l.phones, ...l.emails].join(", ") || <span className="text-white/25">—</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
