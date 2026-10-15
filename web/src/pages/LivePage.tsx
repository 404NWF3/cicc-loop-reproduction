import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowUpRight,
  Check,
  Download,
  FlaskConical,
  Pause,
  Play,
  Radio,
  ShieldCheck,
  Square,
} from 'lucide-react';
import { api, messageOf, post } from '../api';
import { ErrorNotice, Loading, Status } from '../components';
import { useResource, useRun } from '../hooks';
import type { Candidate, Run } from '../types';

export interface LiveStatus {
  enabled: boolean;
  model_ready: boolean;
  worker: string;
  snapshot: { assets: number; dates: number; start: string; end: string; sha256: string };
  budget: {
    cost_upper_bound_cny: number;
    hard_cap_cny: number;
    requests: number;
    unresolved_requests: number;
    remaining_upper_bound_cny: number;
  };
}
const number = (v: number | null | undefined, digits = 3) => (v == null ? '—' : v.toFixed(digits));
const percent = (v: number | null | undefined) => (v == null ? '—' : `${(v * 100).toFixed(2)}%`);
const stages: Record<string, string> = {
  generating: '模型生成假设',
  generated: '准备逻辑审查',
  reviewing: '独立逻辑审查',
  evaluating: '逐条回测与筛选',
};

export function NavChart({ candidate }: { candidate: Candidate }) {
  const data = candidate.series ?? [];
  if (!data.length)
    return <p className="live-empty-chart">通过结构检查后，在这里查看现场计算的净值。</p>;
  const minimum = Math.min(1, ...data.map((d) => d.relative)) - 0.01;
  const maximum = Math.max(1, ...data.map((d) => d.relative)) + 0.01;
  const x = (i: number) => 42 + (i / Math.max(1, data.length - 1)) * 490;
  const y = (n: number) => 185 - ((n - minimum) / (maximum - minimum)) * 155;
  return (
    <figure className="live-nav-chart">
      <figcaption>
        开发期相对净值 <span>扣费后 / 等权基准 = 1</span>
      </figcaption>
      <svg
        viewBox="0 0 560 220"
        role="img"
        aria-label="2014 至 2015 年开发筛选期相对净值，五交易日采样"
      >
        {[minimum, 1, maximum].map((n, i) => (
          <g key={i}>
            <line
              x1="42"
              x2="532"
              y1={y(n)}
              y2={y(n)}
              stroke="#dce4e6"
              strokeDasharray={i === 1 ? '4 4' : undefined}
            />
            <text x="3" y={y(n) + 4} fill="#667c85" fontSize="11">
              {n.toFixed(2)}
            </text>
          </g>
        ))}
        <path
          d={data.map((d, i) => `${i ? 'L' : 'M'}${x(i)},${y(d.relative)}`).join(' ')}
          fill="none"
          stroke="#197b7b"
          strokeWidth="2.5"
        />
        <text x="42" y="210" fill="#667c85" fontSize="11">
          2014.01
        </text>
        <text x="486" y="210" fill="#667c85" fontSize="11">
          2015.12
        </text>
      </svg>
    </figure>
  );
}

