import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Expand,
  List,
  Play,
  X,
} from 'lucide-react';
import slides from '../presentation/slides.json';
import results from '../presentation/local-results.json';
import '../presentation/presentation.css';

type Slide = (typeof slides)[number];
const root = '/presentation/';
const names = ['变异', '交叉', '参数扰动', '随机生成', '机制引导'];
const weights = [25, 25, 15, 15, 20];
const pad = (n: number) => String(n).padStart(2, '0');

function FactorVisual() {
  return (
    <div className="factor-illustration">
      <div className="formula-label">A HYPOTHESIS / 教学示意</div>
      <div className="large-formula">rank( − mean(gap, 5) )</div>
      <p>“近期隔夜跳空越弱，未来是否越强？”</p>
      <div className="toy-ranks">
        {[86, 63, 45, 31, 18].map((n, i) => (
          <div key={n}>
            <span>{'ABCDE'[i]}</span>
            <div>
              <i style={{ width: `${n}%` }} />
            </div>
            <span>{n}</span>
            {i === 0 && <b>选入</b>}
          </div>
        ))}
      </div>
      <div className="timing-track">
        <div>
          <b>t 日收盘</b>
          <span>形成信号</span>
        </div>
        <ArrowRight />
        <div>
          <b>t+1 日开盘</b>
          <span>执行交易</span>
        </div>
        <ArrowRight />
        <div>
          <b>5 个交易日</b>
          <span>持有 / 再平衡</span>
        </div>
      </div>
      <small>分数为示意值；现场实验使用完整 50 股截面。</small>
    </div>
  );
}

function LoopVisual() {
  return (
    <div className="research-loop-visual">
      <div className="loop-steps">
        {[
          ['01', '生成', '提出价量假设'],
          ['02', '审查', '独立上下文检查'],
          ['03', '验证', '回测与联合门槛'],
        ].map(([n, t, d]) => (
          <div key={n}>
            <span>{n}</span>
            <h3>{t}</h3>
            <p>{d}</p>
          </div>
        ))}
      </div>
      <div className="loop-feedback">
        <span>↰</span> 指标 · 拒绝原因 · 结构频率 <span>↵</span>
      </div>
      <div className="loop-image">
        <img src={`${root}servers.jpg`} alt="CERN GBAR 附近的机柜，作为计算基础设施概念配图" />
        <p>
          长期运行需要的不只是模型，
          <br />
          还有预算、检查点和明确的停止条件。
        </p>
      </div>
      <small>CERN GBAR 机柜 · 概念配图 / Unnerving duck · CC BY-SA 4.0</small>
    </div>
  );
}

function GatesVisual() {
  const gates = [
    ['|Rank IC|', '> 0.03'],
    ['第 1 年超额', '> 0'],
    ['第 2 年超额', '> 0'],
    ['第 1 年夏普', '> 0.5'],
    ['第 2 年夏普', '> 0.5'],
    ['Calmar', '> 1'],
    ['近 9 月超额', '> 0'],
    ['近 12 月超额', '> 0'],
    ['最大相关', '< 0.7'],
    ['有效覆盖率', '≥ 90%'],
    ['样本量', '通过'],
  ];
  return (
    <div className="gate-illustration">
      <div className="visual-heading">
        本地透明实现 <span>全部适用条件须同时通过</span>
      </div>
      <div className="deck-gates">
        {gates.map(([label, value], i) => (
          <div key={label} className={i > 8 ? 'local-gate' : ''}>
            <span>{pad(i + 1)}</span>
            <p>{label}</p>
            <b>{value}</b>
          </div>
        ))}
      </div>
      <div className="gate-legend">
        <span />
        材料明确条件的本地改写 <span />
        本项目补充工程约束
      </div>
    </div>
  );
}

