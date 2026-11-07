"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  FileText,
  Upload,
  Trash2,
  RefreshCw,
  Search,
  Filter,
  Eye,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  X,
  FileCode,
  FileSpreadsheet,
} from "lucide-react";
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
  getDocuments,
  getDocument,
  deleteDocument,
  uploadDocument,
  uploadDocumentsBatch,
} from "@/lib/api";
import { formatBytes, formatDate, formatNumber } from "@/lib/utils";
import type { Document, DocumentDetail, DocumentChunk } from "@/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Inspection modal
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [inspectLoading, setInspectLoading] = useState(false);

  // Upload modal / state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getDocuments({
        page,
        page_size: pageSize,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
        file_type: typeFilter || undefined,
        sort_by: "created_at",
        sort_order: "desc",
      });
      // Handle both documents and items property from backend
      const docs = (resp as any).documents || resp.items || [];
      setDocuments(docs);
      setTotalPages(resp.total_pages || Math.ceil((resp.total || 0) / pageSize) || 1);
      setTotalCount(resp.total || docs.length);
    } catch (err: any) {
      setError(err?.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, typeFilter]);

  useEffect(() => {
    fetchDocuments();
    const interval = setInterval(fetchDocuments, 20000);
    return () => clearInterval(interval);
  }, [fetchDocuments]);

  const handleInspect = async (id: string) => {
    setInspectLoading(true);
    try {
      const doc = await getDocument(id);
      setSelectedDoc(doc);
    } catch (err: any) {
      alert("Failed to load document details: " + (err?.message || "Unknown error"));
    } finally {
      setInspectLoading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Permanently delete document "${name}" and all associated vector chunks?`)) {
      return;
    }
    try {
      await deleteDocument(id);
      if (selectedDoc?.id === id) {
        setSelectedDoc(null);
      }
      fetchDocuments();
    } catch (err: any) {
      alert("Delete failed: " + (err?.message || "Unknown error"));
    }
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const executeUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setUploadError(null);
    try {
      if (selectedFiles.length === 1) {
        await uploadDocument(selectedFiles[0]);
      } else {
        await uploadDocumentsBatch(selectedFiles);
      }
      setSelectedFiles([]);
      setIsUploadOpen(false);
      fetchDocuments();
    } catch (err: any) {
      setUploadError(err?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="w-3 h-3" /> COMPLETED
          </Badge>
        );
      case "processing":
      case "chunking":
      case "embedding":
      case "indexing":
        return (
          <Badge variant="info" className="gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> {status.toUpperCase()}
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

  const getFileTypeIcon = (ext: string) => {
    const clean = ext.replace(".", "").toLowerCase();
    if (clean === "csv") return <FileSpreadsheet className="w-3.5 h-3.5 text-zinc-400" />;
    if (clean === "md" || clean === "json") return <FileCode className="w-3.5 h-3.5 text-zinc-400" />;
    return <FileText className="w-3.5 h-3.5 text-zinc-400" />;
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-zinc-950 text-zinc-100 font-sans">
      {/* Top Header */}
      <div className="h-14 border-b border-zinc-800 px-6 flex items-center justify-between flex-shrink-0 bg-zinc-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-zinc-400" />
          <h1 className="text-sm font-semibold tracking-wider uppercase text-zinc-200">
            Document Repository
          </h1>
          <span className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-sm">
            {totalCount} Documents Indexed
          </span>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchDocuments()}
            disabled={loading}
            className="h-8 gap-1.5 text-xs font-mono border-zinc-800 hover:border-zinc-700 bg-zinc-900"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            REFRESH
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={() => {
              setSelectedFiles([]);
              setUploadError(null);
              setIsUploadOpen(true);
            }}
            className="h-8 gap-1.5 text-xs font-mono bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
          >
            <Upload className="w-3.5 h-3.5" />
            INGEST DOCUMENTS
          </Button>
        </div>
      </div>

      {/* Control Bar: Filters, Search */}
      <div className="p-4 border-b border-zinc-800 flex flex-wrap items-center gap-3 bg-zinc-900/30">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-zinc-500" />
          <Input
            placeholder="Search documents by title or filename..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9 h-8 text-xs font-mono bg-zinc-900/80 border-zinc-800"
          />
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <Filter className="w-3.5 h-3.5 text-zinc-500" />
          <span>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 bg-zinc-900 border border-zinc-800 rounded-sm px-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700 font-mono"
          >
            <option value="">ALL STATUSES</option>
            <option value="completed">COMPLETED</option>
            <option value="processing">PROCESSING</option>
            <option value="pending">PENDING</option>
            <option value="failed">FAILED</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-zinc-400">
          <span>Type:</span>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="h-8 bg-zinc-900 border border-zinc-800 rounded-sm px-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-700 font-mono"
          >
            <option value="">ALL TYPES</option>
            <option value="pdf">PDF</option>
            <option value="docx">DOCX</option>
            <option value="txt">TXT</option>
            <option value="md">MARKDOWN</option>
            <option value="csv">CSV</option>
          </select>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Table View */}
        <div className="flex-1 overflow-auto p-4">
          {error && (
            <div className="mb-4 p-3 border border-red-900/50 bg-red-950/20 text-red-400 text-xs font-mono flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="border border-zinc-800 rounded-sm overflow-hidden bg-zinc-900/40">
            <Table>
              <TableHeader className="bg-zinc-900/80 sticky top-0">
                <TableRow className="border-b border-zinc-800 text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
                  <TableHead className="py-2.5">Document</TableHead>
                  <TableHead className="py-2.5">Type</TableHead>
                  <TableHead className="py-2.5 text-right">Size</TableHead>
                  <TableHead className="py-2.5 text-right">Pages</TableHead>
                  <TableHead className="py-2.5 text-right">Chunks</TableHead>
                  <TableHead className="py-2.5 text-right">Words</TableHead>
                  <TableHead className="py-2.5">Status</TableHead>
                  <TableHead className="py-2.5">Ingested</TableHead>
                  <TableHead className="py-2.5 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && documents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="h-48 text-center text-zinc-500 font-mono text-xs">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                        <span>Querying document registry...</span>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : documents.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="h-48 text-center text-zinc-500 font-mono text-xs">
                      No documents found matching the filter criteria.
                    </TableCell>
                  </TableRow>
                ) : (
                  documents.map((doc: any) => (
                    <TableRow
                      key={doc.id}
                      className="border-b border-zinc-800/60 hover:bg-zinc-800/30 text-xs font-mono transition-colors"
                    >
                      <TableCell className="py-2.5 font-medium text-zinc-200">
                        <div className="flex items-center gap-2">
                          {getFileTypeIcon(doc.file_type)}
                          <span className="truncate max-w-[260px]" title={doc.original_filename || doc.filename}>
                            {doc.title || doc.original_filename || doc.filename}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5 text-zinc-400 uppercase">
                        {doc.file_type.replace(".", "")}
                      </TableCell>
                      <TableCell className="py-2.5 text-right text-zinc-300">
                        {formatBytes(doc.file_size)}
                      </TableCell>
                      <TableCell className="py-2.5 text-right text-zinc-400">
                        {doc.page_count ?? "—"}
                      </TableCell>
                      <TableCell className="py-2.5 text-right text-zinc-200 font-semibold">
                        {doc.chunk_count || 0}
                      </TableCell>
                      <TableCell className="py-2.5 text-right text-zinc-400">
                        {doc.word_count ? formatNumber(doc.word_count) : "—"}
                      </TableCell>
                      <TableCell className="py-2.5">
                        {getStatusBadge(doc.status)}
                      </TableCell>
                      <TableCell className="py-2.5 text-zinc-400 text-[11px]">
                        {formatDate(doc.ingested_at || doc.created_at)}
                      </TableCell>
                      <TableCell className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleInspect(doc.id)}
                            className="h-7 w-7 p-0 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800"
                            title="Inspect document & chunks"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(doc.id, doc.filename)}
                            className="h-7 w-7 p-0 text-zinc-500 hover:text-red-400 hover:bg-red-950/30"
                            title="Delete document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="mt-4 flex items-center justify-between text-xs font-mono text-zinc-400">
            <div>
              Showing {documents.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
              {Math.min(page * pageSize, totalCount)} of {totalCount} records
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={page <= 1}
                className="h-7 text-xs border-zinc-800 bg-zinc-900"
              >
                <ChevronLeft className="w-3.5 h-3.5 mr-1" /> PREV
              </Button>
              <span className="px-2">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={page >= totalPages}
                className="h-7 text-xs border-zinc-800 bg-zinc-900"
              >
                NEXT <ChevronRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </div>
          </div>
        </div>

        {/* Side Panel: Chunk Inspector */}
        {selectedDoc && (
          <div className="w-[480px] border-l border-zinc-800 bg-zinc-900/90 flex flex-col h-full overflow-hidden">
            <div className="h-12 border-b border-zinc-800 px-4 flex items-center justify-between flex-shrink-0 bg-zinc-900">
              <div className="flex items-center gap-2 truncate">
                <FileText className="w-4 h-4 text-zinc-400" />
                <span className="text-xs font-mono font-semibold truncate text-zinc-200">
                  {selectedDoc.filename}
                </span>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="text-zinc-500 hover:text-zinc-300 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Metadata Summary */}
            <div className="p-4 border-b border-zinc-800 bg-zinc-950/40 text-xs font-mono space-y-1.5">
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-zinc-500">ID: </span>
                  <span className="text-zinc-300 truncate">{selectedDoc.id.slice(0, 8)}...</span>
                </div>
                <div>
                  <span className="text-zinc-500">Status: </span>
                  <span className="text-zinc-300">{selectedDoc.status}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Size: </span>
                  <span className="text-zinc-300">{formatBytes(selectedDoc.file_size)}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Chunks: </span>
                  <span className="text-zinc-300">{selectedDoc.chunks?.length || 0}</span>
                </div>
              </div>
              {selectedDoc.error_message && (
                <div className="mt-2 text-red-400 bg-red-950/40 p-2 rounded-sm border border-red-900/40">
                  Error: {selectedDoc.error_message}
                </div>
              )}
            </div>

            {/* Chunks List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-500 font-semibold mb-2">
                Partitioned Chunks ({selectedDoc.chunks?.length || 0})
              </div>
              {selectedDoc.chunks && selectedDoc.chunks.length > 0 ? (
                selectedDoc.chunks.map((chunk: DocumentChunk) => (
                  <div
                    key={chunk.id}
                    className="p-3 bg-zinc-950 border border-zinc-800 rounded-sm text-xs font-mono space-y-2 hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex items-center justify-between text-[11px] text-zinc-400">
                      <span className="text-zinc-300 font-semibold">Chunk #{chunk.chunk_index}</span>
                      <div className="flex gap-2">
                        {chunk.page_number && (
                          <span className="bg-zinc-800/80 px-1.5 py-0.5 rounded-sm">
                            p. {chunk.page_number}
                          </span>
                        )}
                        <span className="bg-zinc-800/80 px-1.5 py-0.5 rounded-sm">
                          {chunk.token_count || 0} tokens
                        </span>
                      </div>
                    </div>
                    <p className="text-zinc-300 text-[12px] leading-relaxed whitespace-pre-wrap font-sans bg-zinc-900/40 p-2 border border-zinc-800/50 rounded-sm max-h-48 overflow-y-auto">
                      {chunk.content}
                    </p>
                  </div>
                ))
              ) : (
                <div className="text-xs font-mono text-zinc-500 text-center py-10">
                  No chunk partitions available for this document.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Ingestion Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-sm w-full max-w-lg p-6 shadow-2xl font-mono">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
              <div className="flex items-center gap-2">
                <Upload className="w-4 h-4 text-zinc-300" />
                <h3 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">
                  Ingest Documents into Verity
                </h3>
              </div>
              <button
                onClick={() => setIsUploadOpen(false)}
                className="text-zinc-500 hover:text-zinc-300"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-4">
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-zinc-700 hover:border-zinc-500 bg-zinc-950/60 p-8 rounded-sm text-center cursor-pointer transition-colors"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  multiple
                  accept=".pdf,.docx,.txt,.md,.csv"
                  className="hidden"
                />
                <Upload className="w-8 h-8 text-zinc-500 mx-auto mb-2" />
                <p className="text-xs text-zinc-300 mb-1">
                  Drag and drop files here, or <span className="underline">browse</span>
                </p>
                <p className="text-[11px] text-zinc-500">
                  Supported formats: PDF, DOCX, TXT, Markdown, CSV (up to 100 MB)
                </p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="mt-4 max-h-40 overflow-y-auto space-y-1">
                  <div className="text-[11px] text-zinc-400 font-semibold mb-1">
                    Staged Files ({selectedFiles.length}):
                  </div>
                  {selectedFiles.map((file, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between text-xs bg-zinc-950 px-2.5 py-1.5 border border-zinc-800"
                    >
                      <span className="truncate max-w-[320px] text-zinc-300">{file.name}</span>
                      <span className="text-[11px] text-zinc-500">{formatBytes(file.size)}</span>
                    </div>
                  ))}
                </div>
              )}

              {uploadError && (
                <div className="mt-3 p-2 border border-red-900 bg-red-950/30 text-red-400 text-xs">
                  {uploadError}
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3 pt-4 border-t border-zinc-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsUploadOpen(false)}
                disabled={uploading}
                className="text-xs border-zinc-800 bg-zinc-900"
              >
                CANCEL
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={executeUpload}
                disabled={uploading || selectedFiles.length === 0}
                className="text-xs bg-zinc-100 text-zinc-950 hover:bg-zinc-200"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" />
                    INGESTING...
                  </>
                ) : (
                  `INGEST ${selectedFiles.length} FILE${selectedFiles.length === 1 ? "" : "S"}`
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