function CandidateDetail({ candidate }: { candidate?: Candidate }) {
  if (!candidate)
    return (
      <section className="live-detail panel">
        <FlaskConical size={28} />
        <h2>等待第一条假设</h2>
        <p>运行后选择一行，查看公式、净值和每一项筛选依据。</p>
      </section>
    );
  return (
    <section className="live-detail panel" aria-label="选中因子的计算结果">
      <div className="live-section-title">
        <span className="eyebrow">FACTOR INSPECTOR</span>
        <Status state={candidate.status} />
      </div>
      <h2>{candidate.name}</h2>
      <p className="live-origin">
        {candidate.origin === 'archive_seed'
          ? '已知研究种子 · 本次现场复算'
          : candidate.origin === 'model'
            ? 'DeepSeek 新假设'
            : '程序生成的新候选'}
      </p>
      <code className="live-expression">{candidate.expression}</code>
      <p>{candidate.hypothesis}</p>
      <p className="live-review">
        <strong>逻辑审查：</strong>
        {candidate.review
          ? `${({ approve: '通过', reject: '拒绝', uncertain: '不确定' } as Record<string, string>)[candidate.review.verdict] ?? candidate.review.verdict} · ${candidate.review.explanation}`
          : '本次未调用模型审查；表达式由程序检查。'}
      </p>
      <div className="live-numbers">
        <div>
          <span>发现期 IC</span>
          <strong>{number(candidate.discovery_ic)}</strong>
        </div>
        <div>
          <span>筛选期 Calmar</span>
          <strong>{number(candidate.metrics?.calmar, 2)}</strong>
        </div>
        <div>
          <span>年化超额</span>
          <strong>{percent(candidate.periods?.selection.annual_excess)}</strong>
        </div>
      </div>
      <NavChart candidate={candidate} />
      <div className="live-section-title">
        <h3>11 项联合门槛</h3>
        <small>
          冻结方向 {candidate.direction === -1 ? '−1' : candidate.direction === 1 ? '+1' : '—'}
        </small>
      </div>
      <div className="live-gates">
        {candidate.gates.map((g) => (
          <div key={g.id} className={`live-gate ${g.status}`}>
            <span>
              {g.status === 'passed' ? (
                <Check size={13} />
              ) : g.status === 'not_applicable' ? (
                '—'
              ) : (
                '·'
              )}
            </span>
            <div>
              <strong>
                {g.id} {g.name}
              </strong>
              <small>
                {g.status === 'not_applicable'
                  ? '首个因子：相关性不适用'
                  : `${number(g.value)} ${g.operator} ${g.threshold}`}
              </small>
            </div>
          </div>
        ))}
      </div>
      <p className="live-reason">{candidate.reason}</p>
    </section>
  );
}