function FsaVisual() {
  return (
    <div className="fsa-illustration">
      <div className="visual-heading">不同参数 / 相同骨架</div>
      <div className="formula-stack">
        {[20, 40, 60].map((n) => (
          <code key={n}>
            cs_rank(ts_mean(gap, <b>{n}</b>))
          </code>
        ))}
      </div>
      <div className="skeleton">
        ↓ 忽略参数后归为同一结构 ↓<code>cs_rank(ts_mean(gap, WINDOW))</code>
        <span>频率超过 15% → 暂时冻结</span>
      </div>
      <div className="fsa-timeline">
        <div>
          <b>前 50 轮</b>
          <strong>4</strong>
          <span>累计入库</span>
        </div>
        <div>
          <b>401–450 轮</b>
          <strong>+51</strong>
          <span>区间新增</span>
        </div>
        <div>
          <b>450 轮后</b>
          <strong>↗</strong>
          <span>转向新结构</span>
        </div>
      </div>
      <small>仅标出材料披露阶段；图形间距不表示时间比例。</small>
    </div>
  );
}

function FunnelVisual() {
  return (
    <div className="funnel-illustration">
      <div className="funnel-big">
        <span>
          0.41<small>%</small>
        </span>
        <p>
          入选率
          <br />
          <b>69 / 16,939</b>
        </p>
      </div>
      <svg
        viewBox="0 0 580 310"
        role="img"
        aria-label="500 点示意图，2 个高亮，约表示 0.4% 的入选率"
      >
        {Array.from({ length: 500 }, (_, i) => (
          <circle
            key={i}
            cx={16 + (i % 25) * 23}
            cy={10 + Math.floor(i / 25) * 15}
            r={4.1}
            fill={i < 2 ? '#e1be79' : '#345360'}
          />
        ))}
      </svg>
      <div className="funnel-legend">
        <span /> 入库 <span /> 其余候选 <small>500 点近似示意 · 精确数量见上方</small>
      </div>
    </div>
  );
}

function PerformanceVisual() {
  return (
    <div className="performance-illustration">
      <div className="visual-heading">
        年化超额收益 <span>报告披露 / %</span>
      </div>
      <div className="performance-bars">
        {[
          ['单因子均值', 14.5, '1.63'],
          ['Top 5 等权组合', 18.3, '3.14'],
        ].map(([name, val, sharpe]) => (
          <div key={name}>
            <div className="perf-caption">
              <b>{name}</b>
              <span>夏普 {sharpe}</span>
            </div>
            <div className="perf-track">
              <i style={{ width: `${(Number(val) / 25) * 100}%` }} />
              <strong>
                {val}
                <small>%</small>
              </strong>
            </div>
          </div>
        ))}
      </div>
      <div className="bar-axis">
        <span>0</span>
        <span>5</span>
        <span>10</span>
        <span>15</span>
        <span>20</span>
        <span>25%</span>
      </div>
      <div className="evidence-questions">
        <b>仍需补齐的证据</b>
        <span>独立样本外</span>
        <span>参数选择记录</span>
        <span>冲击与容量</span>
      </div>
      <small>两类统计对象不同；图中不构造未披露的净值序列。</small>
    </div>
  );
}

function ReplicationVisual() {
  const y = (n: number) => 55 + ((0.26 - n) / 0.43) * 300;
  return (
    <div className="replication-illustration">
      <div className="visual-heading">
        同一因子，走进下一段时间 <span>年化超额</span>
      </div>
      <svg
        viewBox="0 0 600 430"
        role="img"
        aria-label="23 个入库因子的筛选期与留出期年化超额配对图，留出期仅 1 个为正"
      >
        <text x="130" y="24" textAnchor="middle">
          开发筛选期
        </text>
        <text x="450" y="24" textAnchor="middle">
          留出期
        </text>
        {[-0.1, 0, 0.1, 0.2].map((n) => (
          <g key={n}>
            <line
              x1="70"
              x2="530"
              y1={y(n)}
              y2={y(n)}
              stroke={n === 0 ? '#84999b' : '#dfe4df'}
              strokeDasharray={n === 0 ? '4 4' : undefined}
            />
            <text x="6" y={y(n) + 5}>
              {Math.round(n * 100)}%
            </text>
          </g>
        ))}
        {results.factors.map((f) => (
          <g key={f.id}>
            <title>
              {f.id}: {(f.selection * 100).toFixed(2)}% → {(f.holdout * 100).toFixed(2)}%
            </title>
            <line
              x1="130"
              x2="450"
              y1={y(f.selection)}
              y2={y(f.holdout)}
              stroke="#8fa3a0"
              strokeOpacity=".48"
            />
            <circle cx="130" cy={y(f.selection)} r="4" fill="#137d75" />
            <circle cx="450" cy={y(f.holdout)} r="4" fill={f.holdout > 0 ? '#137d75' : '#b55c46'} />
          </g>
        ))}
        <text x="130" y="396" textAnchor="middle">
          2014—2015
        </text>
        <text x="450" y="396" textAnchor="middle">
          2016—2017.09
        </text>
      </svg>
      <div className="holdout-callout">
        <div>
          <strong>
            1<small> / 23</small>
          </strong>
          <span>留出期年化超额为正</span>
        </div>
        <div>
          <strong>
            −3.18<small>%</small>
          </strong>
          <span>固定 Top 5 留出年化超额</span>
        </div>
      </div>
    </div>
  );
}

