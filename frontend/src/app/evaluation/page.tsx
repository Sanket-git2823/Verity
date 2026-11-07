"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  BarChart3,
  Play,
  Plus,
  RefreshCw,
  Sliders,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  ChevronRight,
  TrendingUp,
  FileCheck,
  CheckSquare,
  ArrowUpDown,
  Layers,
  X,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  getEvaluationDatasets,
  createEvaluationDataset,
  getEvaluationRuns,
  getEvaluationRun,
  createEvaluationRun,
  compareEvaluationRuns,
} from "@/lib/api";
import { formatDuration, formatScore } from "@/lib/utils";
import type {
  EvaluationDataset,
  EvaluationRun,
  EvaluationQueryResult,
  EvaluationCompareResponse,
} from "@/types";

export default function EvaluationPage() {
  const [datasets, setDatasets] = useState<EvaluationDataset[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [selectedRunDetail, setSelectedRunDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Run selection for comparison
  const [compareRunIds, setCompareRunIds] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<any[]>([]);

  // Run Modal State
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [runName, setRunName] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [bm25Weight, setBm25Weight] = useState(0.4);
  const [vectorWeight, setVectorWeight] = useState(0.6);
  const [topK, setTopK] = useState(10);
  const [rerank, setRerank] = useState(true);
  const [isLaunchingRun, setIsLaunchingRun] = useState(false);

  // Create Dataset Modal State
  const [isDatasetModalOpen, setIsDatasetModalOpen] = useState(false);
  const [datasetName, setDatasetName] = useState("");
  const [datasetDesc, setDatasetDesc] = useState("");
  const [datasetJson, setDatasetJson] = useState("");
  const [isCreatingDataset, setIsCreatingDataset] = useState(false);

  // Initial load
  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dsets, evalRuns] = await Promise.all([
        getEvaluationDatasets(),
        getEvaluationRuns(),
      ]);
      setDatasets(dsets);
      setRuns(evalRuns);

      if (dsets.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(dsets[0].id);
      }

      if (evalRuns.length > 0) {
        const first = evalRuns[0];
        setSelectedRun(first);
        loadRunDetail(first.id);

        // Pre-select top 2-3 completed runs for comparison chart
        const completed = evalRuns.filter((r) => r.status === "completed").slice(0, 3);
        const ids = completed.map((r) => r.id);
        setCompareRunIds(ids);
        if (ids.length >= 2) {
          updateComparison(ids);
        }
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load evaluation datasets or runs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const loadRunDetail = async (id: string) => {
    try {
      const detail = await getEvaluationRun(id);
      setSelectedRunDetail(detail);
    } catch {
      // silent
    }
  };

  const handleSelectRun = (run: EvaluationRun) => {
    setSelectedRun(run);
    loadRunDetail(run.id);
  };

  const toggleCompareRun = async (id: string) => {
    let next: string[];
    if (compareRunIds.includes(id)) {
      next = compareRunIds.filter((x) => x !== id);
    } else {
      next = [...compareRunIds, id];
    }
    setCompareRunIds(next);
    if (next.length >= 1) {
      updateComparison(next);
    } else {
      setComparisonData([]);
    }
  };

  const updateComparison = async (ids: string[]) => {
    try {
      const comp = await compareEvaluationRuns(ids);
      // Transform runs into recharts comparison format
      const chartPoints: Record<string, any>[] = [
        { metric: "MRR" },
        { metric: "Recall@10" },
        { metric: "Precision@10" },
        { metric: "NDCG@10" },
        { metric: "Faithfulness" },
      ];

      comp.runs.forEach((r) => {
        const metrics = r.metrics || (r as any);
        chartPoints[0][r.name] = parseFloat(((metrics.mrr || 0) * 100).toFixed(1));
        chartPoints[1][r.name] = parseFloat(
          (((metrics.recall_at_k as any)?.["10"] || 0) * 100).toFixed(1)
        );
        chartPoints[2][r.name] = parseFloat(
          (((metrics.precision_at_k as any)?.["10"] || 0) * 100).toFixed(1)
        );
        chartPoints[3][r.name] = parseFloat(
          (((metrics.ndcg_at_k as any)?.["10"] || 0) * 100).toFixed(1)
        );
        chartPoints[4][r.name] = parseFloat(
          (((metrics.avg_faithfulness || 0) * 100).toFixed(1))
        );
      });

      setComparisonData(chartPoints);
    } catch {
      // fallback manual parse
    }
  };

  const handleLaunchRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId || !runName.trim()) return;
    setIsLaunchingRun(true);
    try {
      await createEvaluationRun({
        dataset_id: selectedDatasetId,
        name: runName.trim(),
        description: `Config: BM25=${bm25Weight}, Vec=${vectorWeight}, TopK=${topK}, Rerank=${rerank}`,
        config: {
          bm25_weight: bm25Weight,
          vector_weight: vectorWeight,
          top_k: topK,
          rerank,
          k_values: [5, 10, 20],
        },
      });
      setIsRunModalOpen(false);
      setRunName("");
      loadInitialData();
    } catch (err: any) {
      alert("Failed to start run: " + (err?.message || "Unknown error"));
    } finally {
      setIsLaunchingRun(false);
    }
  };

  const handleCreateDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!datasetName.trim()) return;
    setIsCreatingDataset(true);
    try {
      let items = [];
      if (datasetJson.trim()) {
        const parsed = JSON.parse(datasetJson);
        items = Array.isArray(parsed) ? parsed : parsed.items || [];
      } else {
        // default baseline items
        items = [
          {
            query_text: "What are gradient descent optimization algorithms?",
            expected_answer: "Optimization algorithms minimize loss via parameters update.",
          },
          {
            query_text: "How does inverted index retrieval work?",
            expected_answer: "Maps tokens to posting lists containing document IDs and frequencies.",
          },
          {
            query_text: "Explain self-attention mechanism in transformers",
            expected_answer: "Computes query-key dot products to weight value representations.",
          },
        ];
      }

      await createEvaluationDataset({
        name: datasetName.trim(),
        description: datasetDesc.trim() || "Institutional evaluation benchmark",
        items,
      });

      setIsDatasetModalOpen(false);
      setDatasetName("");
      setDatasetDesc("");
      setDatasetJson("");
      loadInitialData();
    } catch (err: any) {
      alert("Failed to create dataset: " + (err?.message || "Invalid JSON"));
    } finally {
      setIsCreatingDataset(false);
    }
  };

  const getRunStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="w-3 h-3" /> COMPLETED
          </Badge>
        );
      case "running":
        return (
          <Badge variant="info" className="gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> RUNNING
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="error" className="gap-1">
            <AlertCircle className="w-3 h-3" /> FAILED
          </Badge>
        );
      default:
        return (
          <Badge variant="default" className="gap-1">
            <Clock className="w-3 h-3" /> {status.toUpperCase()}
          </Badge>
        );
    }
  };

  const currentMetrics = selectedRun?.metrics || (selectedRun as any);

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans">
      {/* Top Header */}
      <div className="h-14 border-b border-zinc-800 px-6 flex items-center justify-between flex-shrink-0 bg-zinc-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <BarChart3 className="w-4 h-4 text-zinc-400" />
          <h1 className="text-sm font-semibold tracking-wider uppercase text-zinc-200">
            Evaluation & Benchmarking Dashboard
          </h1>
          <span className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-sm">
            Empirical RAG Quality Suite
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsDatasetModalOpen(true)}
            className="h-8 gap-1.5 text-xs font-mono border-zinc-800 hover:border-zinc-700 bg-zinc-900"
          >
            <Plus className="w-3.5 h-3.5" />
            NEW DATASET
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={() => {
              setRunName(`eval-run-${new Date().toISOString().slice(11, 19).replace(/:/g, "")}`);
              setIsRunModalOpen(true);
            }}
            className="h-8 gap-1.5 text-xs font-mono bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
          >
            <Play className="w-3.5 h-3.5" />
            EXECUTE EVALUATION RUN
          </Button>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left 65%: Metrics & Visualizations */}
        <div className="flex-[3] flex flex-col overflow-y-auto border-r border-zinc-800 p-6 space-y-6">
          {selectedRun ? (
            <>
              {/* Selected Run Banner */}
              <div className="p-4 border border-zinc-800 bg-zinc-900/50 rounded-sm flex items-center justify-between font-mono">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-zinc-100">
                      {selectedRun.name}
                    </span>
                    {getRunStatusBadge(selectedRun.status)}
                  </div>
                  <div className="text-xs text-zinc-500 mt-1">
                    {selectedRun.description || "Retrieval configuration benchmark"}
                  </div>
                </div>
                <div className="text-right text-xs text-zinc-400">
                  <div>Queries: <span className="text-zinc-200 font-semibold">{selectedRun.total_queries || (selectedRunDetail?.results?.length) || 0}</span></div>
                  <div>Avg Latency: <span className="text-zinc-200 font-semibold">{formatDuration(currentMetrics?.avg_latency_ms || 0)}</span></div>
                </div>
              </div>

              {/* Core Quality Metrics Grid */}
              <div>
                <div className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold mb-3">
                  Retrieval & Generation Benchmarks (Actual Computed Metrics)
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">Recall @ 5</span>
                    <span className="text-lg font-bold text-zinc-100">
                      {((currentMetrics?.recall_at_k?.["5"] ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">Recall @ 10</span>
                    <span className="text-lg font-bold text-zinc-100">
                      {((currentMetrics?.recall_at_k?.["10"] ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">Precision @ 10</span>
                    <span className="text-lg font-bold text-zinc-100">
                      {((currentMetrics?.precision_at_k?.["10"] ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">MRR (Mean RR)</span>
                    <span className="text-lg font-bold text-emerald-400">
                      {formatScore(currentMetrics?.mrr ?? 0, 3)}
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">NDCG @ 10</span>
                    <span className="text-lg font-bold text-zinc-100">
                      {formatScore(currentMetrics?.ndcg_at_k?.["10"] ?? 0, 3)}
                    </span>
                  </div>

                  <div className="p-3 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono">
                    <span className="text-[10px] text-zinc-500 uppercase block">Faithfulness</span>
                    <span className="text-lg font-bold text-emerald-400">
                      {((currentMetrics?.avg_faithfulness ?? 0) * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Latency Percentile Bar */}
              <div className="p-4 bg-zinc-900/30 border border-zinc-800 rounded-sm font-mono text-xs">
                <span className="text-[11px] text-zinc-500 uppercase tracking-wider block mb-2">
                  Latency Distribution
                </span>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <span className="text-zinc-500 text-[10px] block">Mean Latency:</span>
                    <span className="text-zinc-200 font-semibold">{formatDuration(currentMetrics?.avg_latency_ms || 0)}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-[10px] block">P50 (Median):</span>
                    <span className="text-zinc-200 font-semibold">{formatDuration(currentMetrics?.p50_latency_ms || 0)}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 text-[10px] block">P95 Latency:</span>
                    <span className="text-zinc-200 font-semibold">{formatDuration(currentMetrics?.p95_latency_ms || 0)}</span>
                  </div>
                </div>
              </div>

              {/* Comparative Analysis Chart */}
              {comparisonData.length > 0 && (
                <div className="p-4 border border-zinc-800 bg-zinc-900/40 rounded-sm">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 font-semibold">
                      Multi-Configuration Comparison (% Benchmark)
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500">
                      Comparing {compareRunIds.length} runs
                    </span>
                  </div>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={comparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="metric" stroke="#71717a" fontSize={11} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={11} tickLine={false} domain={[0, 100]} />
                        <RechartsTooltip
                          contentStyle={{ backgroundColor: "#18181b", borderColor: "#27272a", fontSize: "12px", fontFamily: "monospace" }}
                        />
                        <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace" }} />
                        {compareRunIds.map((id, idx) => {
                          const r = runs.find((x) => x.id === id);
                          if (!r) return null;
                          const colors = ["#a1a1aa", "#3b82f6", "#10b981", "#f59e0b"];
                          return (
                            <Bar
                              key={id}
                              dataKey={r.name}
                              fill={colors[idx % colors.length]}
                              radius={[2, 2, 0, 0]}
                            />
                          );
                        })}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Per-Query Breakdown Table */}
              <div>
                <div className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold mb-3">
                  Per-Query Ground Truth & Evaluation Details
                </div>
                <div className="border border-zinc-800 rounded-sm overflow-hidden bg-zinc-900/40">
                  <Table>
                    <TableHeader className="bg-zinc-900/80">
                      <TableRow className="border-b border-zinc-800 text-[11px] font-mono text-zinc-400 uppercase">
                        <TableHead className="py-2.5">Evaluation Query</TableHead>
                        <TableHead className="py-2.5 text-right">Recall</TableHead>
                        <TableHead className="py-2.5 text-right">Precision</TableHead>
                        <TableHead className="py-2.5 text-right">Reciprocal Rank</TableHead>
                        <TableHead className="py-2.5 text-right">Faithfulness</TableHead>
                        <TableHead className="py-2.5 text-right">Latency</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedRunDetail?.results && selectedRunDetail.results.length > 0 ? (
                        selectedRunDetail.results.map((res: any, idx: number) => (
                          <TableRow
                            key={res.id || idx}
                            className="border-b border-zinc-800/60 hover:bg-zinc-800/20 text-xs font-mono"
                          >
                            <TableCell className="py-2 font-medium text-zinc-200">
                              <div className="max-w-md truncate" title={res.query_text}>
                                {res.query_text}
                              </div>
                            </TableCell>
                            <TableCell className="py-2 text-right text-zinc-300">
                              {((res.recall ?? 0) * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className="py-2 text-right text-zinc-300">
                              {((res.precision ?? 0) * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className="py-2 text-right text-zinc-300">
                              {formatScore(res.reciprocal_rank ?? 0, 2)}
                            </TableCell>
                            <TableCell className="py-2 text-right text-emerald-400">
                              {((res.faithfulness ?? 0) * 100).toFixed(0)}%
                            </TableCell>
                            <TableCell className="py-2 text-right text-zinc-400">
                              {formatDuration(res.latency_ms || 0)}
                            </TableCell>
                          </TableRow>
                        ))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={6} className="h-24 text-center text-zinc-500 font-mono text-xs">
                            No per-query execution rows recorded for this run.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-zinc-600 font-mono text-xs">
              <BarChart3 className="w-8 h-8 mb-2" />
              <span>No evaluation runs recorded. Click "EXECUTE EVALUATION RUN" to start.</span>
            </div>
          )}
        </div>

        {/* Right 35%: Past Runs & Datasets Directory */}
        <div className="flex-[2] flex flex-col h-full bg-zinc-900/20">
          <div className="h-12 border-b border-zinc-800 px-4 flex items-center justify-between bg-zinc-900">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-zinc-200">
              Evaluation Experiments ({runs.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={loadInitialData}
              className="h-7 w-7 p-0 text-zinc-400 hover:text-zinc-100"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {runs.map((r) => {
              const isSelected = selectedRun?.id === r.id;
              const isCompared = compareRunIds.includes(r.id);
              const m = r.metrics || (r as any);
              return (
                <div
                  key={r.id}
                  onClick={() => handleSelectRun(r)}
                  className={`p-3 border rounded-sm text-xs font-mono cursor-pointer transition-colors space-y-2 ${
                    isSelected
                      ? "border-zinc-500 bg-zinc-900/80"
                      : "border-zinc-800 bg-zinc-950/60 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-100 truncate max-w-[180px]">
                      {r.name}
                    </span>
                    {getRunStatusBadge(r.status)}
                  </div>

                  <div className="grid grid-cols-3 gap-1 text-[11px] text-zinc-400 pt-1 border-t border-zinc-900">
                    <div>
                      MRR: <span className="text-zinc-200">{formatScore(m?.mrr ?? 0, 3)}</span>
                    </div>
                    <div>
                      Rec@10: <span className="text-zinc-200">{(((m?.recall_at_k as any)?.["10"] ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                    <div>
                      Faith: <span className="text-emerald-400">{((m?.avg_faithfulness ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-zinc-500">
                      {new Date(r.created_at).toLocaleDateString()}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleCompareRun(r.id);
                      }}
                      className={`text-[10px] px-1.5 py-0.5 rounded-sm border ${
                        isCompared
                          ? "bg-blue-950 border-blue-800 text-blue-300"
                          : "border-zinc-800 text-zinc-500 hover:text-zinc-300"
                      }`}
                    >
                      {isCompared ? "✓ In Chart" : "+ Compare"}
                    </button>
                  </div>
                </div>
              );
            })}

            {runs.length === 0 && (
              <div className="text-center py-12 text-xs font-mono text-zinc-600">
                No evaluation experiments available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Execute Run Modal */}
      {isRunModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleLaunchRun}
            className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-lg p-6 shadow-2xl font-mono space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                Launch Evaluation Experiment
              </h3>
              <button
                type="button"
                onClick={() => setIsRunModalOpen(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Experiment Name</label>
                <Input
                  value={runName}
                  onChange={(e) => setRunName(e.target.value)}
                  placeholder="e.g. baseline-hybrid-reranked"
                  className="h-8 bg-zinc-950 border-zinc-800 text-xs font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Target Evaluation Dataset</label>
                <select
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  className="w-full h-8 bg-zinc-950 border border-zinc-800 rounded-sm px-2 text-xs text-zinc-200 font-mono"
                  required
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.item_count || 0} items)
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-sm space-y-3">
                <div className="text-[11px] text-zinc-500 uppercase font-semibold">
                  Retrieval Pipeline Hyperparameters
                </div>

                <div>
                  <div className="flex justify-between text-[11px] text-zinc-400 mb-1">
                    <span>BM25 Weight: {bm25Weight}</span>
                    <span>Vector Weight: {vectorWeight}</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={bm25Weight}
                    onChange={(e) => {
                      const w = parseFloat(e.target.value);
                      setBm25Weight(w);
                      setVectorWeight(parseFloat((1 - w).toFixed(2)));
                    }}
                    className="w-full accent-zinc-400"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-zinc-400">Top K Candidates:</span>
                  <select
                    value={topK}
                    onChange={(e) => setTopK(parseInt(e.target.value))}
                    className="bg-zinc-900 border border-zinc-800 px-2 py-1 rounded-sm text-xs"
                  >
                    {[5, 10, 15, 20, 30].map((k) => (
                      <option key={k} value={k}>{k}</option>
                    ))}
                  </select>
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rerank}
                    onChange={(e) => setRerank(e.target.checked)}
                    className="accent-zinc-400"
                  />
                  <span className="text-zinc-300 text-[11px]">
                    Apply Cross-Encoder Reranking
                  </span>
                </label>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-zinc-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsRunModalOpen(false)}
                className="text-xs border-zinc-800 bg-zinc-900"
              >
                CANCEL
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isLaunchingRun}
                className="text-xs bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
              >
                {isLaunchingRun ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    DISPATCHING...
                  </>
                ) : (
                  "START EVALUATION"
                )}
              </Button>
            </div>
          </form>
        </div>
      )}

      {/* Create Dataset Modal */}
      {isDatasetModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <form
            onSubmit={handleCreateDataset}
            className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-lg p-6 shadow-2xl font-mono space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-100">
                New Evaluation Ground-Truth Dataset
              </h3>
              <button
                type="button"
                onClick={() => setIsDatasetModalOpen(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Dataset Identifier</label>
                <Input
                  value={datasetName}
                  onChange={(e) => setDatasetName(e.target.value)}
                  placeholder="e.g. institutional-benchmark-v1"
                  className="h-8 bg-zinc-950 border-zinc-800 text-xs font-mono"
                  required
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Description</label>
                <Input
                  value={datasetDesc}
                  onChange={(e) => setDatasetDesc(e.target.value)}
                  placeholder="Empirical test questions with verified relevance"
                  className="h-8 bg-zinc-950 border-zinc-800 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">
                  JSON Ground-Truth Items (Optional - leave empty for sample benchmark):
                </label>
                <textarea
                  value={datasetJson}
                  onChange={(e) => setDatasetJson(e.target.value)}
                  placeholder='[{"query_text": "...", "expected_answer": "..."}]'
                  className="w-full h-32 bg-zinc-950 border border-zinc-800 rounded-sm p-2 text-xs font-mono text-zinc-200 focus:outline-none focus:border-zinc-700"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-zinc-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsDatasetModalOpen(false)}
                className="text-xs border-zinc-800 bg-zinc-900"
              >
                CANCEL
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isCreatingDataset}
                className="text-xs bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
              >
                {isCreatingDataset ? "SAVING..." : "CREATE DATASET"}
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
