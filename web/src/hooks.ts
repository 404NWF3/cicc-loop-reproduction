import { useCallback, useEffect, useState } from 'react';
import { api, apiUrl, messageOf } from './api';
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
    let lastRefresh = 0;
    let candidateCursor = 0;
    let loaded: Candidate[] = [];
    setRun(undefined);
    setCandidates([]);
    setEvents([]);
    setError('');
    const load = async () => {
      if (refreshing || !alive || Date.now() - lastRefresh < 750) return;
      refreshing = true;
      lastRefresh = Date.now();
      try {
        const r = await api<Run>(`/runs/${runId}`);
        if (alive) {
          setRun(r);
          setError('');
        }
        while (alive && candidateCursor < r.cursor) {
          const c = await api<{ items: Candidate[]; next_after: number }>(
            `/runs/${runId}/factors?after=${candidateCursor}&limit=100`,
          );
          if (!c.items.length || c.next_after <= candidateCursor) break;
          candidateCursor = c.next_after;
          loaded = [...loaded, ...c.items];
          if (alive) setCandidates(loaded);
        }
      } catch (e) {
        if (alive) setError(messageOf(e));
      } finally {
        refreshing = false;
      }
    };
    void load();
    const source = new EventSource(apiUrl(`/runs/${runId}/events`), { withCredentials: true });
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
