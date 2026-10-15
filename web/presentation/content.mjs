// Layouts adapted from guizang-ppt-skill Style A, AGPL-3.0.
// Research figures use the supplied case and archived local experiment only.
export function renderSlides({ slides, results, plan, escape, pad, icons }) {
  const label = (text) => `<div class='kicker'>${escape(text)}</div>`;
  const heading = (i, lead = true) =>
    `${label(slides[i].eyebrow)}<h1 class='h-xl'>${plan[i].title}</h1>${lead ? `<p class='lead'>${escape(slides[i].subtitle)}</p>` : ''}`;
  const prose = (i) =>
    `<div class='body-zh'>${slides[i].body.map((t) => `<p>${escape(t)}</p>`).join('')}</div>`;
  const takeaway = (i) => `<p class='callout'>${escape(slides[i].takeaway)}</p>`;
  const photo = (name, alt, caption, height = '38vh') =>
    `<figure class='frame-img' style='height:${height}'><img src='${name}.jpg' alt='${escape(alt)}'><figcaption class='img-cap'>${escape(caption)}</figcaption></figure>`;
  const stat = (name, number, unit, note) =>
    `<div class='stat-card'><div class='stat-label'>${name}</div><div class='stat-nb'>${number}<span class='stat-unit'>${unit}</span></div><p class='stat-note'>${note}</p></div>`;
  const split = (left, right, ratio = 'grid-2-6-6') =>
    `<div class='frame ${ratio}'><div class='col'>${left}</div><div class='col'>${right}</div></div>`;
  const step = (n, title, description) =>
    `<div class='step'><span class='step-nb'>${n}</span><h2 class='step-title'>${title}</h2><p class='step-desc'>${description}</p></div>`;
  const bar = (name, value, max = 100, unit = '%') =>
    `<div class='rowline' style='grid-template-columns:1fr auto'><span>${name}</span><b>${value}${unit}</b><div style='grid-column:1/-1;height:7px;background:var(--faint)'><div style='height:100%;width:${(value / max) * 100}%;background:currentColor'></div></div></div>`;
  const score = (value, i) =>
    `<div class='rowline' style='grid-template-columns:7em 1fr 2em;align-items:center'><span>股票 ${'ABCDE'[i]}${i === 0 ? ' · 选入' : ''}</span><div style='height:7px;background:var(--faint)'><div style='width:${value}%;height:100%;background:currentColor'></div></div><b>${value}</b></div>`;
  const y = (n) => 54 + ((0.26 - n) / 0.43) * 300;
  const pairedChart = `<figure aria-label='23 个入库因子的开发筛选期与留出期年化超额配对图'>
    <div class='meta-row' style='justify-content:space-between'><span>开发筛选期</span><span>留出期</span></div>
    <svg viewBox='0 0 600 430' role='img' aria-label='23 个因子中仅 1 个留出年化超额为正'>
      ${[-0.1, 0, 0.1, 0.2].map((v) => `<line x1='65' x2='548' y1='${y(v)}' y2='${y(v)}' stroke='currentColor' stroke-opacity='${v === 0 ? 0.65 : 0.16}' ${v === 0 ? "stroke-dasharray='5 6'" : ''}/><text x='8' y='${y(v) + 5}'>${Math.round(v * 100)}%</text>`).join('')}
      ${results.factors.map((f) => `<g><title>${f.id}: ${(f.selection * 100).toFixed(2)}% → ${(f.holdout * 100).toFixed(2)}%</title><line x1='130' x2='455' y1='${y(f.selection)}' y2='${y(f.holdout)}' stroke='currentColor' stroke-opacity='.32'/><circle cx='130' cy='${y(f.selection)}' r='4' fill='currentColor'/><circle cx='455' cy='${y(f.holdout)}' r='${f.holdout > 0 ? 6 : 4}' stroke='currentColor' fill='${f.holdout > 0 ? 'currentColor' : 'var(--ink)'}'/></g>`).join('')}
      <text x='130' y='401' text-anchor='middle'>2014—2015</text><text x='455' y='401' text-anchor='middle'>2016—2017.09</text>
    </svg><figcaption class='meta'>单因子年化超额 · 每条连线 = 同一因子 · 空心点为负值</figcaption></figure>`;
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
  return [
    split(
      `${label('CASE G · RESEARCH AS A SYSTEM')}<h1 class='h-hero'>因子工厂</h1><p class='sign'>The Factor Factory</p><h2 class='h-sub'>当 AI 开始<br>自己挖因子</h2><p class='lead'>中金自动化因子发现引擎<br>机制、证据与边界</p>`,
      `${photo('shanghai', '上海浦东天际线，金融研究背景配图', 'SHANGHAI / King of Hearts · CC BY-SA 4.0', '43vh')}<div class='meta-row'><span>HYPOTHESIS</span><span>EVIDENCE</span><span>LIMITS</span></div><p class='body-zh'>一项关于研究生产方式的案例研究。<br>因子可以批量生成，证据仍需逐条建立。</p>`,
    ),
    split(
      `${heading(1)}${prose(1)}${takeaway(1)}`,
      `${photo('trading-floor', '纽约证券交易所历史交易大厅，非中金内部场景', 'NYSE / Carol M. Highsmith · 公有领域', '35vh')}<h2 class='h-md' style='margin-top:2vh'>更快提出假设<br><span style='opacity:.6'>≠ 更可靠的发现</span></h2>`,
    ),
    split(
      `${heading(2)}${prose(2)}${takeaway(2)}`,
      `<div class='meta'>A HYPOTHESIS / 教学示意</div><code style='font-size:2.15vw;margin:1vh 0;display:block'>rank(−mean(gap, 5))</code><p class='body-zh'>近期隔夜跳空越弱，未来是否越强？</p><div>${[86, 63, 45, 31, 18].map((v, i) => score(v, i)).join('')}</div><div class='pipeline' data-cols='3'>${step('t', '收盘', '形成信号')}${step('t + 1', '开盘', '执行交易')}${step('5 DAYS', '再平衡', '持有 5 个交易日')}</div><p class='meta'>分数为示意值；真实实验使用 50 股截面。</p>`,
    ),
    `<div class='frame'><div>${heading(3)}</div><div class='pipeline' data-cols='3' style='margin-top:4vh'>${step('01', '生成假设', '模型提出可解释的价量公式')}${step('02', '独立审查', '在独立上下文检查逻辑与时间安全')}${step('03', '程序验证', '确定性回测与联合门槛决定入库')}</div><div class='row' style='border-block:1px solid var(--line);padding:2vh 0;margin-top:3vh'>${icons.loop}<span class='body-zh'>反馈到下一批：指标、拒绝原因、结构频率</span></div><div class='grid-2-6-6' style='margin-top:3vh'>${photo('servers', 'CERN GBAR 附近机柜，作为计算基础设施概念配图', 'CERN GBAR / Unnerving duck · CC BY-SA 4.0', '18vh')}<div class='col'><p class='body-zh'>${escape(slides[3].body[1])}</p><p class='h-md'>让模型提问，让程序给证据。</p></div></div></div>`,
    `<div class='frame'>${heading(4, false)}<p class='lead'>五种初始配额，两个搜索方向。</p><div class='grid-2-6-6' style='margin-top:3vh'><div>${stat('EXPLOIT', '65', '%', '利用已有结构')}${[
      ['变异', 25],
      ['交叉', 25],
      ['参数扰动', 15],
    ]
      .map(([n, v]) => bar(n, v, 25))
      .join('')}</div><div>${stat('EXPLORE', '35', '%', '探索未知方向')}${[
      ['随机生成', 15],
      ['机制引导', 20],
    ]
      .map(([n, v]) => bar(n, v, 25))
      .join(
        '',
      )}<p class='body-zh' style='margin-top:3vh'>材料描述动态调整，未提供完整逐轮记录。<br>这里展示初始配置，不推测演化轨迹。</p></div></div><p class='meta' style='margin-top:2vh'>条形共用 0—25% 尺度；分组大数字表示合计配额。机制引导覆盖 13 类机制。</p></div>`,
    split(
      `${heading(5)}${prose(5)}${takeaway(5)}`,
      `<div class='grid-2-6-6' style='gap:3vw'>${[gates.slice(0, 6), gates.slice(6)].map((group, gi) => `<div>${group.map(([name, value], i) => `<div class='rowline' style='grid-template-columns:1fr auto;${gi === 1 && i > 2 ? 'border-top-style:dashed' : ''}'><div><span class='meta'>${pad(gi * 6 + i + 1)}</span><p class='body-zh'>${name}</p></div><b style='font-size:1.55vw'>${escape(value)}</b></div>`).join('')}</div>`).join('')}</div><p class='meta'>01—09：材料明确条件的本地改写<br>10—11：本地工程补充；虚线分隔</p>`,
    ),
    split(
      `${heading(6)}${prose(6)}<div class='stat-card'><div class='stat-label'>SKELETON FREQUENCY</div><div class='stat-nb'>15<span class='stat-unit'>%</span></div><p class='stat-note'>骨架使用率超过阈值 → 暂时冻结</p></div>`,
      `<div class='meta'>不同参数 / 相同骨架</div><div>${[20, 40, 60].map((v) => `<div class='rowline' style='grid-template-columns:1fr'><code>cs_rank(ts_mean(gap, <b>${v}</b>))</code></div>`).join('')}</div><div>${icons.down}</div><code style='font-size:1.4vw'>cs_rank(ts_mean(gap, WINDOW))</code><div class='pipeline' data-cols='3' style='margin-top:3vh'>${step('4', '前 50 轮', '累计入库')}${step('+51', '401–450 轮', '区间新增')}${step('450+', '后续阶段', '转向新结构')}</div><p class='meta'>离散阶段，不插补完整收敛曲线。</p>`,
    ),
    `<div class='frame'>${heading(7, false)}<div class='row' style='justify-content:space-between;align-items:flex-end;margin:2vh 0 3vh'><div><div class='meta'>CANDIDATES</div><div class='display' style='font-size:7vw;margin-top:2vh'>16,939</div></div><span style='padding-bottom:3vh'>${icons.wide}</span><div><div class='meta'>RETAINED</div><div class='display' style='font-size:18vw;margin-top:1vh'>69</div></div><div style='padding-bottom:1vh'><div class='big-num' style='font-size:6vw'>0.41<span style='font-size:.4em'>%</span></div><p class='body-zh' style='margin-top:2vh'>3 天 · 581 轮<br>入选不等于有效投资信号</p></div></div><div class='grid-2-7-5'><div><div style='display:grid;grid-template-columns:repeat(50,1fr);gap:4px'>${Array.from({ length: 500 }, (_, i) => `<i style='height:5px;background:currentColor;opacity:${i < 2 ? 1 : 0.16}'></i>`).join('')}</div><p class='meta' style='margin-top:1.5vh'>500 个点中突出 2 个，近似示意 0.4%；不是逐候选观测。</p></div><p class='body-zh'>低通过率既可能来自严格门槛，也可能留下少数历史幸运者。<br><strong>换一段时间，还成立吗？</strong></p></div></div>`,
    split(
      `${heading(8)}${prose(8)}${takeaway(8)}`,
      `<div class='meta'>ANNUALIZED EXCESS RETURN / 历史回测</div><div>${bar('69 因子平均', 14.5, 25)}${bar('Top 5 等权组合', 18.3, 25)}</div><div class='meta-row' style='justify-content:space-between'><span>0</span><span>5</span><span>10</span><span>15</span><span>20</span><span>25%</span></div><div style='margin-top:3vh'>${stat('TOP 5 SHARPE', '3.14', '', '材料披露；尚待独立样本外与冲击成本验证')}</div><p class='meta'>单因子均值与组合不是同一统计对象。</p>`,
    ),
    `<div class='frame'>${heading(9, false)}<p class='lead'>结构不同，信息来源仍可能相似。</p><div class='grid-2-6-6' style='margin-top:4vh'>${[
      ['85', '隔夜跳空', 'open / previous close'],
      ['63', '日内振幅', '(high − low) / close'],
    ]
      .map(
        ([value, name, formula]) =>
          `<div>${stat(name, value, '%', '入库公式的字段出现比例')}<div style='height:8px;background:var(--faint);margin:3vh 0 1vh'><div style='width:${value}%;height:100%;background:currentColor'></div></div><div class='meta-row' style='justify-content:space-between'><span>0</span><span>100%</span></div><code style='display:block;margin-top:3vh'>${escape(formula)}</code></div>`,
      )
      .join(
        '',
      )}</div><div class='rowline' style='grid-template-columns:1fr 1fr;margin-top:3vh'><p class='body-zh'>同一公式可包含两个字段。<br><strong>85% + 63% &gt; 100% 并不矛盾。</strong></p><p class='body-zh'>FSA 后新结构平均夏普 0.92，<br>核心结构为 1.68。多样性与历史表现存在张力。</p></div></div>`,
    split(
      `${heading(10, false)}<p class='lead'>入库不为零，样本外却退化了。</p><div style='margin:2vh 0 1vh'><div class='big-num' style='font-size:8.2vw'>−3.18<span style='font-size:.4em'>%</span></div><p class='meta' style='margin-top:2vh'>固定 TOP 5 / 留出期年化超额 / 扣费后</p></div><p class='body-zh'>6,637 次尝试 → 966 次回测 → 23 个入库。<br>冻结后，只有 <strong>1 / 23</strong> 留出年化超额为正。</p><p class='callout'>能运行的研究流程，<br>仍然需要经受下一段时间的检验。</p>`,
      pairedChart,
    ),
    `<div class='frame'>${heading(11, false)}<p class='lead'>系统内去重，市场里仍可能拥挤。</p><div class='pipeline' data-cols='3' style='margin-top:4vh'>${['A', 'B', 'C'].map((v, i) => step(pad(i + 1), `机构 ${v}`, '各自独立的研究循环')).join('')}</div><div class='row' style='justify-content:center;padding:2vh 0'>${icons.down}</div><div class='rowline' style='grid-template-columns:1fr 1fr'><h2 class='h-md'>相近字段 · 模型 · 筛选目标</h2><p class='body-zh'>不同公式可能导向重叠持仓。<br>这是机制讨论，不是估计出的因果效应。</p></div><div class='row' style='justify-content:space-between;margin-top:4vh'><h2 class='h-md'>同时减仓</h2>${icons.right}<h2 class='h-md'>流动性压力</h2>${icons.right}<h2 class='h-md'>冲击放大</h2></div><p class='body-zh' style='margin-top:4vh'>研究问题：控制收益相关性后，不同模型生成的组合还有多少持仓重合？</p></div>`,
    split(
      `${heading(12)}${prose(12)}<a class='lab-link' href='/mine' target='_top'>进入实时挖掘 ${icons.upRight}</a><p class='meta'>短演示可选 36 个；支持暂停、刷新与继续。</p>`,
      `<div class='meta'>LIVE LAB / HISTORICAL SNAPSHOT</div><div class='display' style='font-size:11vw;margin-top:2vh'>1,200</div><p class='lead'>个候选 / 完整搜索上限</p><div class='grid-2-6-6'>${stat('DEEPSEEK', '¥5', '', '单次默认上限，可选 ¥1 / 3 / 5 / 10')}${stat('SHARED CAP', '¥40', '', '累计上限，保留历史账本')}</div><p class='body-zh' style='margin-top:3vh'>50 股 · 2012–2015 开发期快照<br>本地计算免费；已知种子复算单独计数。</p>`,
    ),
    `<div class='frame' style='justify-content:center'>${label('WHAT CHANGES, WHAT REMAINS')}<h1 class='h-hero' style='font-size:5.6vw;line-height:1.45;font-weight:500'>生产方式变了。<br>证据标准不能变。</h1><p class='lead' style='margin-top:3vh;max-width:65vw'>AI 降低提出假设的成本。真正稀缺的，是能经受反证、可以被复核的知识。</p><div class='pipeline' data-cols='3' style='margin-top:5vh'>${step('01', '经得起时间', '冻结规则，滚动验证，报告失败。')}${step('02', '经得起复制', '固定数据版本，公开公式与口径。')}${step('03', '经得起共同使用', '研究容量、持仓重合与流动性反馈。')}</div></div>`,
  ];
}
