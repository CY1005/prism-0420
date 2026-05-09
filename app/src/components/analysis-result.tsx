"use client";

import { AlertTriangle, CheckCircle, Lightbulb, Loader2, Info } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { type LayerResult, type AnalysisLevel, LEVEL_LABELS } from "@/services/analyzer";

interface AnalysisResultProps {
  layer: LayerResult;
}

const levelColors: Record<AnalysisLevel, string> = {
  L1: "bg-blue-100 text-blue-700 border-blue-200",
  L2: "bg-purple-100 text-purple-700 border-purple-200",
  L3: "bg-orange-100 text-orange-700 border-orange-200",
};

export function AnalysisResult({ layer }: AnalysisResultProps) {
  const directModules = layer.affected_modules.filter((m) => m.impact_level === "high");
  const indirectModules = layer.affected_modules.filter((m) => m.impact_level !== "high");

  return (
    <div className="space-y-4">
      {/* Layer Header */}
      <div className="flex items-center gap-2">
        <Badge variant="outline" className={levelColors[layer.level]}>
          {layer.level}
        </Badge>
        <span className="text-muted-foreground text-sm">{LEVEL_LABELS[layer.level]}</span>
        {layer.isStreaming && <Loader2 className="text-primary ml-auto h-3.5 w-3.5 animate-spin" />}
      </div>

      {/* Impact Analysis */}
      {(layer.affected_modules.length > 0 || layer.isComplete) && (
        <Card className="border-border/60 p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-500" />
            <h3 className="font-medium">影响范围</h3>
            <Badge variant="outline" className="ml-auto text-xs">
              {layer.affected_modules.length} 个模块
            </Badge>
          </div>
          <div className="space-y-3">
            {directModules.length > 0 && (
              <div>
                <p className="text-muted-foreground mb-2 text-xs">直接影响</p>
                <div className="space-y-2">
                  {directModules.map((mod) => (
                    <div key={mod.node_id} className="flex items-start gap-2">
                      <Badge className="bg-primary/10 text-primary hover:bg-primary/10 shrink-0">
                        直接
                      </Badge>
                      <div>
                        <span className="text-sm font-medium">
                          {mod.node_path || mod.node_name}
                        </span>
                        <p className="text-muted-foreground text-xs">{mod.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {indirectModules.length > 0 && (
              <div>
                <p className="text-muted-foreground mb-2 text-xs">间接影响</p>
                <div className="space-y-2">
                  {indirectModules.map((mod) => (
                    <div key={mod.node_id} className="flex items-start gap-2">
                      <Badge variant="secondary" className="shrink-0">
                        间接
                      </Badge>
                      <div>
                        <span className="text-sm font-medium">
                          {mod.node_path || mod.node_name}
                        </span>
                        <p className="text-muted-foreground text-xs">{mod.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {layer.isComplete && layer.affected_modules.length === 0 && (
              <p className="text-muted-foreground text-sm">未发现受影响的模块</p>
            )}
          </div>
        </Card>
      )}

      {/* Completeness Issues */}
      {(layer.completeness_issues.length > 0 || layer.isComplete) && (
        <Card className="border-border/60 p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <h3 className="font-medium">完整性评估</h3>
          </div>
          <div className="space-y-2">
            {layer.completeness_issues.length > 0
              ? layer.completeness_issues.map((issue, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-yellow-500" />
                    <span className="text-muted-foreground">{issue}</span>
                  </div>
                ))
              : layer.isComplete && (
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                    <span>需求描述完整，未发现明显遗漏</span>
                  </div>
                )}
          </div>
        </Card>
      )}

      {/* Suggestions */}
      {layer.suggestions.length > 0 && (
        <Card className="border-border/60 p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-yellow-500" />
            <h3 className="font-medium">建议</h3>
          </div>
          <div className="space-y-2">
            {layer.suggestions.map((suggestion, index) => (
              <div key={index} className="flex items-start gap-2 text-sm">
                <span className="text-muted-foreground shrink-0">{index + 1}.</span>
                <span>{suggestion}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Metadata */}
      {layer.metadata && layer.isComplete && (
        <div className="text-muted-foreground flex items-center gap-4 pt-1 text-xs">
          <div className="flex items-center gap-1">
            <Info className="h-3 w-3" />
            <span>模型: {layer.metadata.model}</span>
          </div>
          <span>耗时: {layer.metadata.analysis_time_ms}ms</span>
          {layer.metadata.tokens_used > 0 && <span>Token: {layer.metadata.tokens_used}</span>}
        </div>
      )}
    </div>
  );
}
