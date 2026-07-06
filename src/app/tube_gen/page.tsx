"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";
import { AILoader } from "@/components/ui/ai-loader";

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
  _fallback?: boolean;
}

const TONES = ["energetic", "professional", "casual", "educational", "inspirational", "funny"] as const;
const CONTENT_TYPES = ["explainer", "tutorial", "vlog", "review", "listicle", "story", "podcast"] as const;
const LENGTHS = [
  { value: "short", label: "Short (<60s)" },
  { value: "standard", label: "Standard (8-12m)" },
  { value: "long", label: "Long (20m+)" },
] as const;

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
      animate={{ opacity: 1, y: 0, rotate }}
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

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <button
      onClick={handleCopy}
      className="text-xs px-3 py-1 rounded-lg bg-white/[0.08] hover:bg-white/[0.16] text-white/70 hover:text-white border border-white/[0.1] transition-all"
    >
      {copied ? "✅ Copied" : `📋 ${label}`}
    </button>
  );
}

function SectionCard({
  title,
  emoji,
  children,
  copyText,
}: {
  title: string;
  emoji: string;
  children: React.ReactNode;
  copyText?: string;
}) {
  return (
    <Card className="border border-white/[0.1] bg-white/[0.03] backdrop-blur-lg">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white/90 flex items-center gap-2">
            <span>{emoji}</span> {title}
          </h3>
          {copyText !== undefined && <CopyButton text={copyText} />}
        </div>
        {children}
      </CardContent>
    </Card>
  );
}

