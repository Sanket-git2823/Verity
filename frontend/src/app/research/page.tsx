"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Search,
  Send,
  Loader2,
  AlertTriangle,
  FileText,
  Clock,
  ChevronRight,
  Settings2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { queryResearch, getQueryHistory } from "@/lib/api";
import { formatDuration, truncateText, formatDate, formatScore } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { QueryResponse, QueryHistoryItem, Citation } from "@/types";

export default function ResearchPage() {
  const [query, setQuery] = useState("");
  const [followUpQuery, setFollowUpQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [activeCitation, setActiveCitation] = useState<number | null>(null);
  const [showConfig, setShowConfig] = useState(false);

  // Retrieval config
  const [bm25Weight, setBm25Weight] = useState(0.3);
  const [vectorWeight, setVectorWeight] = useState(0.7);
  const [topK, setTopK] = useState(10);
  const [rerank, setRerank] = useState(true);
  const [generateAnswer, setGenerateAnswer] = useState(true);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const citationRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getQueryHistory({ page: 1, page_size: 20 });
      setHistory(data.items);
    } catch {
      // silent fail on history load
    }
  };

  const executeQuery = useCallback(
    async (q: string) => {
      if (!q.trim()) return;
      setLoading(true);
      setError(null);
      setActiveCitation(null);

      try {
        const data = await queryResearch({
          query: q.trim(),
          bm25_weight: bm25Weight,
          vector_weight: vectorWeight,
          top_k: topK,
          rerank,
          generate_answer: generateAnswer,
        });
        setResult(data);
        loadHistory();
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : "Query failed";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [bm25Weight, vectorWeight, topK, rerank, generateAnswer]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeQuery(query);
  };

  const handleFollowUp = (e: React.FormEvent) => {
    e.preventDefault();
    if (followUpQuery.trim()) {
      setQuery(followUpQuery);
      executeQuery(followUpQuery);
      setFollowUpQuery("");
    }
  };

  const handleCitationClick = (index: number) => {
    setActiveCitation(activeCitation === index ? null : index);
    const ref = citationRefs.current[index];
    if (ref) {
      ref.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  const renderAnswerText = (text: string, citations: Citation[]) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citIndex = parseInt(match[1]);
        const cit = citations.find((c) => c.citation_index === citIndex);
        return (
          <button
            key={i}
            onClick={() => handleCitationClick(citIndex)}
            className={cn(
              "inline-flex items-center justify-center h-4 min-w-[16px] px-1 text-[10px] font-mono font-semibold rounded-sm mx-0.5 transition-colors cursor-pointer",
              activeCitation === citIndex
                ? "bg-blue-500 text-white"
                : "bg-zinc-700 text-zinc-300 hover:bg-zinc-600"
            )}
            title={cit ? `${cit.filename}${cit.page_number ? ` p.${cit.page_number}` : ""}` : undefined}
          >
            {citIndex}
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Search bar */}
      <div className="border-b border-zinc-800 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-2 items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="research query — enter your question"
              className="w-full h-10 bg-zinc-900 border border-zinc-800 rounded-sm pl-10 pr-4 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
              disabled={loading}
            />
          </div>
          <Button type="submit" disabled={loading || !query.trim()} size="lg">
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Query
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="lg"
            onClick={() => setShowConfig(!showConfig)}
            className={cn(showConfig && "bg-zinc-800")}
          >
            <Settings2 className="h-4 w-4" />
          </Button>
        </form>

        {/* Config panel */}
        {showConfig && (
          <div className="flex items-center gap-6 mt-3 text-xs text-zinc-400">
            <label className="flex items-center gap-2">
              <span className="text-zinc-500 uppercase tracking-wider">BM25</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={bm25Weight}
                onChange={(e) => setBm25Weight(parseFloat(e.target.value))}
                className="w-20 h-1 accent-zinc-400"
              />
              <span className="font-mono w-8 text-right">{bm25Weight.toFixed(2)}</span>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-zinc-500 uppercase tracking-wider">Vector</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={vectorWeight}
                onChange={(e) => setVectorWeight(parseFloat(e.target.value))}
                className="w-20 h-1 accent-zinc-400"
              />
              <span className="font-mono w-8 text-right">{vectorWeight.toFixed(2)}</span>
            </label>
            <label className="flex items-center gap-2">
              <span className="text-zinc-500 uppercase tracking-wider">Top-K</span>
              <select
                value={topK}
                onChange={(e) => setTopK(parseInt(e.target.value))}
                className="bg-zinc-800 border border-zinc-700 rounded-sm px-2 py-0.5 text-xs text-zinc-300"
              >
                {[5, 10, 15, 20, 30, 50].map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-zinc-500 uppercase tracking-wider">Rerank</span>
              <input
                type="checkbox"
                checked={rerank}
                onChange={(e) => setRerank(e.target.checked)}
                className="accent-zinc-400"
              />
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-zinc-500 uppercase tracking-wider">Generate</span>
              <input
                type="checkbox"
                checked={generateAnswer}
                onChange={(e) => setGenerateAnswer(e.target.checked)}
                className="accent-zinc-400"
              />
            </label>
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left - Answer panel */}
        <div className="flex-[3] border-r border-zinc-800 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-6 py-4">
            {loading && (
              <div className="flex items-center gap-3 py-16 justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
                <span className="text-sm text-zinc-500">Retrieving and generating…</span>
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-950/50 border border-red-900 rounded-sm text-sm text-red-400 mt-4">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {!loading && !error && !result && (
              <div className="flex flex-col items-center justify-center py-24 text-zinc-600">
                <Search className="h-8 w-8 mb-3" />
                <p className="text-sm">Enter a research query to begin</p>
                <p className="text-xs mt-1">Results will include cited sources from your document corpus</p>
              </div>
            )}

            {!loading && result && (
              <div className="space-y-4">
                {/* Query echo */}
                <div className="text-xs text-zinc-500 font-mono flex items-center gap-2">
                  <span className="uppercase tracking-wider">Query</span>
                  <span className="text-zinc-600">·</span>
                  <span className="text-zinc-400">{result.query}</span>
                  <span className="text-zinc-600">·</span>
                  <span className="data-mono">{formatDuration(result.latency_ms)}</span>
                </div>

                {/* Insufficient evidence warning */}
                {result.answer?.insufficient_evidence && (
                  <div className="flex items-center gap-2 p-2 bg-amber-950/30 border border-amber-900/50 rounded-sm text-xs text-amber-400">
                    <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" />
                    Insufficient evidence — answer may be incomplete or unreliable
                  </div>
                )}

                {/* Answer text */}
                {result.answer && (
                  <div className="space-y-3">
                    <div className="text-sm text-zinc-200 leading-relaxed whitespace-pre-wrap">
                      {renderAnswerText(result.answer.text, result.answer.citations)}
                    </div>

                    {/* Confidence bar */}
                    <div className="flex items-center gap-3">
                      <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Confidence</span>
                      <div className="flex-1 h-1 bg-zinc-800 rounded-sm overflow-hidden max-w-xs">
                        <div
                          className={cn(
                            "h-full rounded-sm transition-all",
                            result.answer.confidence >= 0.7
                              ? "bg-emerald-500"
                              : result.answer.confidence >= 0.4
                                ? "bg-amber-500"
                                : "bg-red-500"
                          )}
                          style={{ width: `${result.answer.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-zinc-500">
                        {(result.answer.confidence * 100).toFixed(0)}%
                      </span>
                    </div>

                    {/* Evidence summary */}
                    <div className="text-xs text-zinc-500 flex items-center gap-4 pt-1 border-t border-zinc-800/50">
                      <span>
                        {result.answer.citations.length} citation{result.answer.citations.length !== 1 ? "s" : ""}
                      </span>
                      <span>·</span>
                      <span>
                        {new Set(result.answer.citations.map((c) => c.document_id)).size} source{new Set(result.answer.citations.map((c) => c.document_id)).size !== 1 ? "s" : ""}
                      </span>
                      <span>·</span>
                      <span>Model: {result.answer.model}</span>
                    </div>
                  </div>
                )}

                {/* If no answer but have results */}
                {!result.answer && result.retrieval_results.length > 0 && (
                  <div className="text-xs text-zinc-500">
                    {result.retrieval_results.length} chunks retrieved (answer generation disabled)
                  </div>
                )}

                {!result.answer && result.retrieval_results.length === 0 && (
                  <div className="text-sm text-zinc-500 py-8 text-center">
                    No relevant results found for this query.
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Follow-up input */}
          {result && !loading && (
            <div className="border-t border-zinc-800 px-6 py-3">
              <form onSubmit={handleFollowUp} className="flex gap-2">
                <input
                  type="text"
                  value={followUpQuery}
                  onChange={(e) => setFollowUpQuery(e.target.value)}
                  placeholder="follow-up query…"
                  className="flex-1 h-8 bg-zinc-900 border border-zinc-800 rounded-sm px-3 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-zinc-600"
                />
                <Button type="submit" variant="outline" size="sm" disabled={!followUpQuery.trim()}>
                  <Send className="h-3 w-3" />
                </Button>
              </form>
            </div>
          )}

          {/* History */}
          {history.length > 0 && (
            <div className="border-t border-zinc-800 max-h-40 overflow-y-auto">
              <div className="px-6 py-2">
                <span className="text-[10px] text-zinc-600 uppercase tracking-wider">History</span>
              </div>
              {history.map((item) => (
                <button
                  key={item.query_id}
                  onClick={() => {
                    setQuery(item.query);
                    executeQuery(item.query);
                  }}
                  className="w-full flex items-center gap-3 px-6 py-1.5 text-left hover:bg-zinc-800/30 transition-colors group"
                >
                  <Clock className="h-3 w-3 text-zinc-700 flex-shrink-0" />
                  <span className="text-xs text-zinc-500 truncate flex-1 group-hover:text-zinc-300">
                    {truncateText(item.query, 80)}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-700">
                    {formatDuration(item.latency_ms)}
                  </span>
                  <span className="text-[10px] text-zinc-700">
                    {formatDate(item.created_at)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right - Source panel */}
        <div className="flex-[2] flex flex-col overflow-hidden">
          {result ? (
            <Tabs defaultValue="citations" className="flex flex-col h-full">
              <TabsList className="px-4 flex-shrink-0">
                <TabsTrigger value="citations">Citations</TabsTrigger>
                <TabsTrigger value="sources">Sources</TabsTrigger>
                <TabsTrigger value="raw">Raw</TabsTrigger>
              </TabsList>

              <TabsContent value="citations" className="flex-1 overflow-y-auto">
                <div className="px-4 py-3 space-y-2">
                  {result.answer?.citations.length === 0 && (
                    <p className="text-xs text-zinc-600 py-4 text-center">No citations</p>
                  )}
                  {result.answer?.citations.map((cit) => (
                    <div
                      key={cit.citation_index}
                      ref={(el) => { citationRefs.current[cit.citation_index] = el; }}
                      className={cn(
                        "border rounded-sm p-3 transition-colors",
                        activeCitation === cit.citation_index
                          ? "border-blue-500/50 bg-blue-950/20"
                          : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-700"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="flex items-center justify-center h-4 min-w-[16px] px-1 text-[10px] font-mono font-semibold bg-zinc-700 text-zinc-300 rounded-sm">
                          {cit.citation_index}
                        </span>
                        <FileText className="h-3 w-3 text-zinc-500" />
                        <span className="text-xs text-zinc-400 truncate font-mono">
                          {cit.filename}
                        </span>
                        {cit.page_number && (
                          <span className="text-[10px] text-zinc-600 font-mono">
                            p.{cit.page_number}
                          </span>
                        )}
                        <span className="text-[10px] text-zinc-600 font-mono ml-auto">
                          {formatScore(cit.score)}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 leading-relaxed">
                        {truncateText(cit.content, 300)}
                      </p>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="sources" className="flex-1 overflow-y-auto">
                <div className="px-4 py-3 space-y-1">
                  {result.answer?.citations && (() => {
                    const uniqueSources = new Map<string, { filename: string; document_id: string; count: number }>();
                    result.answer.citations.forEach((cit) => {
                      const existing = uniqueSources.get(cit.document_id);
                      if (existing) {
                        existing.count++;
                      } else {
                        uniqueSources.set(cit.document_id, {
                          filename: cit.filename,
                          document_id: cit.document_id,
                          count: 1,
                        });
                      }
                    });
                    return Array.from(uniqueSources.values()).map((src) => (
                      <div
                        key={src.document_id}
                        className="flex items-center gap-3 px-3 py-2 border border-zinc-800 rounded-sm hover:border-zinc-700 transition-colors"
                      >
                        <FileText className="h-3.5 w-3.5 text-zinc-500" />
                        <span className="text-xs text-zinc-300 truncate flex-1 font-mono">
                          {src.filename}
                        </span>
                        <Badge size="sm">{src.count} ref{src.count !== 1 ? "s" : ""}</Badge>
                      </div>
                    ));
                  })()}
                  {(!result.answer?.citations || result.answer.citations.length === 0) && (
                    <p className="text-xs text-zinc-600 py-4 text-center">No sources</p>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="raw" className="flex-1 overflow-y-auto">
                <div className="px-4 py-3">
                  <pre className="text-xs text-zinc-400 font-mono whitespace-pre-wrap leading-relaxed">
                    {result.answer?.text || "No raw response available"}
                  </pre>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            <div className="flex items-center justify-center h-full text-zinc-700">
              <div className="text-center">
                <ChevronRight className="h-6 w-6 mx-auto mb-2" />
                <p className="text-xs">Sources appear here</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
