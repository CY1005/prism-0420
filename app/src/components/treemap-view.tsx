"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, Loader2 } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { getPanoramaData } from "@/actions/panorama";

function completionToColorClass(percent: number): string {
  if (percent >= 80) return "bg-emerald-50 border-emerald-200/60 hover:border-emerald-300";
  if (percent >= 40) return "bg-amber-50/70 border-amber-200/60 hover:border-amber-300";
  return "bg-rose-50/70 border-rose-200/60 hover:border-rose-300";
}

function completionToTextColor(percent: number): string {
  if (percent >= 80) return "text-emerald-600";
  if (percent >= 40) return "text-amber-600";
  return "text-rose-500";
}

function completionToDot(percent: number): string {
  if (percent >= 80) return "bg-emerald-400";
  if (percent >= 40) return "bg-amber-400";
  return "bg-rose-400";
}

/** Compute a relative grid size class based on feature count weight */
function getBlockSize(count: number, total: number): string {
  const ratio = count / total;
  if (ratio >= 0.2) return "col-span-2 row-span-2";
  if (ratio >= 0.13) return "col-span-2 row-span-1";
  return "col-span-1 row-span-1";
}

interface TreemapItem {
  nodeId: string;
  name: string;
  type: string;
  featureCount: number;
  completionPercent: number;
}

interface BreadcrumbLevel {
  nodeId: string | null;
  name: string;
}

interface TreemapViewProps {
  projectId: string;
  initialData: TreemapItem[];
}

export function TreemapView({ projectId, initialData }: TreemapViewProps) {
  const router = useRouter();
  const [data, setData] = useState<TreemapItem[]>(initialData);
  const [loading, setLoading] = useState(false);
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbLevel[]>([
    { nodeId: null, name: "项目" },
  ]);

  const totalFeatures = data.reduce((sum, item) => sum + Math.max(item.featureCount, 1), 0);

  const handleCellClick = useCallback(
    async (item: TreemapItem) => {
      if (item.type === "file") {
        // Leaf node — navigate to feature profile
        router.push(`/projects/${projectId}/features/${item.nodeId}`);
        return;
      }

      // Folder — drill down
      setLoading(true);
      const result = await getPanoramaData(projectId, item.nodeId);
      if (result.success) {
        setData(result.data);
        setBreadcrumbs((prev) => [...prev, { nodeId: item.nodeId, name: item.name }]);
      }
      setLoading(false);
    },
    [projectId, router],
  );

  const handleBreadcrumbClick = useCallback(
    async (index: number) => {
      const target = breadcrumbs[index];
      setLoading(true);
      const result = await getPanoramaData(projectId, target.nodeId ?? undefined);
      if (result.success) {
        setData(result.data);
        setBreadcrumbs((prev) => prev.slice(0, index + 1));
      }
      setLoading(false);
    },
    [breadcrumbs, projectId],
  );

  return (
    <div className="space-y-4">
      {/* Breadcrumb + Legend */}
      <div className="flex items-center justify-between">
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumbs.map((level, i) => {
              const isLast = i === breadcrumbs.length - 1;
              return (
                <BreadcrumbItem key={level.nodeId ?? "root"}>
                  {!isLast ? (
                    <>
                      <BreadcrumbLink
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          handleBreadcrumbClick(i);
                        }}
                      >
                        {level.name}
                      </BreadcrumbLink>
                      <BreadcrumbSeparator>
                        <ChevronRight className="h-4 w-4" />
                      </BreadcrumbSeparator>
                    </>
                  ) : (
                    <BreadcrumbPage>{level.name}</BreadcrumbPage>
                  )}
                </BreadcrumbItem>
              );
            })}
          </BreadcrumbList>
        </Breadcrumb>

        <div className="text-muted-foreground flex items-center gap-4 text-xs">
          <span>面积 = 功能项数量</span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm border border-rose-300 bg-rose-100" />
            完善度 &lt; 40%
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm border border-amber-300 bg-amber-100" />
            40% - 80%
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-sm border border-emerald-300 bg-emerald-100" />
            完善度 &gt; 80%
          </span>
        </div>
      </div>

      {/* Treemap grid */}
      <div className="relative min-h-[500px]">
        {loading && (
          <div className="bg-background/60 absolute inset-0 z-10 flex items-center justify-center rounded-lg">
            <Loader2 className="text-muted-foreground h-5 w-5 animate-spin" />
          </div>
        )}
        {data.length === 0 ? (
          <div className="text-muted-foreground flex h-[500px] items-center justify-center text-sm">
            当前层级暂无数据
          </div>
        ) : (
          <div className="grid auto-rows-[140px] grid-cols-5 gap-3">
            {data.map((item) => {
              const sizeClass = getBlockSize(Math.max(item.featureCount, 1), totalFeatures);
              return (
                <div
                  key={item.nodeId}
                  className={`${sizeClass} ${completionToColorClass(item.completionPercent)} flex cursor-pointer flex-col justify-between rounded-lg border-2 p-5 transition-all hover:shadow-md`}
                  onClick={() => handleCellClick(item)}
                >
                  <div>
                    <h3 className="text-foreground font-semibold">{item.name}</h3>
                    <p className="text-muted-foreground mt-1 text-sm">
                      {item.type === "file" ? "功能项" : `${item.featureCount} 个功能项`}
                    </p>
                  </div>
                  <div className="flex items-center justify-between">
                    <span
                      className={`text-2xl font-bold ${completionToTextColor(item.completionPercent)}`}
                    >
                      {item.completionPercent}%
                    </span>
                    <span
                      className={`h-2 w-2 rounded-full ${completionToDot(item.completionPercent)}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