export function LiveRun({ id }: { id: string }) {
  const { run, setRun, candidates, events, connection, error } = useRun(id);
  const [selected, setSelected] = useState('');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);
  const [candidatePage, setCandidatePage] = useState<number | null>(null);
  const pageCount = Math.max(1, Math.ceil(candidates.length / 60));
  const pageIndex = candidatePage === null ? pageCount - 1 : Math.min(candidatePage, pageCount - 1);
  const visibleCandidates = candidates.slice(pageIndex * 60, (pageIndex + 1) * 60);
  const candidate = candidates.find((c) => c.id === selected) ?? candidates.at(-1);
  const browsePage = (page: number | null) => {
    setCandidatePage(page);
    setSelected(page === null ? '' : (candidates[page * 60]?.id ?? ''));
  };
  const action = async (name: string) => {
    setBusy(true);
    setActionError('');
    try {
      setRun(await post<Run>(`/runs/${id}/${name}`));
    } catch (e) {
      setActionError(messageOf(e));
    } finally {
      setBusy(false);
    }
  };
  const download = async () => {
    try {
      const report = await api(`/runs/${id}/report`);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }),
      );
      const a = document.createElement('a');
      a.href = url;
      a.download = `research-${id}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setActionError(messageOf(e));
    }
  };
  if (!run)
    return (
      <>
        <ErrorNotice message={error} />
        <Loading />
      </>
    );
  const novel = run.counts.novel;
  return (
    <div className="live-workspace">
      <section className="panel live-progress">
        <div className="live-section-title">
          <div>
            <span className="eyebrow">RUN · {id.slice(0, 8)}</span>
            <h2>{run.config.name}</h2>
          </div>
          <Status state={run.state} />
        </div>
        <div className="live-counts" aria-label="现场实验统计">
          <div>
            <span>已处理</span>
            <strong>
              {run.cursor}
              <small> / {run.target}</small>
            </strong>
          </div>
          <div>
            <span>真实回测</span>
            <strong>{run.counts.backtested}</strong>
          </div>
          <div>
            <span>本次入库</span>
            <strong>{run.counts.accepted}</strong>
            <small>其中新候选 {novel}</small>
          </div>
          <div>
            <span>模型调用</span>
            <strong>{run.counts.model_calls}</strong>
            <small>{run.counts.tokens.toLocaleString()} tokens</small>
          </div>
        </div>
        <progress value={run.cursor} max={run.target} aria-label="实时挖掘进度" />
        <div className="live-run-budget">
          <span>
            本次模型费用上界 <b>¥{number(Number(run.checkpoint.model_cost_upper_cny ?? 0))}</b> / ¥
            {run.config.max_model_cny ?? 0.5}
          </span>
          <span>
            {run.config.generator === 'deepseek'
              ? `模型批次 ${run.checkpoint.model_batch ?? 0} · `
              : ''}
            时间上限 {Math.round(run.config.max_seconds / 60)} 分钟
          </span>
        </div>
        <div className="live-section-title">
          <p role="status">
            <Radio size={13} />{' '}
            {run.state === 'completed'
              ? '本次任务已完成'
              : (stages[String(run.checkpoint.stage)] ?? '等待工作进程')}
          </p>
          <div className="button-group">
            {['queued', 'running'].includes(run.state) && (
              <button
                className="button outline compact"
                disabled={busy}
                onClick={() => action('pause')}
              >
                <Pause size={14} />
                暂停
              </button>
            )}
            {['paused', 'interrupted'].includes(run.state) && (
              <button
                className="button navy compact"
                disabled={busy}
                onClick={() => action('resume')}
              >
                <Play size={14} />
                继续
              </button>
            )}
            {['queued', 'running', 'paused', 'pause_requested', 'interrupted'].includes(
              run.state,
            ) && (
              <button
                className="button outline compact"
                disabled={busy}
                onClick={() => action('stop')}
              >
                <Square size={13} />
                停止
              </button>
            )}
            <button className="button outline compact" onClick={download}>
              <Download size={14} />
              导出
            </button>
          </div>
        </div>
        <ErrorNotice message={error || actionError || run.error || ''} />
      </section>
      <div className="live-results-grid">
        <div>
          <section className="panel live-candidates">
            <div className="live-section-title">
              <h2>候选序列</h2>
              <small>点击查看计算依据</small>
            </div>
            <div className="live-candidate-list">
              {candidates.length ? (
                visibleCandidates.map((c) => (
                  <button
                    key={c.id}
                    className={`live-candidate ${candidate?.id === c.id ? 'active' : ''}`}
                    onClick={() => setSelected(c.id)}
                  >
                    <span className="mono">{String(c.ordinal).padStart(2, '0')}</span>
                    <div>
                      <strong>{c.name}</strong>
                      <code>{c.expression}</code>
                      <small>
                        {c.origin === 'archive_seed'
                          ? '已知种子复算'
                          : c.origin === 'model'
                            ? '模型新假设'
                            : '新候选'}
                      </small>
                    </div>
                    <Status state={c.status} />
                  </button>
                ))
              ) : (
                <p className="live-empty-list">候选正在准备，事件流会显示当前步骤。</p>
              )}
            </div>
            {pageCount > 1 && (
              <nav className="live-pagination" aria-label="候选分页">
                <button
                  type="button"
                  disabled={pageIndex === 0}
                  onClick={() => browsePage(pageIndex - 1)}
                >
                  上一页
                </button>
                <span>
                  {pageIndex + 1} / {pageCount} 页
                </span>
                <button
                  type="button"
                  disabled={pageIndex === pageCount - 1}
                  onClick={() => browsePage(pageIndex + 1)}
                >
                  下一页
                </button>
                <button type="button" onClick={() => browsePage(null)}>
                  跟随最新
                </button>
              </nav>
            )}
          </section>
          <section className="panel live-events">
            <div className="live-section-title">
              <h2>运行日志</h2>
              <span className="live-connection">
                {connection === 'connected' ? '已连接' : '重新连接中'}
              </span>
            </div>
            <ol>
              {events
                .slice(-7)
                .reverse()
                .map((e) => (
                  <li key={e.id}>
                    <time>
                      {new Date(e.created_at).toLocaleTimeString('zh-CN', { hour12: false })}
                    </time>
                    <span>{e.payload.message ?? e.type}</span>
                  </li>
                ))}
            </ol>
          </section>
        </div>
        <CandidateDetail candidate={candidate} />
      </div>
    </div>
  );
}

export function LivePage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const status = useResource<LiveStatus>('/live/status', 3000);
  const history = useResource<{ items: Run[] }>('/runs', 4000);
  const [generator, setGenerator] = useState<'local' | 'deepseek'>('local');
  const [count, setCount] = useState(1200);
  const [modelBudget, setModelBudget] = useState(5);
  const [minutes, setMinutes] = useState(60);
  const [seed, setSeed] = useState(42);
  const [token, setToken] = useState(sessionStorage.getItem('loop-research-token') ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const start = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (generator === 'deepseek') sessionStorage.setItem('loop-research-token', token);
      const run = await post<Run>(
        '/runs',
        {
          name: `现场研究 · ${generator === 'local' ? '本地搜索' : 'DeepSeek'}`,
          mode: 'live',
          generator,
          rounds: Math.ceil(count / 12),
          batch_size: 12,
          max_candidates: count,
          max_seconds: minutes * 60,
          seed,
          fsa_enabled: true,
          max_model_cny: modelBudget,
        },
        { 'Idempotency-Key': crypto.randomUUID() },
      );
      await post(`/runs/${run.id}/start`);
      navigate(`/mine/${run.id}`);
      history.refresh();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="page-width live-page">
      <Link to="/presentation?slide=13" className="back-link">
        <ArrowLeft size={14} />
        返回研究演示
      </Link>
      <div className="live-page-heading">
        <div>
          <span className="eyebrow">THE LIVE LAB</span>
          <h1>让假设，当场接受检验。</h1>
          <p>生成公式 → 检查逻辑 → 历史回测 → 联合筛选。每一步都留下证据。</p>
        </div>
        <span className="tag">
          <Radio size={13} />
          {status.data?.worker === 'online' ? '研究引擎在线' : '等待研究引擎'}
        </span>
      </div>
      <div className="live-data-note">
        <ShieldCheck size={18} />
        <p>
          <strong>真实计算，历史快照。</strong>50 股 · 2012–2013 发现期 · 2014–2015 开发筛选期 ·
          单边成本 0.1%。本地模式先复算 6
          个已知种子，再生成新候选。结果不代表实时行情或独立样本外收益。
        </p>
      </div>
      <form className="panel live-launch" onSubmit={start}>
        <div className="live-mode-select" role="group" aria-label="候选生成方式">
          <button
            type="button"
            className={generator === 'local' ? 'active' : ''}
            onClick={() => setGenerator('local')}
          >
            <FlaskConical size={18} />
            <span>
              <strong>本地搜索</strong>
              <small>无需密钥 · 真实回测 · 免费</small>
            </span>
          </button>
          <button
            type="button"
            className={generator === 'deepseek' ? 'active' : ''}
            onClick={() => setGenerator('deepseek')}
          >
            <ShieldCheck size={18} />
            <span>
              <strong>DeepSeek 引导</strong>
              <small>逐批生成 · 独立审查 · 结果反馈</small>
            </span>
          </button>
        </div>
        <label className="field">
          候选数
          <select
            aria-label="候选数"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          >
            {[24, 36, 120, 300, 600, 1200].map((n) => (
              <option key={n} value={n}>
                {n.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          时间上限
          <select
            aria-label="时间上限"
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
          >
            {[15, 30, 60].map((n) => (
              <option key={n} value={n}>
                {n} 分钟
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          随机种子
          <input
            type="number"
            min="0"
            max="2147483647"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
          />
        </label>
        {generator === 'deepseek' && (
          <label className="field">
            单次模型预算
            <select
              aria-label="单次模型预算"
              value={modelBudget}
              onChange={(e) => setModelBudget(Number(e.target.value))}
            >
              {[1, 3, 5, 10].map((n) => (
                <option key={n} value={n}>
                  ¥{n.toFixed(2)}
                </option>
              ))}
            </select>
          </label>
        )}
        {generator === 'deepseek' && (
          <label className="field live-password">
            演示口令
            <input
              type="password"
              autoComplete="off"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="服务端设置的演示口令"
            />
          </label>
        )}
        <button
          className="button navy"
          disabled={
            busy ||
            !status.data?.enabled ||
            status.data.worker !== 'online' ||
            (generator === 'deepseek' && !status.data.model_ready)
          }
        >
          <Play size={16} />
          {busy ? '正在启动…' : '开始现场挖掘'}
        </button>
        <p className="live-launch-note">
          {generator === 'deepseek'
            ? `计划处理 ${count.toLocaleString()} 个候选，每批最多 12 个。每批重新生成、独立审查，并反馈开发期结果。单次预算 ¥${modelBudget}，达到候选、时间或费用上限即停止，按实际调用计费。`
            : `计划处理 ${count.toLocaleString()} 个候选，本地计算免费。大任务可保持运行、暂停或刷新后继续查看。`}
        </p>
        {generator === 'deepseek' && !status.data?.model_ready && (
          <p className="live-launch-note">
            模型模式需在服务端配置 DeepSeek 密钥和演示口令。本地搜索现在即可运行。
          </p>
        )}
        <ErrorNotice message={error || status.error} />
      </form>
      <div className="live-budget-line">
        <span>
          共享账本累计保守费用 <b>¥{number(status.data?.budget.cost_upper_bound_cny)}</b> / ¥
          {status.data?.budget.hard_cap_cny ?? 40}
          {' · '}剩余额度 ¥{number(status.data?.budget.remaining_upper_bound_cny, 2)}
        </span>
        <span>每次最多 1,200 个候选 · 单任务顺序计算 · 可暂停与恢复</span>
      </div>
      {runId ? (
        <LiveRun key={runId} id={runId} />
      ) : (
        <section className="live-intro-grid">
          <div>
            <span className="eyebrow">01 / HYPOTHESIS</span>
            <h2>一条公式，一个可证伪的想法。</h2>
            <p>从已知种子出发探索新时间尺度，或让模型提出新的价量假设。</p>
          </div>
          <div>
            <span className="eyebrow">02 / EVIDENCE</span>
            <h2>看到它为什么通过，为什么失败。</h2>
            <p>选择候选即可检查开发期净值、IC 和全部 11 项门槛。</p>
          </div>
          <div>
            <span className="eyebrow">03 / RESEARCH</span>
            <h2>把运行过程，变成研究记录。</h2>
            <p>暂停、刷新、继续，检查点仍在。结束后导出完整结果。</p>
          </div>
        </section>
      )}
      {!!history.data?.items.filter((r) => r.config.mode === 'live').length && (
        <section className="live-history">
          <h2>最近的现场研究</h2>
          {history.data.items
            .filter((r) => r.config.mode === 'live')
            .slice(0, 6)
            .map((r) => (
              <Link key={r.id} to={`/mine/${r.id}`}>
                <span>{r.config.name}</span>
                <small>
                  {r.cursor}/{r.target} 候选 · {r.counts.accepted} 入库
                </small>
                <Status state={r.state} />
                <ArrowUpRight size={15} />
              </Link>
            ))}
        </section>
      )}
    </main>
  );
}
