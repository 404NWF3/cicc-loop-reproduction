import { useRef, useState, type FormEvent } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Braces,
  Check,
  CircleHelp,
  Clock3,
  Database,
  Download,
  FileCode2,
  Fingerprint,
  FlaskConical,
  LayoutDashboard,
  LoaderCircle,
  Pause,
  Play,
  Plus,
  Radio,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Square,
  Terminal,
  Workflow,
} from 'lucide-react';
import { Link, NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { api, messageOf, post } from '../api';
import { Brand, dateTime, EmptyState, ErrorNotice, Loading, Modal, Status } from '../components';
import { strategyName } from '../content';
import { useResource, useRun } from '../hooks';
import type {
  Candidate,
  Capabilities,
  Dataset,
  ModelStatus,
  Run,
  RunConfig,
  Validation,
} from '../types';

function FixtureNotice() {
  return (
    <div className="fixture-notice">
      <FlaskConical size={17} />
      <span>
        <strong>本地流程演示</strong> · 不调用大模型，不加载市场数据，不生成回测收益。
      </span>
    </div>
  );
}

export function ConsoleLayout() {
  const health = useResource<{ worker: string }>('/health', 5000);
  return (
    <div className="console-layout">
      <aside className="console-sidebar">
        <Brand compact />
        <div className="sidebar-caption">RESEARCH WORKSPACE</div>
        <nav aria-label="控制台导航">
          <NavLink to="/console" end>
            <LayoutDashboard size={18} />
            工作台
          </NavLink>
          <NavLink to="/console/settings">
            <Settings2 size={18} />
            数据与模型
          </NavLink>
          <NavLink to="/experiments">
            <FlaskConical size={18} />
            实验记录
            <ArrowUpRight size={13} />
          </NavLink>
          <NavLink to="/research">
            <BookIcon />
            原理与方法
            <ArrowUpRight size={13} />
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-mode">
            <span className="mini-dot" /> SCAFFOLD · v0.1
          </div>
          <p>
            先把研究流程连接起来。
            <br />
            每一步，都留下依据。
          </p>
          <Link to="/">
            返回研究概览 <ArrowUpRight size={13} />
          </Link>
        </div>
      </aside>
      <div className="console-main">
        <header className="console-topbar">
          <span>
            <Workflow size={16} />
            因子发现 / 研究工作区
          </span>
          <span className="worker-state">
            <i className={health.data?.worker === 'online' && !health.error ? 'online' : ''} />
            {health.error
              ? '后端未连接'
              : health.data?.worker === 'online'
                ? 'Worker 已连接'
                : 'Worker 待启动'}
          </span>
        </header>
        <div className="console-content">
          <Outlet />
        </div>
        <footer className="console-footer">
          LOOP RESEARCH <span>独立复现 · 所有演示记录均保存于本地</span>
        </footer>
      </div>
    </div>
  );
}

function BookIcon() {
  return <FileCode2 size={18} />;
}

function NewRunModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [config, setConfig] = useState<RunConfig>({
    name: '我的第一次 Loop',
    mode: 'fixture',
    rounds: 3,
    batch_size: 6,
    seed: 42,
    fsa_enabled: true,
    max_candidates: 100,
    max_seconds: 600,
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const key = useRef(crypto.randomUUID());
  const update = (value: Partial<RunConfig>) => {
    setConfig((c) => ({ ...c, ...value }));
    key.current = crypto.randomUUID();
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const created = await post<Run>('/runs', config, { 'Idempotency-Key': key.current });
      await post<Run>(`/runs/${created.id}/start`);
      onClose();
      navigate(`/console/runs/${created.id}`);
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="新建演示任务" onClose={onClose} busy={busy}>
      <form onSubmit={submit}>
        <div className="mode-choice">
          <span className="selected-radio">
            <Check size={13} />
          </span>
          <div>
            <strong>本地流程演示</strong>
            <p>使用预置规则生成候选，检查结构与任务流转。</p>
          </div>
          <span className="tag">无需密钥</span>
        </div>
        <fieldset disabled={busy}>
          <label className="field">
            任务名称
            <input
              required
              value={config.name}
              maxLength={80}
              onChange={(e) => update({ name: e.target.value })}
            />
          </label>
          <div className="form-grid">
            <label className="field">
              迭代轮数
              <input
                type="number"
                required
                min={1}
                max={50}
                value={config.rounds}
                onChange={(e) => update({ rounds: Number(e.target.value) })}
              />
            </label>
            <label className="field">
              每轮候选数
              <input
                type="number"
                required
                min={1}
                max={20}
                value={config.batch_size}
                onChange={(e) => update({ batch_size: Number(e.target.value) })}
              />
            </label>
            <label className="field">
              随机种子
              <input
                type="number"
                required
                min={0}
                max={2147483647}
                value={config.seed}
                onChange={(e) => update({ seed: Number(e.target.value) })}
              />
            </label>
            <label className="field">
              候选尝试上限
              <input
                type="number"
                required
                min={1}
                max={1000}
                value={config.max_candidates}
                onChange={(e) => update({ max_candidates: Number(e.target.value) })}
              />
            </label>
            <label className="field">
              时间上限（秒）
              <input
                type="number"
                required
                min={5}
                max={1800}
                value={config.max_seconds}
                onChange={(e) => update({ max_seconds: Number(e.target.value) })}
              />
            </label>
          </div>
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={config.fsa_enabled}
              onChange={(e) => update({ fsa_enabled: e.target.checked })}
            />
            <span>
              <strong>启用 FSA 骨架检查</strong>
              <small>积累 50 个合法候选后，检查高频结构。</small>
            </span>
          </label>
        </fieldset>
        <div className="run-estimate">
          <span>
            计划候选 <strong>{config.rounds * config.batch_size}</strong>
          </span>
          <span>
            模型调用 <strong>0</strong>
          </span>
          <span>
            外部费用 <strong>无</strong>
          </span>
        </div>
        <ErrorNotice message={error} />
        <div className="modal-actions">
          <button type="button" className="button outline" disabled={busy} onClick={onClose}>
            取消
          </button>
          <button className="button navy" disabled={busy}>
            {busy ? <LoaderCircle size={16} className="spin" /> : <Play size={16} />}创建并启动
          </button>
        </div>
      </form>
    </Modal>
  );
}

function MetricCards({
  values,
}: {
  values: { label: string; value: number | string; note: string }[];
}) {
  return (
    <div className="metric-grid">
      {values.map(({ label, value, note }) => (
        <div className="metric-card" key={label}>
          <span>{label}</span>
          <strong className="mono">{value}</strong>
          <small>{note}</small>
        </div>
      ))}
    </div>
  );
}

function DebugPanel() {
  const [expression, setExpression] = useState(
    'sub(ts_mean(gap, 10), ts_mean(intraday_range, 10))',
  );
  const [result, setResult] = useState<Validation & { notice: string }>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    setResult(undefined);
    try {
      setResult(await post('/factors/debug', { expression }));
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="panel debug-panel">
      <div className="panel-title">
        <div>
          <Braces size={19} />
          <h2>公式工作台</h2>
        </div>
        <span className="subtle-label">DSL CHECK</span>
      </div>
      <p className="panel-description">先验证语法、量纲和回看长度，再进入数据验证。</p>
      <form onSubmit={submit}>
        <label className="sr-only" htmlFor="expression">
          因子表达式
        </label>
        <div className="code-editor">
          <span>01</span>
          <textarea
            id="expression"
            value={expression}
            maxLength={2000}
            spellCheck={false}
            rows={3}
            onChange={(e) => {
              setExpression(e.target.value);
              setResult(undefined);
              setError('');
            }}
          />
        </div>
        <div className="debug-actions">
          <span>
            <ShieldCheck size={14} />
            只执行白名单算子
          </span>
          <button className="button outline compact" disabled={busy}>
            {busy ? <LoaderCircle size={14} className="spin" /> : <Check size={14} />}校验公式
          </button>
        </div>
      </form>
      <ErrorNotice message={error} />
      {result && (
        <div className="debug-result" role="status">
          <strong>
            <Check size={15} />
            结构校验通过
          </strong>
          <div className="debug-facts">
            <span>节点 {result.nodes}</span>
            <span>深度 {result.depth}</span>
            <span>回看 {result.lookback} 个交易日</span>
          </div>
          <p>{result.notice}</p>
          <details>
            <summary>查看解析树</summary>
            <pre>{JSON.stringify(result.tree, null, 2)}</pre>
          </details>
        </div>
      )}
    </section>
  );
}

export function ConsolePage() {
  const [creating, setCreating] = useState(false);
  const runs = useResource<{ items: Run[] }>('/runs', 2500);
  const items = runs.data?.items ?? [];
  return (
    <>
      <div className="console-heading">
        <div>
          <span className="eyebrow">OVERVIEW</span>
          <h1>研究控制台</h1>
          <p>从一条假设开始，观察每一次迭代。</p>
        </div>
        <button className="button navy" onClick={() => setCreating(true)}>
          <Plus size={17} />
          新建演示任务
        </button>
      </div>
      <FixtureNotice />
      <ErrorNotice message={runs.error} retry={runs.refresh} />
      <MetricCards
        values={[
          {
            label: '最近演示任务',
            value: runs.data ? items.length : '—',
            note: '保留配置与检查点',
          },
          {
            label: '结构检查通过',
            value: runs.data ? items.reduce((s, r) => s + r.counts.validated, 0) : '—',
            note: '仍待真实数据验证',
          },
          { label: '真实模型调用', value: 0, note: '当前为本地演示模式' },
          { label: '正式入库因子', value: 0, note: '尚未进行市场回测' },
        ]}
      />
      <section className="panel tasks-panel">
        <div className="panel-title">
          <div>
            <Workflow size={19} />
            <h2>任务记录</h2>
            <span className="count-chip">{items.length}</span>
          </div>
          <button className="icon-button" aria-label="刷新任务" onClick={runs.refresh}>
            <RotateCcw size={16} />
          </button>
        </div>
        {!runs.data && !runs.error ? (
          <Loading />
        ) : items.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务</th>
                  <th>状态</th>
                  <th>候选进度</th>
                  <th>创建时间</th>
                  <th>
                    <span className="sr-only">操作</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map((run) => (
                  <tr key={run.id}>
                    <td>
                      <Link className="table-link" to={`/console/runs/${run.id}`}>
                        {run.config.name}
                      </Link>
                      <small className="table-sub">演示模式 · seed {run.config.seed}</small>
                    </td>
                    <td>
                      <Status state={run.state} />
                    </td>
                    <td className="mono">
                      {run.cursor}
                      <span className="muted"> / {run.target}</span>
                    </td>
                    <td className="muted nowrap">{dateTime(run.created_at)}</td>
                    <td>
                      <Link
                        className="row-arrow"
                        to={`/console/runs/${run.id}`}
                        aria-label={`查看 ${run.config.name}`}
                      >
                        <ArrowUpRight size={17} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<Workflow size={30} strokeWidth={1.2} />}
            title="你的第一条研究循环"
            action={
              <button className="text-link" onClick={() => setCreating(true)}>
                创建一个演示任务 <ArrowRight size={15} />
              </button>
            }
          >
            用预置候选走通生成、规则检查与记录流程。
            <br />
            任务结束后，可以逐一查看公式与拒绝原因。
          </EmptyState>
        )}
      </section>
      <div className="workspace-bottom">
        <DebugPanel />
        <section className="panel next-panel">
          <span className="eyebrow">NEXT CONNECTION</span>
          <Database size={27} strokeWidth={1.3} />
          <h2>
            为真实研究，
            <br />
            留好连接。
          </h2>
          <p>
            DeepSeek 官方接口适配器和本地数据契约已准备。待模型 ID
            与数据口径确认后，再连接真实实验。
          </p>
          <Link className="text-link" to="/console/settings">
            查看数据与模型 <ArrowRight size={15} />
          </Link>
        </section>
      </div>
      {creating && <NewRunModal onClose={() => setCreating(false)} />}
    </>
  );
}

export function RunPage() {
  const { runId = '' } = useParams();
  const { run, setRun, candidates, events, connection, error } = useRun(runId);
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState('');
  const [filter, setFilter] = useState('all');
  const action = async (name: string) => {
    setBusy(name);
    setActionError('');
    try {
      setRun(await post<Run>(`/runs/${runId}/${name}`));
    } catch (e) {
      setActionError(messageOf(e));
    } finally {
      setBusy('');
    }
  };
  const download = async () => {
    setBusy('export');
    setActionError('');
    try {
      const report = await api(`/runs/${runId}/report`);
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }),
      );
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `fixture-${runId}.json`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setActionError(messageOf(e));
    } finally {
      setBusy('');
    }
  };
  if (!run)
    return (
      <>
        <Link className="back-link" to="/console">
          <ArrowLeft size={15} />
          工作台
        </Link>
        <ErrorNotice message={error} />
        {!error && <Loading />}
      </>
    );
  const canPause = ['queued', 'running'].includes(run.state);
  const canResume = ['paused', 'interrupted'].includes(run.state);
  const canStop = [
    'draft',
    'queued',
    'running',
    'pause_requested',
    'paused',
    'interrupted',
  ].includes(run.state);
  const filtered = candidates.filter((c) => filter === 'all' || c.status === filter);
  return (
    <>
      <Link className="back-link" to="/console">
        <ArrowLeft size={15} />
        返回工作台
      </Link>
      <div className="console-heading run-heading">
        <div>
          <span className="eyebrow">RUN / {run.id.slice(0, 8)}</span>
          <h1>{run.config.name}</h1>
          <div className="run-subtitle">
            <Status state={run.state} />
            <span>
              seed {run.config.seed} · {run.config.rounds} 轮 ·{' '}
              {run.config.fsa_enabled ? 'FSA 开启' : 'FSA 关闭'}
            </span>
          </div>
        </div>
        <div className="button-group">
          {run.state === 'draft' && (
            <button
              className="button navy compact"
              disabled={!!busy}
              onClick={() => action('start')}
            >
              <Play size={15} />
              启动
            </button>
          )}
          {canPause && (
            <button
              className="button outline compact"
              disabled={!!busy}
              onClick={() => action('pause')}
            >
              <Pause size={15} />
              暂停
            </button>
          )}
          {canResume && (
            <button
              className="button navy compact"
              disabled={!!busy}
              onClick={() => action('resume')}
            >
              <Play size={15} />
              继续运行
            </button>
          )}
          {canStop && (
            <button
              className="button outline compact"
              disabled={!!busy}
              onClick={() => action('stop')}
            >
              <Square size={13} />
              停止
            </button>
          )}
          <button className="button outline compact" disabled={!!busy} onClick={download}>
            <Download size={15} />
            导出记录
          </button>
        </div>
      </div>
      <FixtureNotice />
      <ErrorNotice message={error || actionError || run.error || ''} />
      <MetricCards
        values={[
          {
            label: '候选尝试',
            value: run.cursor,
            note: `计划 ${run.target} 个 · 上限 ${run.config.max_candidates}`,
          },
          { label: '结构检查通过', value: run.counts.validated, note: '等待后续数据验证' },
          { label: '规则 / 重复拒绝', value: run.counts.rejected, note: '保留具体原因' },
          { label: '模型调用 / 正式入库', value: '0 / 0', note: '演示模式不执行这两项' },
        ]}
      />
      <section className="panel progress-panel">
        <div>
          <span>
            <Workflow size={16} />
            流程进度
          </span>
          <strong className="mono">
            {run.cursor} / {run.target}
          </strong>
        </div>
        <progress value={run.cursor} max={run.target} aria-label="候选进度" />
        <div className="progress-steps">
          <span>01 产生候选</span>
          <span>02 规则检查</span>
          <span>03 保存记录</span>
          <span className="muted">04 数据验证待接入</span>
        </div>
        {run.state === 'pause_requested' && (
          <p className="source-note">将在当前候选保存检查点后暂停。</p>
        )}
      </section>
      <div className="run-columns">
        <section className="panel candidates-panel">
          <div className="panel-title">
            <div>
              <Braces size={19} />
              <h2>候选因子</h2>
            </div>
            <label>
              <span className="sr-only">筛选候选状态</span>
              <select value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="all">全部状态</option>
                <option value="awaiting_data">等待数据</option>
                <option value="rejected">规则拒绝</option>
                <option value="duplicate">表达式重复</option>
                <option value="fsa_blocked">骨架冻结</option>
              </select>
            </label>
          </div>
          {filtered.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>候选 / 表达式</th>
                    <th>策略</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <Link className="table-link" to={`/console/factors/${c.id}`}>
                          {c.name}
                          <ArrowUpRight size={13} />
                        </Link>
                        <code className="table-expression" title={c.expression}>
                          {c.expression}
                        </code>
                      </td>
                      <td className="nowrap">{strategyName(c.strategy)}</td>
                      <td>
                        <Status state={c.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={<Braces size={25} />}
              title={filter === 'all' ? '等待第一个候选' : '此筛选下暂无候选'}
            >
              候选生成后，公式与检查状态会在此更新。
            </EmptyState>
          )}
        </section>
        <section className="panel event-panel">
          <div className="panel-title">
            <div>
              <Terminal size={17} />
              <h2>运行事件</h2>
            </div>
            <span
              className={`event-connection ${connection}`}
              title={connection === 'connected' ? '事件流已连接' : '正在重新连接'}
            >
              <Radio size={13} />
              {connection === 'connected' ? '实时' : '重连中'}
            </span>
          </div>
          <div className="event-list" aria-label="运行事件">
            {events.length ? (
              [...events].reverse().map((event) => (
                <article className="event" key={event.id}>
                  <span className="event-dot" />
                  <div>
                    <time>
                      {dateTime(event.created_at)} <small>#{event.id}</small>
                    </time>
                    <p>{event.payload.message || event.type}</p>
                    {event.payload.ordinal && <small>候选 {event.payload.ordinal}</small>}
                  </div>
                </article>
              ))
            ) : (
              <p className="muted">等待运行事件…</p>
            )}
          </div>
        </section>
      </div>
      <details className="config-details">
        <summary>
          <Settings2 size={15} />
          查看冻结配置与检查点
        </summary>
        <pre>
          {JSON.stringify(
            {
              config: run.config,
              config_hash: run.config_hash,
              next_index: run.checkpoint.next_index ?? 0,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </>
  );
}

export function FactorPage() {
  const { factorId = '' } = useParams();
  const { data: factor, error } = useResource<Candidate>(`/factors/${factorId}`);
  if (!factor)
    return (
      <>
        <ErrorNotice message={error} />
        {!error && <Loading />}
      </>
    );
  return (
    <>
      <Link className="back-link" to={`/console/runs/${factor.run_id}`}>
        <ArrowLeft size={15} />
        返回运行记录
      </Link>
      <div className="console-heading">
        <div>
          <span className="eyebrow">FACTOR / {factor.ordinal.toString().padStart(3, '0')}</span>
          <h1>{factor.name}</h1>
          <div className="run-subtitle">
            <Status state={factor.status} />
            <span>
              {strategyName(factor.strategy)} · 第 {factor.round} 轮
            </span>
          </div>
        </div>
        <span className="tag">预置演示候选</span>
      </div>
      <FixtureNotice />
      <section className="panel factor-expression">
        <span className="eyebrow">EXPRESSION</span>
        <pre>{factor.expression}</pre>
        <p>{factor.hypothesis}</p>
        <div className="factor-facts">
          <span>
            <GitIcon />
            机制：{factor.mechanism}
          </span>
          <span>
            <Fingerprint size={15} />
            {factor.fingerprint?.slice(0, 12) || '未生成指纹'}
          </span>
          <span>
            <ShieldCheck size={15} />
            LLM 审查：未运行
          </span>
        </div>
      </section>
      <section className="panel factor-validation">
        <div className="panel-title">
          <div>
            <ShieldCheck size={19} />
            <h2>规则检查</h2>
          </div>
          <Status state={factor.status} />
        </div>
        <p>{factor.reason}</p>
        {factor.validation && (
          <>
            <div className="debug-facts">
              <span>节点 {factor.validation.nodes}</span>
              <span>深度 {factor.validation.depth}</span>
              <span>回看 {factor.validation.lookback} 个交易日</span>
            </div>
            <details>
              <summary>查看解析树</summary>
              <pre>{JSON.stringify(factor.validation.tree, null, 2)}</pre>
            </details>
          </>
        )}
      </section>
      <section className="panel">
        <div className="panel-title">
          <div>
            <Check size={19} />
            <h2>联合过滤</h2>
          </div>
          <span className="subtle-label">11 CHECKS · 待数据验证</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>检查项</th>
                <th>门槛</th>
                <th>实际值</th>
                <th>结果</th>
                <th>来源</th>
              </tr>
            </thead>
            <tbody>
              {factor.gates.map((g) => (
                <tr key={g.id}>
                  <td>
                    <small className="mono muted">{g.id} </small>
                    {g.name}
                  </td>
                  <td className="mono">
                    {g.operator} {g.threshold}
                  </td>
                  <td>—</td>
                  <td>
                    <Status state={g.status} />
                  </td>
                  <td className="muted nowrap">
                    {g.origin === 'local_reconstruction' ? '工程补充' : '材料条件适配'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <p className="source-note">
        本地 11 项口径详见 SPEC。当前没有市场数据与验证结果，不判定任何候选正式入库。
      </p>
    </>
  );
}

function GitIcon() {
  return <Workflow size={15} />;
}

export function SettingsPage() {
  const capabilities = useResource<Capabilities>('/capabilities');
  const datasets = useResource<{ items: Dataset[] }>('/datasets');
  const [check, setCheck] = useState<ModelStatus & { message: string }>();
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const model = check || capabilities.data?.model;
  const checkModel = async () => {
    setBusy('model');
    setError('');
    try {
      setCheck(await post('/models/check'));
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy('');
    }
  };
  const validate = async (id: string) => {
    setBusy(id);
    setError('');
    try {
      await post(`/datasets/${id}/validate`);
      datasets.refresh();
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy('');
    }
  };
  return (
    <>
      <div className="console-heading">
        <div>
          <span className="eyebrow">CONNECTIONS</span>
          <h1>数据与模型</h1>
          <p>把输入和连接核实清楚，再开始真实研究。</p>
        </div>
        <span className="tag">当前仅启用演示模式</span>
      </div>
      <ErrorNotice message={error || capabilities.error || datasets.error} />
      <section className="panel model-panel">
        <div className="panel-title">
          <div>
            <Braces size={20} />
            <h2>DeepSeek 官方 API</h2>
          </div>
          <span className="tag">{model?.configured ? '已配置 · 未验证' : '待配置'}</span>
        </div>
        <p className="model-target">
          DeepSeek 4.1 Flash <small>用户指定目标 · 官方模型 ID 待核实</small>
        </p>
        <div className="connection-fields">
          <div>
            <span>服务地址</span>
            <strong className="mono">https://api.deepseek.com</strong>
          </div>
          <div>
            <span>模型 ID</span>
            <strong className="mono">{model?.model_id || '尚未配置'}</strong>
          </div>
          <div>
            <span>服务端密钥</span>
            <strong>{model?.key_present ? '已设置（不显示值）' : '尚未设置'}</strong>
          </div>
          <div>
            <span>真实运行通道</span>
            <strong>尚未启用</strong>
          </div>
        </div>
        <div className="model-footer">
          <p>
            <CircleHelp size={15} />
            密钥只保存在服务端环境变量中。
          </p>
          <button className="button outline compact" onClick={checkModel} disabled={!!busy}>
            {busy === 'model' ? (
              <LoaderCircle size={14} className="spin" />
            ) : (
              <RotateCcw size={14} />
            )}
            检查本地配置
          </button>
        </div>
        {check && (
          <p className="inline-notice" role="status">
            {check.message}
          </p>
        )}
        <details>
          <summary>开发者配置说明</summary>
          <pre>DEEPSEEK_API_KEY=你的密钥{`\n`}DEEPSEEK_MODEL=核实后的官方模型ID</pre>
          <p>在项目根目录的本地 .env 中设置，重启后端生效。框架不会自动替换模型或发起付费请求。</p>
        </details>
      </section>
      <section className="panel dataset-panel">
        <div className="panel-title">
          <div>
            <Database size={20} />
            <h2>本地数据集</h2>
            <span className="count-chip">{datasets.data?.items.length || 0}</span>
          </div>
          <span className="subtle-label">VERSIONED INPUTS</span>
        </div>
        {datasets.data?.items.length ? (
          <div className="dataset-list">
            {datasets.data.items.map((dataset) => (
              <article key={dataset.id}>
                <div>
                  <strong>{dataset.name || dataset.id}</strong>
                  <p>
                    {dataset.validation
                      ? `${dataset.validation.rows} 行 · ${dataset.validation.symbols} 只股票 · ${dataset.validation.valid ? '结构校验通过' : '校验未通过'}`
                      : '尚未校验'}
                  </p>
                  <small className="mono muted">{dataset.sha256?.slice(0, 20)}</small>
                </div>
                <button
                  className="button outline compact"
                  disabled={!!busy}
                  onClick={() => validate(dataset.id)}
                >
                  重新校验
                </button>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState icon={<Database size={28} strokeWidth={1.2} />} title="尚未连接研究数据">
            本轮不下载市场数据。后续可以通过本地 CSV 接口，
            <br />
            接入经过确认的股票价格快照。
          </EmptyState>
        )}
        <details>
          <summary>本地 CSV 数据契约</summary>
          <p>
            必需列：date, symbol, open, high, low, close,
            volume。当前校验结构、价格与重复键；复权和研究区间仍需另行确认。
          </p>
          <pre>uv run loop-research data register --csv /path/to/data.csv --id my-dataset</pre>
        </details>
      </section>
      <div className="readiness-note">
        <Clock3 size={17} />
        <p>
          真实实验入口保持关闭，直到官方模型
          ID、数据口径与验证协议完成确认。当前可以在工作台运行本地演示和公式校验。
        </p>
        <Link className="text-link" to="/console">
          返回工作台 <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}
