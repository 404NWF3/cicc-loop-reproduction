import { test, expect } from '@playwright/test';

const title = '因子工厂 · 14 页研究演示';
const deck = (page: import('@playwright/test').Page) =>
  page.frameLocator(`iframe[title='${title}']`);

test('Style A deck preserves research evidence, navigation, notes, sources and the live lab', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  const remote: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('request', (r) => {
    if (!r.url().startsWith('http://127.0.0.1:5174')) remote.push(r.url());
  });
  await page.goto('/presentation');
  const frame = deck(page);
  await expect(frame.locator('#deck>.slide:not([inert]) h1')).toHaveText('因子工厂');
  await page.keyboard.press('ArrowRight');
  await expect(page).toHaveURL(/slide=2/);
  await page.keyboard.press('n');
  await expect(page.getByRole('dialog', { name: '当前页讲稿' })).toContainText(
    '每天 10 个因子是假设',
  );
  await page.getByRole('button', { name: '关闭面板' }).click();
  await page.getByRole('button', { name: '目录', exact: true }).click();
  await expect(frame.locator('#overview [role=button]')).toHaveCount(14);
  await frame.locator('#overview [role=button]').nth(10).click();
  await expect(page).toHaveURL(/slide=11/);
  await expect(frame.locator('#deck>.slide:not([inert])')).toContainText('−3.18');
  await expect(frame.locator('#deck>.slide:not([inert]) svg circle')).toHaveCount(46);
  await page.goBack();
  await expect(frame.locator('#deck>.slide:not([inert]) h1')).toHaveText('搜索悖论');
  await page.getByRole('button', { name: '资料', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('guizang-ppt-skill');
  await expect(page.getByRole('link', { name: '演示源码与 AGPL-3.0 许可 ↗' })).toHaveAttribute(
    'href',
    '/presentation/source/index.html',
  );
  await page.getByRole('button', { name: '关闭面板' }).click();
  expect(await page.locator('a[download]').count()).toBe(0);
  expect(await frame.locator('a[download]').count()).toBe(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/presentation?slide=6');
  await frame
    .locator('#deck>.slide:not([inert])')
    .getByText('样本量', { exact: true })
    .scrollIntoViewIfNeeded();
  await expect(
    frame.locator('#deck>.slide:not([inert])').getByText('样本量', { exact: true }),
  ).toBeInViewport();
  await page.screenshot({ path: testInfo.outputPath('style-a-mobile.png') });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.goto('/presentation?slide=13');
  await frame.getByRole('link', { name: '进入实时挖掘' }).click();
  await expect(page).toHaveURL(/\/mine$/);
  expect(errors).toEqual([]);
  expect(remote).toEqual([]);
});

test('all fourteen research slides retain readable content above the footer at common screen sizes', async ({
  page,
}, testInfo) => {
  test.setTimeout(60000);
  const results: unknown[] = [];
  for (const viewport of [
    { width: 1440, height: 950 },
    { width: 1280, height: 720 },
    { width: 1000, height: 700 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto('/presentation?slide=1');
    const frame = deck(page);
    await frame.locator('#deck').evaluate(() => document.fonts.ready);
    for (let i = 0; i < 14; i++) {
      await frame.locator('#nav .dot').nth(i).click();
      const slide = frame.locator('#deck>.slide').nth(i);
      await expect(slide).not.toHaveAttribute('inert', '');
      const measured = await slide.evaluate((el) => {
        const bounds = el.getBoundingClientRect();
        const foot = el.querySelector('.foot')!.getBoundingClientRect();
        const nodes = [
          ...el.querySelectorAll(
            '.frame h1,.frame h2,.frame p,.frame figure,.frame code,.frame .stat-nb,.frame .meta',
          ),
        ];
        const content = nodes.map((n) => n.getBoundingClientRect()).filter((r) => r.height > 0);
        return {
          id: (el as HTMLElement).dataset.slideId,
          overX: el.scrollWidth - el.clientWidth,
          gap: foot.top - Math.max(...content.map((r) => r.bottom)),
          left: Math.min(...content.map((r) => r.left)) - bounds.left,
          right: bounds.right - Math.max(...content.map((r) => r.right)),
        };
      });
      results.push({ ...viewport, ...measured });
      expect(
        measured.overX,
        `${viewport.width} / ${measured.id} horizontal overflow`,
      ).toBeLessThanOrEqual(2);
      expect(
        measured.gap,
        `${viewport.width} / ${measured.id} footer clearance`,
      ).toBeGreaterThanOrEqual(12);
      expect(Math.min(measured.left, measured.right)).toBeGreaterThanOrEqual(0);
      if (viewport.width === 1440 && [0, 3, 7, 10, 13].includes(i))
        await slide.screenshot({ path: testInfo.outputPath(`style-a-${i + 1}.png`) });
    }
  }
  await testInfo.attach('layout-measurements', {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json',
  });
});

test('presenter keeps audience and previews synchronized, saves notes, and recovers a closed window', async ({
  page,
}, testInfo) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/presentation?slide=11');
  const frame = deck(page);
  let audience: import('@playwright/test').Page;
  [audience] = await Promise.all([
    page.waitForEvent('popup'),
    frame.locator('#ppt-presenter-btn').click(),
  ]);
  await expect(frame.locator('#ppt-sync')).toContainText('已同步');
  await expect(frame.locator('#ppt-auto-toggle')).toContainText('关闭');
  await expect(frame.locator('#ppt-clock')).toHaveText('00:00');
  await frame
    .getByRole('textbox', { name: '本页演讲备注' })
    .fill('这页先解释冻结规则，再讨论留出退化。');
  await expect(frame.locator('#ppt-saved')).toHaveText('已保存');
  const before = await frame.locator('#ppt-current-frame').getAttribute('src');
  await frame.locator('#ppt-next').click();
  await expect(audience.locator('#deck>.slide:not([inert]) h1')).toHaveText('共同拥挤');
  expect(await frame.locator('#ppt-current-frame').getAttribute('src')).toBe(before);
  await frame.locator('#ppt-prev').click();
  await expect(frame.getByRole('textbox', { name: '本页演讲备注' })).toHaveValue(
    '这页先解释冻结规则，再讨论留出退化。',
  );
  await frame.locator('#ppt-grid').click();
  await expect(frame.locator('.ppt-overview-page')).toHaveCount(14);
  await frame.locator('.ppt-overview-page').nth(4).click();
  await expect(frame.locator('#ppt-presenter-overview')).toBeHidden();
  await frame.locator('#ppt-first').click();
  await frame.locator('#ppt-timer-toggle').click();
  await expect(frame.locator('#ppt-clock')).not.toHaveText('00:00', { timeout: 3000 });
  await frame.locator('#ppt-timer-toggle').click();
  await frame.locator('#ppt-timer-reset').click();
  await expect(frame.locator('#ppt-clock')).toHaveText('00:00');
  await frame.locator('#ppt-rehearsal').click();
  await frame.locator('#ppt-next').click();
  await frame.locator('#ppt-rehearsal').click();
  await expect(frame.locator('#ppt-dialog-title')).toContainText('排练');
  await frame.locator('#ppt-dialog-close').click();
  await frame.locator('#ppt-settings').click();
  await frame.locator('[data-screen-choice=black]').click();
  await expect(audience.locator('#ppt-audience-cover')).toBeVisible();
  await frame.locator('[data-screen-choice=white]').click();
  await frame.locator('[data-screen-choice=frozen]').click();
  await frame.locator('#ppt-dialog-close').click();
  const frozen = await audience.locator('#deck>.slide:not([inert]) h1').textContent();
  await frame.locator('#ppt-next').click();
  await expect(audience.locator('#deck>.slide:not([inert]) h1')).toHaveText(frozen!);
  await frame.locator('#ppt-settings').click();
  await frame.locator('[data-screen-choice=normal]').click();
  await frame.locator('#ppt-dialog-close').click();
  await expect(frame.locator('#ppt-sync')).toContainText('已同步');
  await frame.locator('[data-ppt-tool=laser]').click();
  await frame.locator('[data-ppt-tool=circle]').click();
  const ink = await frame.locator('#ppt-presenter-ink').boundingBox();
  await page.mouse.move(ink!.x + 50, ink!.y + 50);
  await page.mouse.down();
  await page.mouse.move(ink!.x + 150, ink!.y + 130);
  await page.mouse.up();
  await expect
    .poll(() =>
      audience
        .locator('body')
        .evaluate(() => Reflect.get(window, '__pptPresenter').debugState().audienceCircles.length),
    )
    .toBe(1);
  await frame.locator('#ppt-ink-clear').click();
  await expect
    .poll(() =>
      audience
        .locator('body')
        .evaluate(() => Reflect.get(window, '__pptPresenter').debugState().audienceCircles.length),
    )
    .toBe(0);
  await frame.locator('#ppt-preflight').click();
  await expect(frame.locator('#ppt-dialog-title')).toHaveText('演前检查');
  await frame.locator('#ppt-dialog-close').click();
  await frame.locator('[data-ppt-tool=circle]').click();
  await frame.locator('#ppt-settings').click();
  await frame.locator('#ppt-auto-seconds-setting').fill('2');
  await frame.locator('#ppt-settings-save').click();
  await expect(frame.locator('#ppt-dialog')).toBeHidden();
  await frame.locator('#ppt-auto-toggle').click();
  await frame.locator('#ppt-grid').click();
  const beforeAuto = await frame.locator('#ppt-page-count').textContent();
  await page.waitForTimeout(2100);
  await expect(frame.locator('#ppt-page-count')).toHaveText(beforeAuto!);
  await frame.locator('#ppt-overview-close').click();
  await expect(frame.locator('#ppt-page-count')).not.toHaveText(beforeAuto!, { timeout: 5000 });
  await frame.locator('#ppt-auto-toggle').click();
  await frame.locator('#ppt-last').click();
  await expect(frame.locator('#ppt-next-card')).toHaveClass(/is-end/);
  await frame.locator('#ppt-last').click();
  await expect(frame.locator('#ppt-page-count')).toContainText('1 / 14');
  for (const size of [
    { width: 1440, height: 950 },
    { width: 1000, height: 750 },
  ]) {
    await page.setViewportSize(size);
    await expect
      .poll(async () => {
        const box = await frame.locator('#ppt-current-frame').boundingBox();
        return box ? Math.abs(box.width / box.height - 16 / 9) : 1;
      })
      .toBeLessThan(0.01);
    const next = await frame.locator('#ppt-next-frame').boundingBox();
    expect(Math.abs(next!.width / next!.height - 16 / 9)).toBeLessThan(0.01);
    for (const selector of ['#ppt-current-frame', '#ppt-next-frame']) {
      const preview = frame.frameLocator(selector);
      await expect.poll(() => preview.locator('body').evaluate(() => innerWidth)).toBe(1440);
      await expect(preview.locator('#deck>.slide:not([inert]) .foot')).toBeInViewport();
      await expect(preview.locator('#deck>.slide:not([inert]) .frame-img')).toBeInViewport();
    }
  }
  await page.screenshot({ path: testInfo.outputPath('style-a-presenter.png') });
  await audience.close();
  await expect(frame.locator('#ppt-sync')).toContainText('未连接');
  [audience] = await Promise.all([
    page.waitForEvent('popup'),
    frame.locator('#ppt-reopen').click(),
  ]);
  await expect(frame.locator('#ppt-sync')).toContainText('已同步');
  await frame.locator('#ppt-exit').click();
  await expect.poll(() => audience.isClosed()).toBe(true);
  await frame.locator('body').evaluate(() => {
    Reflect.set(window, '__originalOpen', window.open);
    window.open = () => null;
  });
  await frame.locator('#ppt-presenter-btn').click();
  await expect(frame.locator('#ppt-sync')).toContainText('弹窗被拦截');
  await frame.locator('#ppt-exit').click();
  await frame.locator('body').evaluate(() => {
    window.open = Reflect.get(window, '__originalOpen');
  });
  [audience] = await Promise.all([
    page.waitForEvent('popup'),
    frame.locator('#ppt-presenter-btn').click(),
  ]);
  await expect(frame.locator('#ppt-sync')).toContainText('已同步');
  await page.getByRole('link', { name: '现场实验' }).click();
  await expect(page).toHaveURL(/\/mine$/);
  await expect.poll(() => audience.isClosed()).toBe(true);
  expect(errors).toEqual([]);
});
