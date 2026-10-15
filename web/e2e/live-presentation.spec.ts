import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('historical live run computes evidence, resumes, distinguishes seeds and exports', async ({
  page,
}, testInfo) => {
  test.setTimeout(100000);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/mine');
  await expect(page.getByText('研究引擎在线', { exact: true })).toBeVisible();
  await expect(page.getByLabel('候选数', { exact: true })).toHaveValue('1200');
  await page.getByLabel('候选数', { exact: true }).selectOption('120');
  await page.getByRole('button', { name: '开始现场挖掘', exact: true }).click();
  await expect(page).toHaveURL(/\/mine\/[a-f0-9]+$/);
  const id = page.url().split('/').pop();
  const current = async () => (await page.request.get(`/api/v1/runs/${id}`)).json();
  await expect.poll(async () => (await current()).cursor).toBeGreaterThan(0);
  await page.getByRole('button', { name: '暂停', exact: true }).click();
  await expect.poll(async () => (await current()).state).toBe('paused');
  const cursor = (await current()).cursor;
  await page.reload();
  await expect(page.getByRole('button', { name: '继续', exact: true })).toBeVisible();
  expect((await current()).cursor).toBe(cursor);
  await page.getByRole('button', { name: '继续', exact: true }).click();
  await expect.poll(async () => (await current()).state, { timeout: 70000 }).toBe('completed');
  const final = await current();
  expect(final.counts.accepted).toBeGreaterThanOrEqual(6);
  expect(final.counts.model_calls).toBe(0);
  await expect(page.getByRole('navigation', { name: '候选分页' })).toBeVisible();
  await page.getByRole('button', { name: '上一页', exact: true }).click();
  await page.locator('.live-candidate').first().click();
  await expect(page.locator('.live-origin')).toContainText('已知研究种子');
  await expect(page.locator('.live-gate')).toHaveCount(11);
  await expect(page.locator('.live-gate.not_applicable')).toHaveCount(1);
  await expect(page.locator('.live-nav-chart path')).toBeVisible();
  await expect(page.locator('.live-counts')).toContainText('其中新候选');
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出', exact: true }).click();
  const report = JSON.parse(await readFile((await (await downloaded).path())!, 'utf8'));
  expect(report.is_experiment).toBe(true);
  expect(report.candidates).toHaveLength(120);
  expect(report.candidates[0].metrics.abs_ic).toBeCloseTo(0.07177635166667387, 10);
  await page.screenshot({ path: testInfo.outputPath('live-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('live-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(errors).toEqual([]);
});

test('large task settings persist and a 1200 candidate job can be stopped', async ({
  page,
}, testInfo) => {
  await page.goto('/mine');
  await expect(page.getByText('研究引擎在线', { exact: true })).toBeVisible();
  await expect(page.getByLabel('候选数', { exact: true })).toHaveValue('1200');
  await page.getByRole('button', { name: 'DeepSeek 引导' }).click();
  await expect(page.getByLabel('单次模型预算')).toHaveValue('5');
  await page.getByLabel('单次模型预算').selectOption('10');
  await page.getByLabel('时间上限').selectOption('30');
  await page.screenshot({
    path: testInfo.outputPath('large-settings-desktop.png'),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('large-settings-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.getByRole('button', { name: '本地搜索' }).click();
  await page.getByRole('button', { name: '开始现场挖掘', exact: true }).click();
  await expect(page).toHaveURL(/\/mine\/[a-f0-9]+$/);
  const id = page.url().split('/').pop();
  const current = async () => (await page.request.get(`/api/v1/runs/${id}`)).json();
  const run = await current();
  expect(run.target).toBe(1200);
  expect(run.config.max_model_cny).toBe(10);
  expect(run.config.max_seconds).toBe(1800);
  await page.getByRole('button', { name: '停止', exact: true }).click();
  await expect.poll(async () => (await current()).state).toBe('stopped');
  expect((await current()).counts.model_calls).toBe(0);
});

test('research deck has fourteen complete slides, navigation, notes and an integrated live lab', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/presentation');
  await page.evaluate(() => document.fonts.ready);
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/slide=2/);
  await page.keyboard.press('n');
  await expect(page.getByRole('complementary', { name: '当前页讲稿' })).toContainText(
    '每天 10 个因子是假设',
  );
  await page.getByRole('button', { name: '关闭面板' }).click();
  await page.getByRole('button', { name: '目录', exact: true }).click();
  await expect(page.locator('.deck-outline li')).toHaveCount(14);
  await page.locator('.deck-outline button').nth(10).click();
  await expect(page.locator('.presentation-stage h1')).toContainText('样本外却退化了');
  await expect(page.locator('.presentation-stage .holdout-callout')).toContainText('−3.18');
  await expect(page.locator('.presentation-toolbar a[download]')).toHaveCount(0);
  for (let i = 1; i <= 14; i++) {
    await page.goto(`/presentation?slide=${i}`);
    const bounds = await page.locator('.presentation-stage .research-slide').evaluate((el) => ({
      h: el.scrollHeight - el.clientHeight,
      w: el.scrollWidth - el.clientWidth,
    }));
    expect(bounds.h).toBeLessThanOrEqual(2);
    expect(bounds.w).toBeLessThanOrEqual(2);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/presentation?slide=6');
  await page.screenshot({ path: testInfo.outputPath('deck-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.goto('/presentation?slide=13');
  await page.locator('.presentation-stage').getByRole('link', { name: '进入实时挖掘' }).click();
  await expect(page).toHaveURL(/\/mine$/);
  expect(errors).toEqual([]);
});
