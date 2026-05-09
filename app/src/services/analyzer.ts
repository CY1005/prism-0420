/**
 * Analyzer service client — HTTP calls to FastAPI analyzer microservice.
 * Types mirror api/schemas/analyze.py and api/schemas/test_points.py exactly.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

// ─── Analysis level types ───────────────────────────

export type AnalysisLevel = "L1" | "L2" | "L3";

export const LEVEL_LABELS: Record<AnalysisLevel, string> = {
  L1: "基于当前功能项",
  L2: "基于关联模块",
  L3: "基于全局扫描",
};

// ─── /analyze types ──────────────────────────────────

export interface AnalyzeContext {
  include_modules?: string[];
}

export interface AnalyzeRequest {
  project_id: string;
  requirement_text: string;
  context?: AnalyzeContext;
}

export interface StreamAnalyzeRequest {
  project_id: string;
  requirement_text: string;
  node_id: string;
  analysis_level: AnalysisLevel;
  file_content?: string;
  provider?: string; // ignored by backend, used for future provider switching
}

export interface AffectedModule {
  node_id: string;
  node_name: string;
  node_path: string;
  impact_level: "high" | "medium" | "low";
  reason: string;
}

export interface AnalysisMetadata {
  model: string;
  tokens_used: number;
  analysis_time_ms: number;
}

export interface AnalyzeResponse {
  affected_modules: AffectedModule[];
  completeness_issues: string[];
  suggestions: string[];
  metadata: AnalysisMetadata;
}

// ─── SSE stream chunk types ─────────────────────────

export type StreamChunkType =
  | "modules"
  | "completeness"
  | "suggestions"
  | "metadata"
  | "done"
  | "error";

export interface StreamChunk {
  type: StreamChunkType;
  level: AnalysisLevel;
  data: Partial<AnalyzeResponse> & { error?: string };
}

// ─── Layer result (accumulated per level) ───────────

export interface LayerResult {
  level: AnalysisLevel;
  affected_modules: AffectedModule[];
  completeness_issues: string[];
  suggestions: string[];
  metadata?: AnalysisMetadata;
  isStreaming: boolean;
  isComplete: boolean;
}

// ─── /test-points types ──────────────────────────────

export interface TestPointsRequest {
  project_id: string;
  requirement_text: string;
  affected_modules: string[];
  test_depth: "smoke" | "standard" | "comprehensive";
}

export interface TestPoint {
  id: string;
  title: string;
  description: string;
  priority: "P0" | "P1" | "P2";
  category: "functional" | "boundary" | "exception" | "performance";
  related_module: string;
}

export interface CoverageSummary {
  total: number;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
}

export interface TestPointsResponse {
  test_points: TestPoint[];
  coverage_summary: CoverageSummary;
}

// ─── /health types ───────────────────────────────────

export interface HealthResponse {
  status: string;
  version: string;
  db_connected: boolean;
}

// ─── Comparison types ───────────────────────────────

export interface ComparisonGenerateRequest {
  project_id: string;
  node_ids: string[];
  competitor_ids: string[];
  custom_dimensions?: string[];
  provider?: string;
}

export interface ComparisonCell {
  value: string;
  score: number | null;
}

export interface ComparisonRow {
  dimension: string;
  cells: Record<string, ComparisonCell>;
}

export interface ComparisonColumn {
  id: string;
  name: string;
  type: "self" | "competitor";
}

export interface ComparisonData {
  columns: ComparisonColumn[];
  rows: ComparisonRow[];
}

export interface ComparisonGenerateResponse {
  comparison_id: string;
  data: ComparisonData;
}

export interface ComparisonConclusion {
  type: "advantage" | "disadvantage";
  text: string;
}

export interface BackfillRequest {
  comparison_id: string;
  row_index: number;
  node_id: string;
  competitor_id: string;
}

export interface BackfillResponse {
  competitor_reference_id: string;
  message: string;
}

// ─── Error wrapper ───────────────────────────────────

export type AnalyzerResult<T> = { ok: true; data: T } | { ok: false; error: string };

// ─── API functions ───────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<AnalyzerResult<T>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as T;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `分析服务不可用: ${(e as Error).message}` };
  }
}

async function get<T>(path: string): Promise<AnalyzerResult<T>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}${path}`);
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as T;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `分析服务不可用: ${(e as Error).message}` };
  }
}

// Legacy non-streaming analyze
export async function analyzeRequirement(
  req: AnalyzeRequest,
): Promise<AnalyzerResult<AnalyzeResponse>> {
  return post<AnalyzeResponse>("/api/analyze", req);
}

// SSE streaming analyze
export function analyzeRequirementStream(
  req: StreamAnalyzeRequest,
  onChunk: (chunk: StreamChunk) => void,
  onError: (error: string) => void,
  onDone: () => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const resp = await fetch(`${ANALYZER_BASE_URL}/api/analyze/requirement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      if (!resp.ok) {
        const text = await resp.text();
        onError(`HTTP ${resp.status}: ${text}`);
        return;
      }

      const reader = resp.body?.getReader();
      if (!reader) {
        onError("无法读取响应流");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.slice(6);
          if (jsonStr === "[DONE]") {
            onDone();
            return;
          }
          try {
            const chunk = JSON.parse(jsonStr) as StreamChunk;
            onChunk(chunk);
            if (chunk.type === "done") {
              onDone();
              return;
            }
          } catch {
            // skip malformed chunk
          }
        }
      }
      onDone();
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError(`分析服务不可用: ${(e as Error).message}`);
      }
    }
  })();

  return controller;
}

// Save analysis result
export async function saveAnalysis(
  projectId: string,
  nodeId: string,
  layers: LayerResult[],
): Promise<AnalyzerResult<{ dimension_record_id: string; message: string }>> {
  // Backend expects { analysis_result: str, metadata: dict }
  const analysisResult = JSON.stringify(
    layers.map((l) => ({
      level: l.level,
      affected_modules: l.affected_modules,
      completeness_issues: l.completeness_issues,
      suggestions: l.suggestions,
    })),
  );
  const lastMeta = layers.findLast((l) => l.metadata)?.metadata;
  return post("/api/analyze/save", {
    project_id: projectId,
    node_id: nodeId,
    analysis_result: analysisResult,
    metadata: lastMeta
      ? {
          model: lastMeta.model,
          tokens_used: lastMeta.tokens_used,
          analysis_time_ms: lastMeta.analysis_time_ms,
        }
      : null,
  });
}

// Generate test points via AI
export interface GenerateTestPointsRequest {
  project_id: string;
  node_id: string;
  analysis_result: string;
  test_depth: "smoke" | "standard" | "comprehensive";
}

export interface AITestPoint {
  title: string;
  description: string;
  priority: string;
  category: string;
  steps?: string[];
  expected_result?: string;
}

export interface GenerateTestPointsResponse {
  test_points: AITestPoint[];
  total: number;
}

export async function generateTestPointsAI(
  req: GenerateTestPointsRequest,
): Promise<AnalyzerResult<GenerateTestPointsResponse>> {
  return post<GenerateTestPointsResponse>("/api/analyze/generate-test-points", req);
}

// Legacy test points (kept for backward compat)
export async function generateTestPoints(
  req: TestPointsRequest,
): Promise<AnalyzerResult<TestPointsResponse>> {
  return post<TestPointsResponse>("/api/test-points", req);
}

// Save test points to dimension
export async function saveTestPoints(
  projectId: string,
  nodeId: string,
  testPoints: AITestPoint[],
): Promise<
  AnalyzerResult<{ saved_count: number; dimension_record_ids: string[]; message: string }>
> {
  // Backend expects { test_points: AITestPoint[] } with full objects
  return post("/api/analyze/save-test-points", {
    project_id: projectId,
    node_id: nodeId,
    test_points: testPoints.map((tp) => ({
      title: tp.title,
      description: tp.description,
      priority: tp.priority,
      category: tp.category,
      steps: tp.steps,
      expected_result: tp.expected_result,
    })),
  });
}

// ─── Comparison API functions ───────────────────────

export async function generateComparison(
  req: ComparisonGenerateRequest,
): Promise<AnalyzerResult<ComparisonGenerateResponse>> {
  return post<ComparisonGenerateResponse>("/api/comparison/generate", req);
}

export async function backfillRow(req: BackfillRequest): Promise<AnalyzerResult<BackfillResponse>> {
  return post<BackfillResponse>(`/api/comparison/${req.comparison_id}/backfill`, {
    row_index: req.row_index,
    node_id: req.node_id,
    competitor_id: req.competitor_id,
  });
}

export async function exportComparison(comparisonId: string): Promise<AnalyzerResult<string>> {
  try {
    const resp = await fetch(
      `${ANALYZER_BASE_URL}/api/comparison/${encodeURIComponent(comparisonId)}/export`,
    );
    if (!resp.ok) {
      const text = await resp.text();
      return { ok: false, error: `HTTP ${resp.status}: ${text}` };
    }
    const data = (await resp.json()) as { markdown: string };
    return { ok: true, data: data.markdown };
  } catch (e) {
    return { ok: false, error: `分析服务不可用: ${(e as Error).message}` };
  }
}

// Health check
export async function checkHealth(): Promise<AnalyzerResult<HealthResponse>> {
  return get<HealthResponse>("/health/");
}