function CrowdingVisual() {
  return (
    <div className="crowding-illustration">
      <div className="institutions">
        {['机构 A', '机构 B', '机构 C'].map((t) => (
          <div key={t}>
            <span>◇</span>
            {t}
            <small>独立研究循环</small>
          </div>
        ))}
      </div>
      <div className="converge-lines">
        <i />
        <i />
        <i />
      </div>
      <div className="crowding-shared">
        <b>相近的字段 · 模型 · 筛选目标</b>
        <p>不同公式，可能导向重叠的持仓</p>
      </div>
      <div className="down-arrow">↓</div>
      <div className="crowding-consequence">
        <div>同时减仓</div>
        <ArrowRight />
        <div>流动性压力</div>
        <ArrowRight />
        <div>冲击放大</div>
      </div>
      <div className="crowding-question">研究问题：如何度量跨机构的“机制多样性”？</div>
      <small>概念图：方向表示可能的传导机制，不代表已识别的因果关系。</small>
    </div>
  );
}

function Visual({ kind }: { kind: string }) {
  switch (kind) {
    case 'cover':
      return (
        <div className="cover-photo">
          <img src={`${root}shanghai.jpg`} alt="上海浦东天际线" />
          <div className="cover-photo-caption">
            <span>SHANGHAI / A NEW RESEARCH PROCESS</span>
            <b>假设 → 证据 → 新问题</b>
          </div>
          <small>King of Hearts / CC BY-SA 4.0</small>
        </div>
      );
    case 'bottleneck':
      return (
        <div className="bottleneck-illustration">
          <img src={`${root}trading-floor.jpg`} alt="纽约证券交易所历史交易大厅" />
          <div className="bottleneck-quote">
            <span>从交易的信息密度，走向研究的验证密度。</span>
            <b>
              更快提出假设
              <br />≠ 更可靠的发现
            </b>
          </div>
          <small>NYSE 历史照片 / Carol M. Highsmith · 公有领域</small>
        </div>
      );
    case 'factor':
      return <FactorVisual />;
    case 'loop':
      return <LoopVisual />;
    case 'strategies':
      return (
        <div className="strategy-illustration">
          <div className="visual-heading">
            初始搜索配额 <span>总计 100%</span>
          </div>
          {names.map((t, i) => (
            <div className={`strategy-bar ${i > 2 ? 'explore' : ''}`} key={t}>
              <div>
                <span>
                  {pad(i + 1)} / {t}
                </span>
                <b>{weights[i]}%</b>
              </div>
              <i style={{ width: `${weights[i] * 4}%` }} />
            </div>
          ))}
          <div className="strategy-sum">
            <div>
              <strong>
                65<small>%</small>
              </strong>
              <span>利用已有结构</span>
            </div>
            <div>
              <strong>
                35<small>%</small>
              </strong>
              <span>探索未知方向</span>
            </div>
          </div>
        </div>
      );
    case 'gates':
      return <GatesVisual />;
    case 'fsa':
      return <FsaVisual />;
    case 'funnel':
      return <FunnelVisual />;
    case 'performance':
      return <PerformanceVisual />;
    case 'concentration':
      return (
        <div className="concentration-illustration">
          <div className="visual-heading">
            入库公式的字段出现比例 <span>允许重叠</span>
          </div>
          {[
            ['隔夜跳空', 85, 'open / previous close'],
            ['日内振幅', 63, '(high − low) / close'],
          ].map(([name, value, formula]) => (
            <div className="concentration-row" key={name}>
              <b>{name}</b>
              <code>{formula}</code>
              <div>
                <i style={{ width: `${value}%` }} />
                <strong>{value}%</strong>
              </div>
              <small>
                0 <span>100%</span>
              </small>
            </div>
          ))}
          <div className="overlap-note">
            85% + 63% &gt; 100%<span>同一公式可同时包含两个字段，因此不能使用饼图。</span>
          </div>
        </div>
      );
    case 'replication':
      return <ReplicationVisual />;
    case 'crowding':
      return <CrowdingVisual />;
    case 'demo':
      return (
        <div className="demo-illustration">
          <span className="lab-stamp">LIVE / HISTORICAL DATA</span>
          <div className="demo-stat">
            <strong>50</strong>
            <span>只股票的固定历史快照</span>
          </div>
          <div className="demo-flow">
            <span>01 / 生成公式</span>
            <span>02 / 现场回测</span>
            <span>03 / 查看门槛</span>
            <span>04 / 导出证据</span>
          </div>
          <Link to="/mine" className="deck-lab-link">
            进入实时挖掘 <ArrowUpRight size={22} />
          </Link>
          <p>
            建议选择 36 个候选，约半分钟。
            <br />
            暂停、刷新与继续，均保留检查点。
          </p>
          <small>本地模式 ¥0 · DeepSeek 单任务上限 ¥0.50</small>
        </div>
      );
    default:
      return (
        <div className="closing-illustration">
          <div className="closing-question">
            <span>01</span>
            <div>
              <b>能否经得起时间？</b>
              <p>冻结规则，滚动验证，报告失败。</p>
            </div>
          </div>
          <div className="closing-question">
            <span>02</span>
            <div>
              <b>能否经得起复制？</b>
              <p>固定数据版本，公开公式与计算口径。</p>
            </div>
          </div>
          <div className="closing-question">
            <span>03</span>
            <div>
              <b>能否经得起共同使用？</b>
              <p>研究容量、持仓重合与流动性反馈。</p>
            </div>
          </div>
          <div className="closing-refs">
            <b>继续阅读</b>
            <a href="https://doi.org/10.1093/rfs/hhaa009" target="_blank" rel="noreferrer">
              Gu, Kelly & Xiu · RFS, 2020 ↗
            </a>
            <Link to="/experiments">本地实验：完整结果与复核记录 ↗</Link>
            <a
              href="https://r2d3.us/visual-intro-to-machine-learning-part-1/"
              target="_blank"
              rel="noreferrer"
            >
              视觉叙事参考：R2D3 ↗
            </a>
          </div>
        </div>
      );
  }
}

