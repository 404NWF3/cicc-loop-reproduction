import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, Expand, List, X, ArrowUpRight } from 'lucide-react';
import slides from '../presentation/slides.json';
import { Sources } from '../presentation/Sources';
import '../presentation/presentation.css';

export function PresentationPage() {
  const [params, setParams] = useSearchParams();
  const raw = Number(params.get('slide') ?? 1);
  const index = Number.isFinite(raw)
    ? Math.max(0, Math.min(slides.length - 1, Math.floor(raw) - 1))
    : 0;
  const capture = params.get('capture') === '1';
  const initialSource = useRef(
    `/presentation/deck.html?slide=${index + 1}${capture ? '&capture=1' : ''}`,
  );
  const [ready, setReady] = useState(false);
  const [panel, setPanel] = useState<'notes' | 'sources' | null>(null);
  const [error, setError] = useState('');
  const frame = useRef<HTMLIFrameElement>(null);
  const container = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const send = useCallback((action: string, target?: number) => {
    frame.current?.contentWindow?.postMessage(
      { type: 'research-control', action, index: target },
      window.location.origin,
    );
  }, []);
  const go = useCallback(
    (next: number) => {
      setParams({
        slide: String(Math.max(0, Math.min(slides.length - 1, next)) + 1),
        ...(capture ? { capture: '1' } : {}),
      });
    },
    [capture, setParams],
  );
  const fullscreen = useCallback(async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await container.current?.requestFullscreen();
    } catch {
      setError('当前浏览器不支持全屏，可使用浏览器的全屏菜单。');
    }
  }, []);
  useEffect(() => {
    const receive = (event: MessageEvent) => {
      if (
        event.origin !== window.location.origin ||
        event.source !== frame.current?.contentWindow ||
        event.data?.type !== 'research-deck'
      )
        return;
      if (event.data.action === 'ready') setReady(true);
      if (event.data.action === 'slide' && Number.isInteger(event.data.index)) {
        const next = Math.max(0, Math.min(slides.length - 1, event.data.index));
        const current = Number(new URLSearchParams(window.location.search).get('slide') ?? 1) - 1;
        if (current !== next) go(next);
      }
      if (event.data.action === 'notes') setPanel((p) => (p === 'notes' ? null : 'notes'));
      if (event.data.action === 'fullscreen') void fullscreen();
    };
    window.addEventListener('message', receive);
    return () => window.removeEventListener('message', receive);
  }, [fullscreen, go]);
  useEffect(() => {
    if (ready) send('goto', index);
    document.title = `${String(index + 1).padStart(2, '0')} · ${slides[index].title.replace('\n', '')} | 研究演示`;
    return () => {
      document.title = 'Loop Research';
    };
  }, [index, ready, send]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (
        panel ||
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        (event.target as HTMLElement).closest('input,textarea,select,[contenteditable]')
      )
        return;
      if (event.key === ' ' && (event.target as HTMLElement).closest('button,a')) return;
      if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(event.key)) {
        event.preventDefault();
        go(index + 1);
      }
      if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) {
        event.preventDefault();
        go(index - 1);
      }
      if (event.key === 'Home') {
        event.preventDefault();
        go(0);
      }
      if (event.key === 'End') {
        event.preventDefault();
        go(slides.length - 1);
      }
      if (event.key === 'Escape') send('overview');
      if (event.key.toLowerCase() === 'n') setPanel('notes');
      if (event.key.toLowerCase() === 'f') void fullscreen();
      if (event.key.toLowerCase() === 'p') send('presenter');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [panel, index, go, fullscreen, send]);
  useEffect(() => {
    if (panel) dialog.current?.showModal();
    else dialog.current?.close();
  }, [panel]);
  return (
    <div className={`presentation-app${capture ? ' capture-mode' : ''}`} ref={container}>
      {!capture && (
        <header className="presentation-toolbar">
          <Link to="/" className="presentation-brand">
            <ArrowLeft size={16} />
            <b>
              LOOP <span>RESEARCH</span>
            </b>
          </Link>
          <span className="deck-toolbar-title">研究札记 / 因子工厂</span>
          <nav aria-label="演示工具">
            <button onClick={() => send('overview')}>
              <List size={16} />
              <span>目录</span>
            </button>
            <button onClick={() => setPanel('notes')}>
              <BookOpen size={16} />
              <span>讲稿</span>
            </button>
            <button onClick={() => setPanel('sources')}>资料</button>
            <button onClick={fullscreen} aria-label="全屏放映（F）">
              <Expand size={17} />
            </button>
            <Link to="/mine" className="presentation-live-link">
              现场实验 <ArrowUpRight size={15} />
            </Link>
          </nav>
        </header>
      )}
      <main className="presentation-stage" aria-label="网页研究演示">
        <iframe
          ref={frame}
          src={initialSource.current}
          title="因子工厂 · 14 页研究演示"
          allow="fullscreen"
          onLoad={() => frame.current?.contentWindow?.focus()}
        />
      </main>
      {error && (
        <p className="deck-error" role="status">
          {error}
        </p>
      )}
      <dialog
        className="presentation-drawer"
        ref={dialog}
        onCancel={() => setPanel(null)}
        aria-label={panel === 'notes' ? '当前页讲稿' : '资料与图片来源'}
      >
        <header>
          <h2>
            {panel === 'notes'
              ? `${String(index + 1).padStart(2, '0')} / 演讲提示`
              : '资料与图片来源'}
          </h2>
          <button
            onClick={() => {
              setPanel(null);
              frame.current?.contentWindow?.focus();
            }}
            aria-label="关闭面板"
          >
            <X size={20} />
          </button>
        </header>
        {panel === 'notes' ? (
          <div className="deck-notes">
            <h3>{slides[index].subtitle}</h3>
            <p>{slides[index].notes}</p>
            <hr />
            <small>{slides[index].source}</small>
            <p>按 P 进入演讲模式，可编辑备注、排练计时，并在独立观众窗口放映。</p>
          </div>
        ) : (
          <Sources />
        )}
      </dialog>
    </div>
  );
}
