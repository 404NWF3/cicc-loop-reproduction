/* Website integration for the Style A template. AGPL-3.0. */
(() => {
  const embedded = parent !== window && !document.body.classList.contains('ppt-preview');
  const send = (message) => {
    if (embedded) parent.postMessage({ type: 'research-deck', ...message }, location.origin);
  };
  const emitSlide = () => {
    const index = window.__currentSlideIndex || 0;
    send({ action: 'slide', index });
    const number = document.querySelector('#research-controls output');
    if (number) number.textContent = `${String(index + 1).padStart(2, '0')} / ${slides.length}`;
    document.getElementById('research-prev').disabled = index === 0;
    document.getElementById('research-next').disabled = index === slides.length - 1;
    const query = new URL(location.href);
    query.searchParams.set('slide', String(index + 1));
    history.replaceState(null, '', query);
    slides[index].scrollTop = 0;
  };
  document.body.insertAdjacentHTML(
    'beforeend',
    `<nav id='research-controls' aria-label='演示翻页'><button id='research-prev' aria-label='上一页'>←</button><output aria-live='polite'></output><button id='research-next' aria-label='下一页'>→</button></nav>`,
  );
  document.getElementById('research-prev').onclick = () => go(idx - 1, { force: true });
  document.getElementById('research-next').onclick = () => go(idx + 1, { force: true });
  if (new URLSearchParams(location.search).get('capture') === '1')
    document.body.classList.add('research-capture');
  addEventListener('research-slide-change', emitSlide);
  addEventListener('pagehide', () => {
    if (window.__pptPresenter.debugState().mode === 'presenter')
      document.getElementById('ppt-exit')?.click();
  });
  addEventListener('message', (event) => {
    if (
      event.origin !== location.origin ||
      event.source !== parent ||
      event.data?.type !== 'research-control'
    )
      return;
    if (event.data.action === 'goto' && Number.isInteger(event.data.index))
      go(event.data.index, { force: true });
    if (event.data.action === 'overview') toggleOverview();
    if (event.data.action === 'presenter') window.__pptPresenter.enterPresenter(true);
  });
  addEventListener('keydown', (event) => {
    if (
      window.__pptPresenter.debugState().mode !== 'deck' ||
      event.ctrlKey ||
      event.metaKey ||
      event.altKey ||
      event.target.closest('input,textarea,select,[contenteditable]')
    )
      return;
    if (event.key.toLowerCase() === 'n') send({ action: 'notes' });
    if (event.key.toLowerCase() === 'f') send({ action: 'fullscreen' });
  });
  // Notify the containing route without reloading this document on every slide.
  emitSlide();
  send({ action: 'ready', index: idx });
})();
