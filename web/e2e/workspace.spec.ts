import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('research pages and responsive layout clearly identify unrun experiments', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('可验证');
  await page.screenshot({ path: testInfo.outputPath('home-desktop.png'), fullPage: true });
  await page
    .getByRole('navigation', { name: '网站导航' })
    .getByRole('link', { name: '原理与方法' })
    .click();
  await page.getByRole('button', { name: /验证信号/ }).click();
  await expect(page.locator('.stage-detail h2')).toHaveText('验证信号');
  await page
    .getByRole('navigation', { name: '网站导航' })
    .getByRole('link', { name: '实验记录' })
    .click();
  await expect(page.getByRole('heading', { name: '实验尚未开始' })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.screenshot({ path: testInfo.outputPath('home-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.goto('/console/settings');
  await expect(page.getByText('真实运行通道', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '检查本地配置' }).click();
  await expect(page.getByRole('status')).toContainText('未发送远程模型请求');
  await page.screenshot({ path: testInfo.outputPath('settings-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(errors).toEqual([]);
});

test('a real backend fixture task can pause, resume, inspect, stop and export', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/console');
  await expect(page.getByText('Worker 已连接')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('console-empty.png'), fullPage: true });
  await page.getByRole('button', { name: '新建演示任务', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('任务名称').fill('E2E 本地流程');
  await dialog.getByLabel('迭代轮数').fill('10');
  await dialog.getByLabel('每轮候选数').fill('20');
  await dialog.getByLabel('候选尝试上限').fill('200');
  await dialog.getByRole('button', { name: '创建并启动' }).click();
  await expect(page).toHaveURL(/\/console\/runs\/[a-f0-9]+$/);
  const runId = page.url().split('/').pop();
  const current = async () => (await page.request.get(`/api/v1/runs/${runId}`)).json();
  await expect.poll(async () => (await current()).cursor).toBeGreaterThan(0);
  await page.getByRole('button', { name: '暂停', exact: true }).click();
  await expect.poll(async () => (await current()).state).toBe('paused');
  const cursor = (await current()).cursor;
  await page.reload();
  await expect(page.locator('.run-subtitle')).toContainText('已暂停');
  expect((await current()).cursor).toBe(cursor);
  await page.getByRole('button', { name: '继续运行' }).click();
  await expect.poll(async () => (await current()).cursor).toBeGreaterThan(cursor);
  await page.getByRole('link', { name: '候选 001', exact: true }).click();
  await expect(page.getByText('尚未计算', { exact: true })).toHaveCount(11);
  await expect(page.getByText('LLM 审查：未运行')).toBeVisible();
  await page.getByRole('link', { name: '返回运行记录' }).click();
  await page.getByRole('button', { name: '停止', exact: true }).click();
  await expect.poll(async () => (await current()).state).toBe('stopped');
  await expect(page.locator('.event-list')).toContainText('检查点');
  await page.screenshot({ path: testInfo.outputPath('run-desktop.png'), fullPage: true });
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出记录' }).click();
  const download = await downloadPromise;
  const record = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(record.is_experiment).toBe(false);
  expect(record.run.counts.model_calls).toBe(0);
  expect(record.candidates.length).toBeGreaterThan(0);
  await page.goto('/console');
  await page.getByLabel('因子表达式').fill('__import__("os")');
  await page.getByRole('button', { name: '校验公式' }).click();
  await expect(page.getByRole('alert')).toContainText('不支持');
  await page.getByLabel('因子表达式').fill('ts_mean(gap, 5)');
  await page.getByRole('button', { name: '校验公式' }).click();
  await expect(page.getByRole('status')).toContainText('结构校验通过');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: testInfo.outputPath('console-mobile.png'), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  expect(errors).toEqual([]);
});
