import { useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Braces,
  CheckCheck,
  Fingerprint,
  GitBranch,
  Layers3,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { CheckItem, LoopDiagram, SectionHeading } from '../components';
import { stages, strategies } from '../content';
import { useResource } from '../hooks';
import { apiUrl } from '../api';
import type { ExperimentResult } from '../types';

export function HomePage() {
  return (
    <>
      <section className="hero page-width">
        <div className="hero-copy">
          <div className="eyebrow hero-eyebrow">
            <span /> QUANTITATIVE RESEARCH · VOL. 07
          </div>
          <h1>
            让因子研究
            <br />
            形成<span>可验证</span>的闭环。
          </h1>
          <p className="hero-description">
            从提出假设，到验证信号。
            <br />以 Loop Engineering 连接大模型的探索能力与量化研究的验证纪律。
          </p>
          <div className="hero-actions">
            <Link className="button navy large" to="/mine">
              开始实时挖掘 <ArrowUpRight size={18} />
            </Link>
            <Link className="text-link" to="/presentation">
              播放研究演示 <ArrowRight size={16} />
            </Link>
          </div>
          <div className="hero-checks">
            <CheckItem>轻量 Python 引擎</CheckItem>
            <CheckItem>研究过程可追溯</CheckItem>
          </div>
        </div>
        <div className="hero-visual">
          <span className="visual-index">THE RESEARCH LOOP</span>
          <LoopDiagram />
          <span className="visual-footnote">大模型提出假设，程序负责验证。</span>
        </div>
      </section>
      <div className="principles-band">
        <div className="page-width principles-inner">
          <div>
            <strong>05</strong>
            <span>
              候选生成策略<small>平衡探索与利用</small>
            </span>
          </div>
          <div>
            <strong>11</strong>
            <span>
              联合过滤条件<small>本项目的透明实现口径</small>
            </span>
          </div>
          <div>
            <Fingerprint size={35} strokeWidth={1.1} />
            <span>
              每一次迭代都有依据<small>表达式、审查与检查点</small>
            </span>
          </div>
        </div>
      </div>
      <section className="section page-width">
        <SectionHeading
          number="01"
          eyebrow="FROM IDEA TO EVIDENCE"
          title="把研究的循环，写进程序。"
        >
          因子发现不止是产生一个公式，更是对假设持续提出问题、寻找证据。
        </SectionHeading>
        <div className="feature-grid">
          {[
            {
              Icon: GitBranch,
              title: '让探索有方向',
              text: '变异、交叉与机制引导共同产生候选。既沿着已有发现继续挖掘，也为未知机制留出空间。',
              tag: 'GENERATION',
            },
            {
              Icon: ShieldCheck,
              title: '让结论有边界',
              text: '将逻辑审查与确定性验证分开。信号要经过时间对齐、交易成本和多项门槛的共同检验。',
              tag: 'VALIDATION',
            },
            {
              Icon: Layers3,
              title: '让迭代有记忆',
              text: '记录每次尝试与失败原因，用高频骨架规避机制减少重复探索，中断后从检查点继续。',
              tag: 'EVOLUTION',
            },
          ].map(({ Icon, title, text, tag }) => (
            <article className="feature" key={tag}>
              <Icon size={26} strokeWidth={1.3} />
              <span className="eyebrow">{tag}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
      <section className="research-note page-width">
        <div className="note-label">
          <BookOpen size={21} />
          <span>
            研究说明
            <br />
            <small>READ THE EVIDENCE</small>
          </span>
        </div>
        <p>
          本项目参考用户提供的中金案例分析，复现发现流程与工程机制。材料披露的历史回测、本地实验与现场计算均注明来源。
        </p>
        <Link className="text-link" to="/research">
          方法与来源 <ArrowUpRight size={16} />
        </Link>
      </section>
      <section className="section page-width home-bottom">
        <div>
          <span className="eyebrow">START WITH A QUESTION</span>
          <h2>下一条假设，从这里开始。</h2>
          <p>运行一次本地流程演示，查看候选如何生成、检查并留下记录。</p>
        </div>
        <Link className="button navy" to="/console">
          <Play size={16} />
          进入控制台
        </Link>
      </section>
    </>
  );
}

export function ResearchPage() {
  const [active, setActive] = useState(0);
  const stage = stages[active];
  return (
    <main className="page-width research-page">
      <div className="page-intro">
        <span className="eyebrow">METHODOLOGY / LOOP ENGINEERING</span>
        <h1>
          发现是一段循环，
          <br />
          结论需要独立验证。
        </h1>
        <p>从因子动物园与重复试错出发，建立可持续探索、可解释审查、可追踪验证的研究流程。</p>
      </div>
      <section className="method-loop">
        <LoopDiagram interactive active={active} onChange={setActive} />
        <article className="stage-detail">
          <span className="section-number">0{active + 1}</span>
          <span className="eyebrow">{stage.en}</span>
          <h2>{stage.name}</h2>
          <p>{stage.description}</p>
          <dl>
            <div>
              <dt>输入</dt>
              <dd>{stage.input}</dd>
            </div>
            <div>
              <dt>输出</dt>
              <dd>{stage.output}</dd>
            </div>
          </dl>
        </article>
      </section>
      <section className="section">
        <SectionHeading
          number="02"
          eyebrow="EXPLORATION & EXPLOITATION"
          title="五种策略，共同拓展搜索空间。"
        >
          以下是材料披露的初始配比。代码框架保留这些策略接口，演示中的机制引导使用预置公式。
        </SectionHeading>
        <div className="strategy-list">
          {strategies.map((s, i) => (
            <div className="strategy-row" key={s.id}>
              <span className="mono muted">0{i + 1}</span>
              <div>
                <h3>{s.name}</h3>
                <p>{s.description}</p>
              </div>
              <div className="strategy-bar">
                <span style={{ width: `${s.weight * 3}%` }} />
              </div>
              <strong className="mono">
                {s.weight}
                <small>%</small>
              </strong>
            </div>
          ))}
        </div>
      </section>
      <section className="method-cards">
        <article className="panel">
          <ShieldCheck size={26} />
          <span className="eyebrow">JOINT VALIDATION</span>
          <h2>让多个问题，共同决定答案。</h2>
          <p>
            同时检查信息系数、分期收益、风险回报、相关性与数据覆盖。筛选集参与开发，最终测试区间保持封存。
          </p>
          <div className="tag-row">
            <span>IC &gt; 0.03</span>
            <span>分期检验</span>
            <span>单边成本 0.1%</span>
            <span>相关性 &lt; 0.7</span>
          </div>
          <small className="source-note">
            附件没有完整列出原始 11 项标准。SPEC 中明确区分了 9 个可拆分条件和 2 项本地工程补充。
          </small>
        </article>
        <article className="panel dark-panel">
          <Fingerprint size={26} />
          <span className="eyebrow">FREQUENT SUBTREE AVOIDANCE</span>
          <h2>
            识别重复结构，
            <br />
            为新方向留出空间。
          </h2>
          <p>
            只改变窗口的公式，可能仍是同一个想法。FSA
            将表达式还原为结构骨架，达到频率阈值后暂时冻结。
          </p>
          <div className="fsa-example">
            <code>
              ts_mean(gap, <b>5</b>)
            </code>
            <code>
              ts_mean(gap, <b>20</b>)
            </code>
            <span>
              <ArrowRight size={15} /> 同一骨架
            </span>
          </div>
          <small className="source-note">
            15% 阈值来自材料；统计窗口和解除规则是本项目的明确实现选择。
          </small>
        </article>
      </section>
      <section className="section sources-section">
        <SectionHeading
          number="03"
          eyebrow="SOURCES & LIMITATIONS"
          title="分清材料中的结果，与自己的证据。"
        />
        <div className="source-grid">
          <div>
            <h3>资料来源</h3>
            <p>
              背景与机制依据用户提供的中金案例分析。原转载正文尚未完成联网核对，以下链接保留为原始来源。
            </p>
            <a
              href="https://finance.sina.com.cn/stock/stockzmt/2026-08-05/doc-inimffsv4845270.shtml"
              target="_blank"
              rel="noreferrer"
            >
              新浪研报转载 <ArrowUpRight size={14} />
            </a>
            <a
              href="https://mp.weixin.qq.com/s/hrKdYATh_9rdASVAdjGymg"
              target="_blank"
              rel="noreferrer"
            >
              微信公众号转载 <ArrowUpRight size={14} />
            </a>
          </div>
          <div>
            <h3>当前实现阶段</h3>
            <p>
              已完成 StockNet 美股小规模实验，并记录全部通过与失败结果。
              这是一项流程复现，不能据此声称复现 A 股收益。
            </p>
            <Link to="/experiments">
              查看真实实验记录 <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export function ExperimentsPage() {
  const { data, error, refresh } = useResource<{ items: ExperimentResult[] }>('/experiments');
  const [selectedId, setSelectedId] = useState('');
  const experiment = data?.items.find((item) => item.id === selectedId) ?? data?.items[0];
  const labels: Record<string, string> = {
    E0: '传统因子基线',
    E1: '随机搜索',
    E2: '完整 Loop',
    E3: '关闭 FSA',
    E4: '系统枚举与平滑',
    E5: '多种子组合搜索',
    E6: '模型机制与局部变体',
    E7: '开发反馈搜索',
  };
  const percent = (value: number | null) =>
    value === null ? '未定义' : `${(value * 100).toFixed(2)}%`;
  const branches = experiment ? Object.entries(experiment.branches) : [];
  const attempts = branches.reduce((total, [, branch]) => total + branch.attempts, 0);
  const accepted = branches.reduce((total, [, branch]) => total + branch.accepted, 0);
  const expanded = experiment?.experiment_version === 'expanded_search_v2';
  const holdout = experiment?.holdout?.LIBRARY;
  const composite = experiment?.holdout?.TOP5?.composite;
  return (
    <main className="page-width experiments-page">
      <div className="page-intro">
        <span className="eyebrow">EXPERIMENT REGISTRY</span>
        <h1>让结果来自真实运行。</h1>
        <p>固定数据与门槛，记录每一次尝试，也保留没有通过筛选的结果。</p>
      </div>
      {error && (
        <div role="alert" className="error-notice">
          {error}{' '}
          <button className="text-link" onClick={refresh}>
            重试
          </button>
        </div>
      )}
      {!experiment && !error && (
        <p role="status">{data ? '尚无已归档的真实实验。' : '正在读取实验记录…'}</p>
      )}
      {data && data.items.length > 1 && (
        <label className="experiment-selector">
          实验版本
          <select value={experiment?.id} onChange={(event) => setSelectedId(event.target.value)}>
            {data.items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.experiment_version === 'expanded_search_v2' ? '扩大实验' : '首轮对照'} ·{' '}
                {item.id}
              </option>
            ))}
          </select>
        </label>
      )}
      {experiment && (
        <>
          <section className="panel experiment-result-intro">
            <span className="eyebrow">
              COMPLETED ·{' '}
              {new Date(experiment.started_at_utc).toLocaleDateString('zh-CN', {
                timeZone: 'Asia/Shanghai',
              })}
            </span>
            <h2>
              {attempts} 次尝试，{accepted} 个因子{expanded ? '通过开发筛选入库' : '通过全部门槛'}。
            </h2>
            <p>
              {experiment.research_note ??
                '首轮四组均未达到固定的 11 项联合条件；所有 217 个实际回测候选的筛选期 Calmar 均未超过 1。未形成测试期复合组合。'}
            </p>
            <div className="experiment-facts">
              <div>
                <strong>{experiment.asset_count}</strong>
                <span>股票 · {experiment.rows.toLocaleString()} 行数据</span>
              </div>
              <div>
                <strong>{experiment.budget.run_requests}</strong>
                <span>官方 API 请求</span>
              </div>
              <div>
                <strong>¥{experiment.budget.run_cost_upper_bound_cny.toFixed(3)}</strong>
                <span>本轮费用保守上界 · 总预算 ¥{experiment.budget.hard_cap_cny}</span>
              </div>
              <div>
                <strong>{(experiment.seconds / 60).toFixed(1)} 分钟</strong>
                <span>实验墙钟时间</span>
              </div>
            </div>
            <p className="source-note">
              {experiment.model.name}（{experiment.model.id}）·{' '}
              {experiment.budget.run_tokens.toLocaleString()} tokens · 按官方高峰价及缓存用量估算约
              ¥{experiment.verification.peak_price_usage_estimate_cny.toFixed(3)}
              。运行于本地，网站读取已归档结果。
              {experiment.budget.cost_upper_bound_cny !== undefined &&
                ` 共享账本累计保守费用 ¥${experiment.budget.cost_upper_bound_cny.toFixed(3)}。`}
            </p>
            <a
              className="button navy"
              href={apiUrl(`/experiments/${experiment.id}/report`)}
              download
            >
              下载实验 JSON <ArrowUpRight size={15} />
            </a>
          </section>
          <section className="experiment-section">
            <h2>{expanded ? '扩大搜索与全部尝试' : '四组对照与全部尝试'}</h2>
            <div className="panel table-wrap">
              <table className="experiment-table">
                <caption>
                  统一股票池、时间切分、单边 0.1% 成本；
                  {expanded
                    ? `随机搜索种子 ${(experiment.random_seeds ?? []).join(' / ')}；E7 固定 3 轮。`
                    : `seed ${experiment.seed}；E2/E3 各 10 轮。`}
                </caption>
                <thead>
                  <tr>
                    <th scope="col">组别</th>
                    <th scope="col">尝试</th>
                    <th scope="col">DSL 合法</th>
                    <th scope="col">回测</th>
                    <th scope="col">入库</th>
                    <th scope="col">独立公式 / 骨架</th>
                  </tr>
                </thead>
                <tbody>
                  {branches.map(([id, branch]) => (
                    <tr key={id}>
                      <th scope="row">
                        {id} · {labels[id]}
                      </th>
                      <td>{branch.attempts}</td>
                      <td>{branch.legal}</td>
                      <td>{branch.backtested}</td>
                      <td>{branch.accepted}</td>
                      <td>
                        {branch.unique_expressions} / {branch.unique_skeletons}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="experiment-progress" aria-label="各组实际回测比例">
              {branches.map(([id, branch]) => (
                <div key={id}>
                  <label htmlFor={`progress-${id}`}>{id} · 实际回测</label>
                  <progress id={`progress-${id}`} value={branch.backtested} max={branch.attempts} />
                  <span>
                    {branch.backtested} / {branch.attempts}
                  </span>
                </div>
              ))}
            </div>
            <p className="source-note">
              {expanded
                ? '无效、重复、退化及发现期 IC 不合格的候选也计入尝试总数。回测列只统计完整开发筛选期回测，入库列统计统一去相关后的最终结果；各分支规模不同。'
                : 'E2 因 FSA 拒绝 7 次；E3 未启用 FSA。两个分支的模型输出和后续父代轨迹不同，单次结果只作描述性比较。'}
            </p>
          </section>
          {!!experiment.accepted_factors?.length && (
            <section className="experiment-section">
              <h2>入库因子与冻结后的留出检验</h2>
              <div className="panel table-wrap">
                <table className="experiment-table">
                  <caption>
                    开发筛选期为 2014–2015 年；留出期为 2016–2017 年。收益均为扣费后年化超额。
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">因子 / 公式</th>
                      <th scope="col">发现期 IC</th>
                      <th scope="col">筛选期 Calmar</th>
                      <th scope="col">筛选期超额</th>
                      <th scope="col">留出期超额</th>
                      <th scope="col">留出期夏普</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiment.accepted_factors.map((factor) => {
                      const test = holdout?.factors.find((item) => item.id === factor.id);
                      return (
                        <tr key={factor.id}>
                          <th scope="row">
                            <details>
                              <summary>
                                {factor.id} · 方向 {factor.direction > 0 ? '+1' : '−1'}
                              </summary>
                              <code>{factor.expression}</code>
                            </details>
                          </th>
                          <td>{factor.discovery_ic.toFixed(4)}</td>
                          <td>{factor.metrics.calmar.toFixed(2)}</td>
                          <td>{percent(factor.periods.selection.annual_excess)}</td>
                          <td>{percent(test?.annual_excess ?? null)}</td>
                          <td>{test?.sharpe?.toFixed(2) ?? '未定义'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {composite && (
                <p>
                  按开发筛选期排序预先选定的前 {composite.factor_count}{' '}
                  个因子，等权排名组合：留出期年化超额 {percent(composite.annual_excess)}， 夏普{' '}
                  {composite.sharpe?.toFixed(2) ?? '未定义'}，相对最大回撤{' '}
                  {percent(composite.max_drawdown)}。
                </p>
              )}
              <p className="source-note">
                全部入库因子均展示，留出期表现不用于重新筛选。扩大搜索会增加过拟合风险，入库数量不等于稳定
                Alpha 的数量。
              </p>
            </section>
          )}
          <section className="experiment-section">
            <h2>交易成本前后的传统基线</h2>
            <div className="panel table-wrap">
              <table className="experiment-table">
                <caption>
                  2014–2015 年筛选期，相对同股票池等权基准的年化超额；这是开发结果。
                </caption>
                <thead>
                  <tr>
                    <th scope="col">固定公式</th>
                    <th scope="col">冻结方向</th>
                    <th scope="col">搜索期 IC</th>
                    <th scope="col">成本前超额</th>
                    <th scope="col">成本后超额</th>
                  </tr>
                </thead>
                <tbody>
                  {experiment.baselines.map((factor) => (
                    <tr key={factor.id}>
                      <th scope="row">
                        <details>
                          <summary>{factor.name}</summary>
                          <code>{factor.expression}</code>
                        </details>
                      </th>
                      <td>{factor.direction === 1 ? '+1' : '−1'}</td>
                      <td>{factor.discovery_ic?.toFixed(4) ?? '未定义'}</td>
                      <td>{percent(factor.periods.selection_gross.annual_excess)}</td>
                      <td>{percent(factor.periods.selection.annual_excess)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="source-note">
              方向只按搜索期 IC 确定。信号在收盘后生成，下一交易日开盘成交，每 5
              个交易日调仓；策略与基准分别扣除买入、卖出及期末平仓费用。
            </p>
          </section>
          <section className="panel experiment-provenance">
            <h2>边界与复现证据</h2>
            <dl>
              {Object.entries(experiment.periods).map(([key, dates]) => (
                <div key={key}>
                  <dt>
                    {{ discovery: '搜索期', selection: '筛选期', holdout: '封存测试期' }[key]}
                  </dt>
                  <dd>{dates.join(' → ')}</dd>
                </div>
              ))}
            </dl>
            <p>
              已用独立 SciPy IC 与标量持仓账本核对{expanded ? '基线及全部入库因子' : '六个基线'}
              ：最大 IC 误差 {experiment.verification.max_ic_absolute_error.toExponential(1)}
              ，最大净值误差 {experiment.verification.max_nav_absolute_error.toExponential(1)}。
              {accepted === 0
                ? '没有因子入库，测试期没有可评估的因子组合。'
                : '已核对全部入库因子的开发及留出期净值和冻结记录。'}
            </p>
            <p>
              股票池存在事后选样风险；历史复权数据不是当时可获得的数据快照。模型可能在预训练中接触过历史行情。反复使用开发集、美股小股票池和重叠标签不支持可交易
              Alpha 或显著性结论。
            </p>
            <details>
              <summary>版本与校验和</summary>
              <p className="mono">
                {experiment.id}
                <br />
                StockNet commit: {experiment.data_commit}
                <br />
                Data SHA-256: {experiment.data_sha256}
                <br />
                Protocol SHA-256: {experiment.protocol_sha256}
              </p>
            </details>
            <div className="experiment-source-links">
              <a href={experiment.sources.data} target="_blank" rel="noreferrer">
                固定数据版本 ↗
              </a>
              <a href={experiment.sources.pricing} target="_blank" rel="noreferrer">
                官方模型与定价 ↗
              </a>
            </div>
          </section>
        </>
      )}
      <div className="section-heading small-heading">
        <span className="eyebrow">EXPERIMENT DESIGN</span>
        <h2>{expanded ? '固定规模，保留每次尝试。' : '每组对照回答一个问题。'}</h2>
      </div>
      <div className="comparison-grid">
        {(expanded
          ? [
              ['E4', '系统枚举与平滑', '覆盖不同周期与价量机制', Braces],
              ['E5', '多种子组合搜索', '三个固定种子，各 1,000 次', GitBranch],
              ['E6', '模型机制与局部变体', '先独立逻辑审查，再生成窗口变体', Layers3],
              ['E7', '开发反馈搜索', '固定三轮，每轮 800 次尝试', CheckCheck],
            ]
          : [
              ['E0', '传统因子基线', '6 个固定价量因子', Braces],
              ['E1', '随机搜索', '受限 DSL 的随机候选', GitBranch],
              ['E2', '完整 Loop', '五种策略、审查与 FSA', Layers3],
              ['E3', '关闭 FSA', '观察结构重复与覆盖差异', CheckCheck],
            ]
        ).map(([id, name, description, Icon]) => {
          const Glyph = Icon as typeof Braces;
          return (
            <article className="panel comparison" key={id as string}>
              <div>
                <span className="mono">{id as string}</span>
                <Glyph size={20} />
              </div>
              <h3>{name as string}</h3>
              <p>{description as string}</p>
              <span className="planned">{experiment ? '已完成本地实验' : '实验方案'}</span>
            </article>
          );
        })}
      </div>
      <p className="source-note experiment-note">
        本页展示已归档实验。实时挖掘页可以在固定历史快照上启动新的计算；浏览记录与本地搜索免费，DeepSeek
        模式需要演示口令。
      </p>
    </main>
  );
}
