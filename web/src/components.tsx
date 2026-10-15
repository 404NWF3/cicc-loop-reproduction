import { useEffect, useRef, type ReactNode } from 'react';
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleAlert,
  LoaderCircle,
  RotateCw,
  X,
} from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { stateLabels, stages } from './content';

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="brand" aria-label="Loop Research 首页">
      <span className="brand-mark">
        <RotateCw size={24} strokeWidth={1.5} />
      </span>
      <span>
        <strong>LOOP RESEARCH</strong>
        {!compact && <small>因子发现实验室</small>}
      </span>
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <Brand />
        <nav aria-label="网站导航">
          <NavLink to="/" end>
            研究概览
          </NavLink>
          <NavLink to="/research">原理与方法</NavLink>
          <NavLink to="/experiments">实验记录</NavLink>
        </nav>
        <Link className="button navy compact" to="/console">
          进入控制台 <ArrowUpRight size={15} />
        </Link>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div>
        <Brand />
        <p>基于公开资料的独立复现 · 让研究过程可验证、可追溯。</p>
      </div>
      <div className="footer-links">
        <Link to="/research">方法与来源</Link>
        <a
          href="https://github.com/404NWF3/cicc-loop-reproduction"
          target="_blank"
          rel="noreferrer"
        >
          GitHub <ArrowUpRight size={14} />
        </a>
        <span>RESEARCH, IN A LOOP.</span>
      </div>
    </footer>
  );
}

export function Status({ state }: { state: string }) {
  return (
    <span className={`status status-${state}`}>
      <span className="status-dot" />
      {stateLabels[state] || state}
    </span>
  );
}

export function ErrorNotice({ message, retry }: { message?: string; retry?: () => void }) {
  if (!message) return null;
  return (
    <div className="error-notice" role="alert">
      <CircleAlert size={17} />
      <span>{message}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          重试
        </button>
      )}
    </div>
  );
}

export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={20} className="spin" /> 正在加载…
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function SectionHeading({
  number,
  eyebrow,
  title,
  children,
}: {
  number: string;
  eyebrow: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <span className="section-number">{number}</span>
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {children && <p>{children}</p>}
      </div>
    </div>
  );
}

export function LoopDiagram({
  interactive = false,
  active = 0,
  onChange,
}: {
  interactive?: boolean;
  active?: number;
  onChange?: (n: number) => void;
}) {
  return (
    <div
      className={`loop-diagram ${interactive ? 'interactive' : ''}`}
      aria-label="生成、审查、验证、反馈循环"
    >
      <div className="diagram-caption">
        <span className="mini-dot" /> LOOP ENGINEERING <span>01—04</span>
      </div>
      <div className="diagram-steps">
        {stages.map((stage, i) => {
          const content = (
            <>
              <span className="step-number">0{i + 1}</span>
              <span>
                <small>{stage.en}</small>
                <strong>{stage.name}</strong>
              </span>
              {i === 3 ? <RotateCw size={18} /> : <ChevronRight size={18} />}
            </>
          );
          return interactive ? (
            <button
              key={stage.en}
              className={`diagram-step ${active === i ? 'selected' : ''}`}
              onClick={() => onChange?.(i)}
              aria-pressed={active === i}
            >
              {content}
            </button>
          ) : (
            <div key={stage.en} className={`diagram-step ${i === 2 ? 'selected' : ''}`}>
              {content}
            </div>
          );
        })}
      </div>
      <div className="diagram-return">
        <span />
        验证结果，成为下一轮的起点
        <RotateCw size={13} />
      </div>
      {!interactive && (
        <div className="formula-note">
          <div>
            <span className="mini-dot" /> HYPOTHESIS → EXPRESSION
          </div>
          <code>
            sub(ts_mean(gap, 10),
            <br />
            &nbsp;&nbsp;&nbsp;&nbsp;ts_mean(intraday_range, 10))
          </code>
          <small>公式示例 · 尚未进行市场验证</small>
        </div>
      )}
    </div>
  );
}

export function Modal({
  title,
  children,
  onClose,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onClose();
      }}
      aria-labelledby="modal-title"
    >
      <div className="modal-heading">
        <div>
          <span className="eyebrow">NEW RESEARCH LOOP</span>
          <h2 id="modal-title">{title}</h2>
        </div>
        <button className="icon-button" aria-label="关闭" onClick={onClose} disabled={busy}>
          <X size={21} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function CheckItem({ children }: { children: ReactNode }) {
  return (
    <span className="check-item">
      <Check size={14} />
      {children}
    </span>
  );
}

export const dateTime = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value));
