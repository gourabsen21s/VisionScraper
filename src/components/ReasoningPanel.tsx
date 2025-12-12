'use client';

import { Brain, CheckCircle2, XCircle, Loader2, MousePointer, Type, Navigation, ScrollText, Hand } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StepResult {
  step: number;
  action: {
    action: string;
    target?: {
      by: string;
      value: string;
    };
    value?: string;
    confidence: number;
    reason: string;
  };
  executed: boolean;
  execution_result?: Record<string, unknown> | null;
}

interface ReasoningPanelProps {
  steps: StepResult[];
  currentStep?: number;
  isRunning?: boolean;
  goal?: string;
  className?: string;
}

const actionIcons: Record<string, React.ReactNode> = {
  click: <MousePointer className="w-3.5 h-3.5" />,
  type: <Type className="w-3.5 h-3.5" />,
  navigate: <Navigation className="w-3.5 h-3.5" />,
  scroll: <ScrollText className="w-3.5 h-3.5" />,
  hover: <Hand className="w-3.5 h-3.5" />,
  noop: <CheckCircle2 className="w-3.5 h-3.5" />,
};

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-green-400';
  if (confidence >= 0.4) return 'text-yellow-400';
  return 'text-red-400';
}

export default function ReasoningPanel({
  steps,
  currentStep,
  isRunning,
  goal,
  className
}: ReasoningPanelProps) {
  return (
    <div className={cn('flex flex-col rounded-xl border border-border/50 bg-card/30 backdrop-blur-sm overflow-hidden', className)}>
      <div className="flex items-center justify-between px-4 py-2 border-b border-border/30 bg-background/50">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-foreground">LLM Reasoning</span>
        </div>
        {isRunning && (
          <div className="flex items-center gap-1.5 text-xs text-accent">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Processing...</span>
          </div>
        )}
      </div>

      {goal && (
        <div className="px-4 py-2 border-b border-border/30 bg-accent/5">
          <p className="text-xs text-muted-foreground">Goal</p>
          <p className="text-sm text-foreground font-medium">{goal}</p>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[400px] scrollbar-thin">
        {steps.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Brain className="w-10 h-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No steps yet</p>
            <p className="text-xs mt-1">Steps will appear as the agent reasons</p>
          </div>
        ) : (
          steps.map((step, index) => {
            const isCurrentStep = currentStep === step.step;
            const icon = actionIcons[step.action.action] || <Brain className="w-3.5 h-3.5" />;
            
            return (
              <div
                key={step.step}
                className={cn(
                  'p-3 rounded-lg border transition-all',
                  isCurrentStep && isRunning
                    ? 'border-accent/50 bg-accent/10'
                    : step.executed
                      ? 'border-green-500/30 bg-green-500/5'
                      : 'border-border/30 bg-background/30'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-5 h-5 rounded-full bg-foreground/10 text-xs font-mono">
                      {step.step}
                    </span>
                    <div className="flex items-center gap-1.5 text-foreground">
                      {icon}
                      <span className="text-sm font-medium capitalize">{step.action.action}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn('text-xs font-mono', getConfidenceColor(step.action.confidence))}>
                      {Math.round(step.action.confidence * 100)}%
                    </span>
                    {step.executed ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    ) : isCurrentStep && isRunning ? (
                      <Loader2 className="w-4 h-4 text-accent animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4 text-muted-foreground/50" />
                    )}
                  </div>
                </div>

                {step.action.target && (
                  <div className="mt-2 text-xs text-muted-foreground font-mono bg-background/50 px-2 py-1 rounded">
                    {step.action.target.by}: {step.action.target.value}
                  </div>
                )}

                {step.action.value && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    <span className="text-foreground/60">Value:</span> {step.action.value}
                  </div>
                )}

                <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                  {step.action.reason}
                </p>
              </div>
            );
          })
        )}
      </div>

      {steps.length > 0 && (
        <div className="px-4 py-2 border-t border-border/30 bg-background/50">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{steps.filter(s => s.executed).length} / {steps.length} steps executed</span>
            {steps.some(s => s.action.action === 'noop') && (
              <span className="text-green-400">Goal completed</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

