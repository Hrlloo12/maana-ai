"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, Progress, SessionView } from "./api";

export function useSession(id: string | null) {
  const [session, setSession] = useState<SessionView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!id) return;
    try {
      setSession(await api.session(id));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [id]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { session, setSession, error, setError, reload };
}

export function useAgentRun() {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  };
  useEffect(() => stop, []);

  async function run<T>(sessionId: string, action: () => Promise<T>): Promise<T | null> {
    setRunning(true);
    setError(null);
    setProgress({ active: null, completed: [], error: null });
    timer.current = setInterval(async () => {
      try {
        setProgress(await api.progress(sessionId));
      } catch {}
    }, 600);
    try {
      return await action();
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      stop();
      try {
        setProgress(await api.progress(sessionId));
      } catch {}
      setRunning(false);
    }
  }

  return { run, running, progress, error };
}
