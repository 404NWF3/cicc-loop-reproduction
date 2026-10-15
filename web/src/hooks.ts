import { useCallback, useEffect, useState } from 'react';
import { api, messageOf } from './api';
import type { Candidate, Run, RunEvent } from './types';

export function useResource<T>(path: string, interval = 0) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  useEffect(() => {
    setData(undefined);
    setError('');
  }, [path]);
  useEffect(() => {
    const abort = new AbortController();
    const load = () =>
      api<T>(path, { signal: abort.signal })
        .then((value) => {
          if (!abort.signal.aborted) {
            setData(value);
            setError('');
          }
        })
        .catch((e) => {
          if (!abort.signal.aborted) setError(messageOf(e));
        });
    void load();
    const timer = interval ? window.setInterval(load, interval) : undefined;
    return () => {
      abort.abort();
      if (timer) clearInterval(timer);
    };
  }, [path, interval, version]);
  return { data, error, refresh };
}

export function useRun(runId: string) {
  const [run, setRun] = useState<Run>();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connection, setConnection] = useState('connecting');
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    let refreshing = false;
    setRun(undefined);
    setCandidates([]);
    setEvents([]);
    setError('');
    const load = async () => {
      if (refreshing) return;
      refreshing = true;
      try {
        const [r, c] = await Promise.all([
          api<Run>(`/runs/${runId}`),
          api<{ items: Candidate[] }>(`/runs/${runId}/factors`),
        ]);
        if (alive) {
          setRun(r);
          setCandidates(c.items);
          setError('');
        }
      } catch (e) {
        if (alive) setError(messageOf(e));
      } finally {
        refreshing = false;
      }
    };
    void load();
    const source = new EventSource(`/api/v1/runs/${runId}/events`);
    source.onopen = () => {
      if (alive) setConnection('connected');
    };
    source.onerror = () => {
      if (alive) setConnection('reconnecting');
    };
    source.onmessage = (message) => {
      if (!alive) return;
      try {
        const event = JSON.parse(message.data) as RunEvent;
        setEvents((previous) =>
          [...new Map([...previous, event].map((e) => [e.id, e])).values()].slice(-200),
        );
        void load();
      } catch {
        setConnection('reconnecting');
      }
    };
    const timer = window.setInterval(load, 1500);
    return () => {
      alive = false;
      source.close();
      clearInterval(timer);
    };
  }, [runId]);
  return { run, setRun, candidates, events, connection, error };
}
