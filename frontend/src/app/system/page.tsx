"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  Server,
  Database,
  Cpu,
  Layers,
  FileText,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Zap,
  HardDrive,
  BarChart,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getSystemHealth, getSystemMetrics } from "@/lib/api";
import { formatBytes, formatDuration, formatNumber } from "@/lib/utils";
import type { SystemHealth, SystemMetrics } from "@/types";

export default function SystemPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshIntervalSec, setRefreshIntervalSec] = useState(15);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchSystemData = useCallback(async () => {
    try {
      const [h, m] = await Promise.all([
        getSystemHealth(),
        getSystemMetrics(),
      ]);
      setHealth(h);
      setMetrics(m);
      setError(null);
      setLastRefreshed(new Date());
    } catch (err: any) {
      setError(err?.message || "Failed to query system telemetry");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSystemData();
  }, [fetchSystemData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchSystemData, refreshIntervalSec * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshIntervalSec, fetchSystemData]);

  const getServiceStatusDot = (status?: string) => {
    switch (status?.toLowerCase()) {
      case "healthy":
        return <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />;
      case "degraded":
      case "unavailable":
        return <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />;
      default:
        return <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans">
      {/* Top Header */}
      <div className="h-14 border-b border-zinc-800 px-6 flex items-center justify-between flex-shrink-0 bg-zinc-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <Activity className="w-4 h-4 text-zinc-400" />
          <h1 className="text-sm font-semibold tracking-wider uppercase text-zinc-200">
            System Monitoring & Telemetry
          </h1>
          <span className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-sm">
            Node: verity-core-01
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
            <span>Auto-refresh:</span>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-zinc-400"
            />
            <select
              value={refreshIntervalSec}
              onChange={(e) => setRefreshIntervalSec(parseInt(e.target.value))}
              disabled={!autoRefresh}
              className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-1.5 py-0.5 rounded-sm text-xs"
            >
              <option value={10}>10s</option>
              <option value={15}>15s</option>
              <option value={30}>30s</option>
              <option value={60}>60s</option>
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchSystemData}
            disabled={loading}
            className="h-8 gap-1.5 text-xs font-mono border-zinc-800 hover:border-zinc-700 bg-zinc-900"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            REFRESH
          </Button>
        </div>
      </div>

      {/* Main Telemetry Body */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {error && (
          <div className="p-3 border border-red-900/50 bg-red-950/20 text-red-400 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Telemetry Error: {error}</span>
          </div>
        )}

        {/* Section 1: Infrastructure Service Health */}
        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold mb-3">
            Infrastructure & Subsystem Health
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Overall Health */}
            <div className="p-4 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-zinc-400" />
                  Cluster State
                </span>
                {getServiceStatusDot(health?.status)}
              </div>
              <div className="text-xl font-bold uppercase text-zinc-100">
                {health?.status || "HEALTHY"}
              </div>
              <div className="text-[11px] text-zinc-500">
                Uptime: {formatDuration((health?.uptime_seconds || 0) * 1000)}
              </div>
            </div>

            {/* PostgreSQL & pgvector */}
            <div className="p-4 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-zinc-400" />
                  PostgreSQL + pgvector
                </span>
                {getServiceStatusDot(health?.services?.database?.status || (health as any)?.database)}
              </div>
              <div className="text-xl font-bold uppercase text-zinc-100">
                {health?.services?.database?.status || (health as any)?.database || "ONLINE"}
              </div>
              <div className="text-[11px] text-zinc-500">
                HNSW Vector Index & Full-Text TsVector
              </div>
            </div>

            {/* Redis Cache */}
            <div className="p-4 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="flex items-center gap-2">
                  <Server className="w-4 h-4 text-zinc-400" />
                  Redis Cache / Queue
                </span>
                {getServiceStatusDot(health?.services?.redis?.status || (health as any)?.redis)}
              </div>
              <div className="text-xl font-bold uppercase text-zinc-100">
                {health?.services?.redis?.status || (health as any)?.redis || "CONNECTED"}
              </div>
              <div className="text-[11px] text-zinc-500">
                Query Caching & Background Task Worker
              </div>
            </div>

            {/* API Engine */}
            <div className="p-4 bg-zinc-900/40 border border-zinc-800 rounded-sm font-mono space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-zinc-400" />
                  FastAPI Engine
                </span>
                {getServiceStatusDot("healthy")}
              </div>
              <div className="text-xl font-bold uppercase text-zinc-100">
                v{health?.version || "1.0.0"}
              </div>
              <div className="text-[11px] text-zinc-500">
                Async Python 3.12+ Runtime
              </div>
            </div>
          </div>
        </div>

        {/* Section 2: Platform Metrics Key Indicators */}
        <div>
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold mb-3">
            Core Corpus & Pipeline Metrics
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Total Documents</span>
              <span className="text-xl font-bold text-zinc-100">
                {metrics?.total_documents ?? 0}
              </span>
            </div>

            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Total Chunks</span>
              <span className="text-xl font-bold text-zinc-100">
                {formatNumber(metrics?.total_chunks ?? 0)}
              </span>
            </div>

            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Vector Embeddings</span>
              <span className="text-xl font-bold text-emerald-400">
                {formatNumber(metrics?.total_embeddings ?? 0)}
              </span>
            </div>

            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Queries Executed</span>
              <span className="text-xl font-bold text-zinc-100">
                {metrics?.total_queries ?? 0}
              </span>
            </div>

            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Mean Latency</span>
              <span className="text-xl font-bold text-zinc-100">
                {formatDuration(metrics?.avg_latency_ms || (metrics as any)?.avg_query_latency_ms || 0)}
              </span>
            </div>

            <div className="p-3 bg-zinc-900/50 border border-zinc-800 rounded-sm">
              <span className="text-[10px] text-zinc-500 uppercase block">Failed Ingestions</span>
              <span className="text-xl font-bold text-red-400">
                {metrics?.failed_ingestions ?? 0}
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: Distribution Breakdowns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Document Ingestion Breakdown */}
          <div className="p-4 border border-zinc-800 bg-zinc-900/40 rounded-sm font-mono space-y-3">
            <span className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block">
              Document Status Distribution
            </span>
            <div className="space-y-2">
              {metrics?.documents_by_status && Object.keys(metrics.documents_by_status).length > 0 ? (
                Object.entries(metrics.documents_by_status).map(([status, count]) => {
                  const total = metrics.total_documents || 1;
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={status} className="space-y-1">
                      <div className="flex justify-between text-xs text-zinc-300">
                        <span className="uppercase text-[11px] text-zinc-400">{status}</span>
                        <span>{count} ({pct}%)</span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-sm overflow-hidden">
                        <div
                          className={`h-full ${
                            status === "completed"
                              ? "bg-emerald-500"
                              : status === "failed"
                              ? "bg-red-500"
                              : "bg-blue-500"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  No documents cataloged in repository.
                </div>
              )}
            </div>
          </div>

          {/* Document Format Distribution */}
          <div className="p-4 border border-zinc-800 bg-zinc-900/40 rounded-sm font-mono space-y-3">
            <span className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block">
              Ingested Document Formats
            </span>
            <div className="space-y-2">
              {metrics?.documents_by_type && Object.keys(metrics.documents_by_type).length > 0 ? (
                Object.entries(metrics.documents_by_type).map(([ext, count]) => {
                  const total = metrics.total_documents || 1;
                  const pct = Math.round((count / total) * 100);
                  return (
                    <div key={ext} className="space-y-1">
                      <div className="flex justify-between text-xs text-zinc-300">
                        <span className="uppercase text-[11px] text-zinc-400">{ext.replace(".", "")}</span>
                        <span>{count} files ({pct}%)</span>
                      </div>
                      <div className="h-1.5 bg-zinc-800 rounded-sm overflow-hidden">
                        <div className="h-full bg-zinc-400" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-zinc-500 text-xs py-4 text-center">
                  No formats recorded yet.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Section 4: Query Latency Distribution & Storage */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 border border-zinc-800 bg-zinc-900/40 rounded-sm font-mono space-y-3">
            <span className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block">
              Retrieval & Generation Latency Profile
            </span>
            <div className="grid grid-cols-3 gap-3 text-center pt-2">
              <div className="p-3 bg-zinc-950 border border-zinc-800">
                <span className="text-[10px] text-zinc-500 uppercase block">Average</span>
                <span className="text-sm font-bold text-zinc-200">
                  {formatDuration(metrics?.query_latency?.avg || (metrics as any)?.avg_query_latency_ms || 0)}
                </span>
              </div>
              <div className="p-3 bg-zinc-950 border border-zinc-800">
                <span className="text-[10px] text-zinc-500 uppercase block">P50 (Median)</span>
                <span className="text-sm font-bold text-zinc-200">
                  {formatDuration(metrics?.query_latency?.p50 || (metrics as any)?.p50_query_latency_ms || 0)}
                </span>
              </div>
              <div className="p-3 bg-zinc-950 border border-zinc-800">
                <span className="text-[10px] text-zinc-500 uppercase block">P95</span>
                <span className="text-sm font-bold text-zinc-200">
                  {formatDuration(metrics?.query_latency?.p95 || (metrics as any)?.p95_query_latency_ms || 0)}
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 border border-zinc-800 bg-zinc-900/40 rounded-sm font-mono space-y-3">
            <span className="text-xs uppercase tracking-wider text-zinc-400 font-semibold block">
              Physical Storage Utilization
            </span>
            <div className="p-4 bg-zinc-950 border border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <HardDrive className="w-5 h-5 text-zinc-400" />
                <div>
                  <div className="text-xs text-zinc-300 font-semibold">Corpus Blob Storage</div>
                  <div className="text-[10px] text-zinc-500">Document uploads directory</div>
                </div>
              </div>
              <div className="text-sm font-bold text-zinc-100">
                {formatBytes((metrics as any)?.storage_used_bytes || 0)}
              </div>
            </div>
            <div className="text-[10px] text-zinc-500 text-right">
              Last Telemetry Snapshot: {lastRefreshed.toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