export function ResearchSlide({ slide, index }: { slide: Slide; index: number }) {
  return (
    <article
      className={`research-slide theme-${slide.theme} slide-${slide.visual}`}
      aria-label={`第 ${index + 1} 页：${slide.title.replace('\n', '')}`}
    >
      <div className="slide-topline">
        <span>LOOP RESEARCH</span>
        <span>{slide.section} / RESEARCH BRIEF</span>
      </div>
      <div className="slide-body">
        <div className="slide-copy">
          <span className="slide-eyebrow">{slide.eyebrow}</span>
          <h1>{slide.title}</h1>
          <h2>{slide.subtitle}</h2>
          <div className="slide-paragraphs">
            {slide.body.map((t) => (
              <p key={t}>{t}</p>
            ))}
          </div>
          <p className="slide-takeaway">{slide.takeaway}</p>
        </div>
        <div className="slide-visual" data-visual={slide.visual}>
          <Visual kind={slide.visual} />
        </div>
      </div>
      <footer className="slide-footer">
        <span>{slide.source}</span>
        <b>
          {pad(index + 1)}
          <i> / 14</i>
        </b>
      </footer>
    </article>
  );
}

export function PresentationPage() {
  const [params, setParams] = useSearchParams();
  const parsed = Number(params.get('slide') ?? 1);
  const index = Number.isFinite(parsed)
    ? Math.max(0, Math.min(slides.length - 1, Math.floor(parsed) - 1))
    : 0;
  const capture = params.get('capture') === '1';
  const [panel, setPanel] = useState<'outline' | 'notes' | 'sources' | null>(null);
  const [error, setError] = useState('');
  const container = useRef<HTMLDivElement>(null);
  const go = (next: number) => {
    setParams({
      slide: String(Math.max(0, Math.min(13, next)) + 1),
      ...(capture ? { capture: '1' } : {}),
    });
  };
  const fullscreen = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await container.current?.requestFullscreen();
    } catch {
      setError('当前浏览器不支持全屏，可使用浏览器的全屏菜单。');
    }
  };
  useEffect(() => {
    window.scrollTo(0, 0);
    container.current?.scrollTo(0, 0);
    document.title = `${pad(index + 1)} · ${slides[index].title.replace('\n', '')} | 研究演示`;
    const onKey = (event: KeyboardEvent) => {
      if (
        (event.target as HTMLElement).closest('input,textarea,select,[contenteditable]') ||
        event.altKey ||
        event.metaKey ||
        event.ctrlKey
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
        go(13);
      }
      if (event.key.toLowerCase() === 'f') void fullscreen();
      if (event.key.toLowerCase() === 'n') setPanel((p) => (p === 'notes' ? null : 'notes'));
      if (event.key === 'Escape') setPanel(null);
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.title = 'Loop Research';
    };
  }, [index]);
  return (
    <div className={`presentation-app ${capture ? 'capture-mode' : ''}`} ref={container}>
      {!capture && (
        <header className="presentation-toolbar">
          <Link to="/" className="presentation-brand">
            <ArrowLeft size={15} />
            <b>
              LOOP <span>RESEARCH</span>
            </b>
          </Link>
          <span className="deck-toolbar-title">当 AI 开始自己挖因子</span>
          <div>
            <button
              onClick={() => setPanel(panel === 'outline' ? null : 'outline')}
              aria-expanded={panel === 'outline'}
            >
              <List size={17} />
              <span>目录</span>
            </button>
            <button
              onClick={() => setPanel(panel === 'notes' ? null : 'notes')}
              aria-expanded={panel === 'notes'}
            >
              <BookOpen size={17} />
              <span>讲稿</span>
            </button>
            <button
              onClick={() => setPanel(panel === 'sources' ? null : 'sources')}
              aria-expanded={panel === 'sources'}
            >
              <span>资料</span>
            </button>
            <button onClick={fullscreen} aria-label="全屏放映（F）">
              <Expand size={18} />
            </button>
          </div>
        </header>
      )}
      <main className="presentation-stage">
        <ResearchSlide slide={slides[index]} index={index} />
      </main>
      {!capture && (
        <>
          <footer className="presentation-controls">
            <span>
              ← → 翻页 <i>·</i> F 全屏 <i>·</i> N 讲稿
            </span>
            <div>
              <button onClick={() => go(index - 1)} disabled={index === 0} aria-label="上一页">
                <ChevronLeft size={20} />
              </button>
              <span aria-live="polite">
                {pad(index + 1)} <small>/ 14</small>
              </span>
              <button onClick={() => go(index + 1)} disabled={index === 13} aria-label="下一页">
                <ChevronRight size={20} />
              </button>
            </div>
            <Link to="/mine">
              <Play size={13} /> 现场实验 <ArrowUpRight size={14} />
            </Link>
          </footer>
          <div className="deck-progress">
            <i style={{ width: `${((index + 1) / slides.length) * 100}%` }} />
          </div>
          {error && (
            <p role="status" className="deck-error">
              {error}
            </p>
          )}
          {panel && (
            <aside
              className="presentation-drawer"
              aria-label={
                panel === 'outline'
                  ? '演示目录'
                  : panel === 'notes'
                    ? '当前页讲稿'
                    : '资料与图片来源'
              }
            >
              <div className="drawer-title">
                <h2>
                  {panel === 'outline'
                    ? '研究的路径'
                    : panel === 'notes'
                      ? `${pad(index + 1)} / 演讲提示`
                      : '资料与图片来源'}
                </h2>
                <button onClick={() => setPanel(null)} aria-label="关闭面板">
                  <X size={20} />
                </button>
              </div>
              {panel === 'outline' && (
                <ol className="deck-outline">
                  {slides.map((s, i) => (
                    <li key={s.visual}>
                      <button
                        className={i === index ? 'active' : ''}
                        onClick={() => {
                          go(i);
                          setPanel(null);
                        }}
                      >
                        <span>{pad(i + 1)}</span>
                        <div>
                          <small>{s.section}</small>
                          <strong>{s.title.replace('\n', '')}</strong>
                        </div>
                        <ChevronRight size={15} />
                      </button>
                    </li>
                  ))}
                </ol>
              )}
              {panel === 'notes' && (
                <div className="deck-notes">
                  <h3>{slides[index].subtitle}</h3>
                  <p>{slides[index].notes}</p>
                  <hr />
                  <small>{slides[index].source}</small>
                </div>
              )}
              {panel === 'sources' && (
                <div className="deck-notes">
                  <h3>研究资料</h3>
                  <p>
                    主体内容依据用户提供的《案例 G：中金 AI
                    因子挖掘案例分析》。所引中金数据为材料转述的历史回测，不等于独立复核或实盘。
                  </p>
                  <a
                    href="https://mp.weixin.qq.com/s/hrKdYATh_9rdASVAdjGymg"
                    target="_blank"
                    rel="noreferrer"
                  >
                    材料所引中金报告 ↗
                  </a>
                  <a href="https://doi.org/10.1093/rfs/hhaa009" target="_blank" rel="noreferrer">
                    Gu, Kelly & Xiu (2020) ↗
                  </a>
                  <Link to="/experiments">本地 v2 实验、协议与留出结果 ↗</Link>
                  <a
                    href="https://github.com/yumoxu/stocknet-dataset/tree/330708b5ddc359961078bef469f43f48992fd6e4"
                    target="_blank"
                    rel="noreferrer"
                  >
                    历史价量数据：StockNet 固定版本 ↗
                  </a>
                  <h3>图像来源</h3>
                  <p>照片均为背景或概念配图，不展示中金内部场景。图表按注明来源重绘。</p>
                  <a
                    href="https://commons.wikimedia.org/wiki/File:Pudong_Shanghai_November_2017_panorama.jpg"
                    target="_blank"
                    rel="noreferrer"
                  >
                    上海：King of Hearts · CC BY-SA 4.0 ↗
                  </a>
                  <a
                    href="https://commons.wikimedia.org/wiki/File:New_York_Stock_Exchange_trading_floor_on_Wall_Street,_New_York,_New_York_LCCN2011634218.tif"
                    target="_blank"
                    rel="noreferrer"
                  >
                    NYSE：Carol M. Highsmith · 公有领域 ↗
                  </a>
                  <a
                    href="https://commons.wikimedia.org/wiki/File:Server_racks_near_the_GBAR_experiment.jpg"
                    target="_blank"
                    rel="noreferrer"
                  >
                    CERN 机柜：Unnerving duck · CC BY-SA 4.0 ↗
                  </a>
                  <a
                    href="https://creativecommons.org/licenses/by-sa/4.0/"
                    target="_blank"
                    rel="noreferrer"
                  >
                    CC BY-SA 4.0 授权说明 ↗
                  </a>
                  <p>
                    照片原文件未修改，页面仅作容器裁切。字体使用 Noto，遵循 SIL Open Font
                    License。参考网页提供排版灵感，未复制图文。
                  </p>
                  <a href={`${root}sources.json`}>完整图像清单与原文件地址 ↗</a>
                </div>
              )}
            </aside>
          )}
        </>
      )}
    </div>
  );
}