export default function TubeGen() {
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("");
  const [keywords, setKeywords] = useState("");
  const [tone, setTone] = useState<(typeof TONES)[number]>("energetic");
  const [contentType, setContentType] = useState<(typeof CONTENT_TYPES)[number]>("explainer");
  const [length, setLength] = useState<(typeof LENGTHS)[number]["value"]>("standard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TubeGenPackage | null>(null);

  const handleGenerate = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch("/api/tube_gen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, audience, keywords, tone, contentType, length }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.error || "Failed to generate content.");
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-[#030303] py-12">
      <div className="absolute inset-0 bg-gradient-to-br from-rose-500/[0.05] via-transparent to-indigo-500/[0.05] blur-3xl" />

      <div className="absolute inset-0 overflow-hidden">
        <ElegantShape delay={0.3} width={600} height={140} rotate={12} gradient="from-rose-500/[0.15]" className="left-[-10%] md:left-[-5%] top-[10%]" />
        <ElegantShape delay={0.5} width={500} height={120} rotate={-15} gradient="from-indigo-500/[0.15]" className="right-[-5%] md:right-[0%] top-[65%]" />
        <ElegantShape delay={0.4} width={300} height={80} rotate={-8} gradient="from-violet-500/[0.15]" className="left-[5%] md:left-[10%] bottom-[5%]" />
        <ElegantShape delay={0.6} width={200} height={60} rotate={20} gradient="from-amber-500/[0.15]" className="right-[15%] md:right-[20%] top-[8%]" />
      </div>

      <div className="relative z-10 w-full max-w-5xl mx-auto p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <h1 className="text-4xl md:text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-white via-rose-100 to-purple-100 drop-shadow-[0_0_20px_rgba(255,255,255,0.3)]">
            🎬 TubeGen AI Studio
          </h1>
          <p className="text-white/60 mt-3 max-w-2xl mx-auto">
            Turn any idea into a full YouTube content package — click-worthy titles, hooks, SEO description, tags, a
            full script, thumbnail concepts, and chapters. All in one click.
          </p>
        </motion.div>

        {/* Generator Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          <Card className="border border-white/[0.1] bg-white/[0.03] backdrop-blur-lg mb-8">
            <CardContent className="p-6 space-y-4">
              <div>
                <label className="text-sm text-white/70 mb-1.5 block">Video topic or idea *</label>
                <Input
                  placeholder="e.g. How to start investing with $100"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleGenerate()}
                  className="bg-white/[0.05] border-white/[0.1] text-white placeholder:text-white/40 focus:border-white/30 focus:ring-white/20 rounded-xl"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-white/70 mb-1.5 block">Target audience</label>
                  <Input
                    placeholder="e.g. college students, new investors"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    className="bg-white/[0.05] border-white/[0.1] text-white placeholder:text-white/40 focus:border-white/30 focus:ring-white/20 rounded-xl"
                  />
                </div>
                <div>
                  <label className="text-sm text-white/70 mb-1.5 block">Focus keywords (optional)</label>
                  <Input
                    placeholder="e.g. investing, stocks, budgeting"
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    className="bg-white/[0.05] border-white/[0.1] text-white placeholder:text-white/40 focus:border-white/30 focus:ring-white/20 rounded-xl"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm text-white/70 mb-1.5 block">Content type</label>
                  <select
                    value={contentType}
                    onChange={(e) => setContentType(e.target.value as (typeof CONTENT_TYPES)[number])}
                    className="w-full bg-white/[0.05] border border-white/[0.1] text-white rounded-xl px-3 py-2 text-sm focus:border-white/30 focus:outline-none capitalize"
                  >
                    {CONTENT_TYPES.map((t) => (
                      <option key={t} value={t} className="bg-[#030303] capitalize">
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-white/70 mb-1.5 block">Tone</label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value as (typeof TONES)[number])}
                    className="w-full bg-white/[0.05] border border-white/[0.1] text-white rounded-xl px-3 py-2 text-sm focus:border-white/30 focus:outline-none capitalize"
                  >
                    {TONES.map((t) => (
                      <option key={t} value={t} className="bg-[#030303] capitalize">
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-white/70 mb-1.5 block">Length</label>
                  <select
                    value={length}
                    onChange={(e) => setLength(e.target.value as (typeof LENGTHS)[number]["value"])}
                    className="w-full bg-white/[0.05] border border-white/[0.1] text-white rounded-xl px-3 py-2 text-sm focus:border-white/30 focus:outline-none"
                  >
                    {LENGTHS.map((l) => (
                      <option key={l.value} value={l.value} className="bg-[#030303]">
                        {l.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <Button
                onClick={handleGenerate}
                disabled={loading || !topic.trim()}
                className="w-full bg-gradient-to-r from-rose-500 to-purple-600 hover:from-rose-600 hover:to-purple-700 text-white border-0 rounded-xl transition-all duration-300 hover:shadow-[0_0_25px_rgba(244,63,94,0.4)] font-semibold py-3 text-lg disabled:opacity-50"
              >
                {loading ? "⚡ Generating..." : "🚀 Generate Content Package"}
              </Button>
            </CardContent>
          </Card>
        </motion.div>

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-center py-8">
            <div className="bg-white/[0.05] border border-white/[0.1] rounded-2xl p-6 backdrop-blur-lg">
              <AILoader text="Building your content package" size="lg" />
            </div>
          </motion.div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-200 text-sm text-center mb-6">
            {error}
          </div>
        )}

        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {result._fallback && (
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200/90 text-xs text-center">
                ⚠️ Showing a template package. Set <code className="font-mono">OPENAI_API_KEY</code> for fully AI-generated, topic-tailored results.
              </div>
            )}

            {/* Titles */}
            <SectionCard title="Title Ideas" emoji="✨">
              <div className="space-y-3">
                {result.titles?.map((t, i) => (
                  <div key={i} className="p-3 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-start justify-between gap-3">
                    <div>
                      <p className="text-white/90 font-medium">{t.title}</p>
                      <p className="text-white/50 text-xs mt-1">💡 {t.reason}</p>
                    </div>
                    <CopyButton text={t.title} />
                  </div>
                ))}
              </div>
            </SectionCard>

            {/* Hook */}
            <SectionCard title="Opening Hook" emoji="🪝" copyText={result.hook}>
              <p className="text-white/80 leading-relaxed italic">&ldquo;{result.hook}&rdquo;</p>
            </SectionCard>

            {/* Script */}
            <SectionCard title="Full Script" emoji="📜" copyText={result.script}>
              <pre className="text-white/80 text-sm leading-relaxed whitespace-pre-wrap font-sans max-h-96 overflow-y-auto">
                {result.script}
              </pre>
            </SectionCard>

            {/* Description */}
            <SectionCard title="SEO Description" emoji="📝" copyText={result.description}>
              <pre className="text-white/80 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                {result.description}
              </pre>
            </SectionCard>

            {/* Tags */}
            <SectionCard title="Tags & Keywords" emoji="🏷️" copyText={result.tags?.join(", ")}>
              <div className="flex flex-wrap gap-2">
                {result.tags?.map((tag, i) => (
                  <span key={i} className="text-xs px-3 py-1 rounded-full bg-white/[0.06] border border-white/[0.1] text-white/70">
                    {tag}
                  </span>
                ))}
              </div>
            </SectionCard>

            {/* Chapters */}
            <SectionCard
              title="Chapters"
              emoji="⏱️"
              copyText={result.chapters?.map((c) => `${c.timestamp} ${c.title}`).join("\n")}
            >
              <div className="space-y-1.5">
                {result.chapters?.map((c, i) => (
                  <div key={i} className="flex gap-3 text-sm">
                    <span className="text-white/40 font-mono min-w-[3rem]">{c.timestamp}</span>
                    <span className="text-white/80">{c.title}</span>
                  </div>
                ))}
              </div>
            </SectionCard>

            {/* Thumbnails */}
            <SectionCard title="Thumbnail Concepts" emoji="🖼️">
              <div className="grid md:grid-cols-3 gap-4">
                {result.thumbnails?.map((th, i) => (
                  <div key={i} className="p-4 rounded-lg bg-white/[0.04] border border-white/[0.08]">
                    <div className="mb-3 h-20 rounded-md bg-gradient-to-br from-rose-500/30 to-indigo-500/30 flex items-center justify-center border border-white/[0.1]">
                      <span className="text-white font-extrabold text-sm text-center px-2 drop-shadow-lg uppercase">
                        {th.overlayText}
                      </span>
                    </div>
                    <p className="text-white/80 text-sm font-medium mb-1">{th.concept}</p>
                    <p className="text-white/50 text-xs">🎨 {th.visualStyle}</p>
                  </div>
                ))}
              </div>
            </SectionCard>

            {/* CTA */}
            <SectionCard title="Closing Call-to-Action" emoji="📢" copyText={result.cta}>
              <p className="text-white/80 leading-relaxed">{result.cta}</p>
            </SectionCard>
          </motion.div>
        )}
      </div>
    </div>
  );
}
