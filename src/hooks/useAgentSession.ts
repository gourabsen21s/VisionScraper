import { useState, useCallback } from 'react';
import { StepResult } from '@/components/ReasoningPanel';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface SessionInfo {
  session_id: string;
  status: string;
  created_at: string;
}

interface PlanLoopResponse {
  session_id: string;
  goal: string;
  completed: boolean;
  steps: StepResult[];
  reason?: string;
}

export function useAgentSession() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<StepResult[]>([]);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [goal, setGoal] = useState<string>('');

  const createSession = useCallback(async (): Promise<string | null> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video: true, keep_artifacts: true })
      });
      if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
      const data = await res.json();
      setSessionId(data.session_id);
      return data.session_id;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const closeSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API_BASE}/api/sessions/${sessionId}?keep_artifacts=true`, {
        method: 'DELETE'
      });
    } catch (e) {
      console.error('Failed to close session:', e);
    } finally {
      setSessionId(null);
      setSteps([]);
      setCurrentStep(0);
      setGoal('');
    }
  }, [sessionId]);

  const executeGoal = useCallback(async (userGoal: string): Promise<PlanLoopResponse | null> => {
    setIsRunning(true);
    setError(null);
    setGoal(userGoal);
    setSteps([]);
    setCurrentStep(0);

    try {
      let sid = sessionId;
      if (!sid) {
        sid = await createSession();
        if (!sid) throw new Error('Failed to create session');
      }

      const res = await fetch(`${API_BASE}/api/sessions/${sid}/plan_execute_loop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: userGoal,
          max_steps: 25,
          stop_on_low_confidence: true,
          force: false
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Request failed: ${res.statusText}`);
      }

      const data: PlanLoopResponse = await res.json();
      setSteps(data.steps);
      setCurrentStep(data.steps.length);
      return data;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
      return null;
    } finally {
      setIsRunning(false);
    }
  }, [sessionId, createSession]);

  const executeSingleStep = useCallback(async (userGoal: string): Promise<StepResult | null> => {
    setError(null);
    if (!goal) setGoal(userGoal);

    try {
      let sid = sessionId;
      if (!sid) {
        sid = await createSession();
        if (!sid) throw new Error('Failed to create session');
      }

      const res = await fetch(`${API_BASE}/api/sessions/${sid}/plan_execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: userGoal,
          last_actions: steps.map(s => s.action),
          force: false
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Request failed: ${res.statusText}`);
      }

      const data = await res.json();
      const stepResult: StepResult = {
        step: steps.length + 1,
        action: data.action,
        executed: !!data.execution_result,
        execution_result: data.execution_result
      };
      
      setSteps(prev => [...prev, stepResult]);
      setCurrentStep(steps.length + 1);
      return stepResult;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
      return null;
    }
  }, [sessionId, steps, goal, createSession]);

  return {
    sessionId,
    isLoading,
    isRunning,
    error,
    steps,
    currentStep,
    goal,
    createSession,
    closeSession,
    executeGoal,
    executeSingleStep,
    setError
  };
}

