"use client";

import { useState } from "react";
import { ChevronDown, Plus, type LucideIcon } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

interface ProtoDimensionCardProps {
  title: string;
  icon: LucideIcon;
  entryCount: number;
  collapsedSummary?: string;
  defaultExpanded?: boolean;
  onAdd?: () => void;
  children: React.ReactNode;
}

export function ProtoDimensionCard({
  title,
  icon: Icon,
  entryCount,
  collapsedSummary,
  defaultExpanded = false,
  onAdd,
  children,
}: ProtoDimensionCardProps) {
  const [isOpen, setIsOpen] = useState(defaultExpanded);

  return (
    <Card className="border-border/60 shadow-sm">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 flex h-8 w-8 items-center justify-center rounded-md">
                <Icon className="text-primary h-4 w-4" />
              </div>
              <h3 className="text-foreground font-medium">{title}</h3>
              <Badge variant="secondary" className="text-xs">
                {entryCount}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {onAdd && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-muted-foreground hover:text-foreground h-8 gap-1"
                  onClick={onAdd}
                >
                  <Plus className="h-4 w-4" />
                  添加
                </Button>
              )}
              <CollapsibleTrigger>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ChevronDown
                    className={cn(
                      "text-muted-foreground h-4 w-4 transition-transform",
                      isOpen && "rotate-180",
                    )}
                  />
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
          {!isOpen && collapsedSummary && (
            <p className="text-muted-foreground mt-2 pl-11 text-sm">{collapsedSummary}</p>
          )}
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="px-4 pt-0 pb-4">{children}</CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
