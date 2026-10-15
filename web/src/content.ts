export const strategies = [
  {
    id: 'mutation',
    name: '结构变异',
    weight: 25,
    description: '替换已有公式的局部结构，沿着有解释力的方向继续探索。',
  },
  {
    id: 'crossover',
    name: '因子交叉',
    weight: 25,
    description: '让两类信号相遇，检查它们之间是否存在新的作用机制。',
  },
  {
    id: 'perturbation',
    name: '参数扰动',
    weight: 15,
    description: '改变时间窗口与有限参数，观察同一假设的尺度变化。',
  },
  {
    id: 'random',
    name: '随机探索',
    weight: 15,
    description: '走出已有因子附近，为尚未覆盖的结构保留探索空间。',
  },
  {
    id: 'mechanism',
    name: '机制引导',
    weight: 20,
    description: '由大模型从经济假设出发，提出值得被检验的表达式。',
  },
];
export const strategyName = (id: string) => strategies.find((s) => s.id === id)?.name || id;
export const stateLabels: Record<string, string> = {
  draft: '待启动',
  queued: '排队中',
  running: '运行中',
  pause_requested: '正在暂停',
  paused: '已暂停',
  stop_requested: '正在停止',
  stopped: '已停止',
  completed: '已完成',
  failed: '失败',
  interrupted: '已中断',
  budget_exhausted: '预算用尽',
  awaiting_data: '等待数据',
  rejected: '规则拒绝',
  duplicate: '表达式重复',
  fsa_blocked: '骨架冻结',
  passed: '通过',
  not_evaluated: '尚未计算',
};
export const stages = [
  {
    name: '提出假设',
    en: 'GENERATE',
    description: '五种策略共同探索候选空间。模型输出公式与机制假设，不直接预测股票收益。',
    input: '算子与字段、父代候选、机制覆盖',
    output: '结构化公式、经济假设、候选血缘',
  },
  {
    name: '审查表达',
    en: 'REVIEW',
    description: '先用程序检查语法、量纲与复杂度，再独立审查逻辑与边界条件。',
    input: '候选公式、数据边界、审查规则',
    output: '通过或拒绝，以及可追踪的原因',
  },
  {
    name: '验证信号',
    en: 'VERIFY',
    description: '由确定性回测计算指标，使用分期检验、交易成本与联合过滤决定是否入库。',
    input: '历史数据、固定阈值、交易约定',
    output: '指标明细、逐项门槛、验证结论',
  },
  {
    name: '反馈迭代',
    en: 'EVOLVE',
    description: '将结果、重复结构和机制覆盖反馈到下一轮，保持探索与利用的平衡。',
    input: '拒绝原因、因子库、高频骨架',
    output: '更新的搜索方向与持久化检查点',
  },
];
