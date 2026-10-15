import { useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Braces,
  CheckCheck,
  Fingerprint,
  FlaskConical,
  GitBranch,
  Layers3,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { CheckItem, EmptyState, LoopDiagram, SectionHeading } from '../components';
import { stages, strategies } from '../content';

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
            <Link className="button navy large" to="/console">
              打开研究控制台 <ArrowUpRight size={18} />
            </Link>
            <Link className="text-link" to="/research">
              理解循环原理 <ArrowRight size={16} />
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
          本项目参考中金公开研报及用户提供的案例分析，复现发现流程与工程机制。研报历史回测、本地演示与后续真实实验将分别标注。
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
              代码框架与本地流程演示。没有市场实验结果；目标模型的官方 ID
              尚待核实。公开数据实验计划使用美股，不能据此声称复现 A 股收益。
            </p>
            <Link to="/experiments">
              查看实验准备状态 <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

export function ExperimentsPage() {
  return (
    <main className="page-width experiments-page">
      <div className="page-intro">
        <span className="eyebrow">EXPERIMENT REGISTRY</span>
        <h1>让结果来自真实运行。</h1>
        <p>记录配置、数据与完整过程，让每一个结果都可以追溯。</p>
      </div>
      <div className="panel experiment-empty">
        <EmptyState
          icon={<FlaskConical size={34} strokeWidth={1.2} />}
          title="实验尚未开始"
          action={
            <Link className="button navy" to="/console">
              先了解运行控制台 <ArrowUpRight size={16} />
            </Link>
          }
        >
          当前按计划搭建前后端框架，未下载实验数据，也未调用付费模型。
          <br />
          演示任务仅验证程序流程，不会出现在真实实验结果中。
        </EmptyState>
      </div>
      <div className="section-heading small-heading">
        <span className="eyebrow">PLANNED COMPARISONS</span>
        <h2>后续实验，已经有清晰的对照。</h2>
      </div>
      <div className="comparison-grid">
        {[
          ['E0', '传统因子基线', '6 个固定价量因子', Braces],
          ['E1', '随机搜索', '受限 DSL 的随机候选', GitBranch],
          ['E2', '完整 Loop', '五种策略、审查与 FSA', Layers3],
          ['E3', '关闭 FSA', '观察结构重复与覆盖差异', CheckCheck],
        ].map(([id, name, description, Icon]) => {
          const Glyph = Icon as typeof Braces;
          return (
            <article className="panel comparison" key={id as string}>
              <div>
                <span className="mono">{id as string}</span>
                <Glyph size={20} />
              </div>
              <h3>{name as string}</h3>
              <p>{description as string}</p>
              <span className="planned">待实施</span>
            </article>
          );
        })}
      </div>
      <p className="source-note experiment-note">
        计划使用最多 50 只股票与 300
        次候选尝试。真实运行前冻结数据、时间切分和预算；没有因子通过筛选也是可报告的结果。
      </p>
    </main>
  );
}
