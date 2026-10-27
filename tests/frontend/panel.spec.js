import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../../src/panel.js', import.meta.url), 'utf8');
const mock = await readFile(new URL('./mock-sdk.js', import.meta.url), 'utf8');
const fixture = await readFile(new URL('./fixture.js', import.meta.url), 'utf8');

test.beforeEach(async ({ page }) => {
  await page.route('http://localhost:4173/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path === '/panel.js') return route.fulfill({ contentType: 'text/javascript', body: source.replace("'@anam-ai/js-sdk'", "'/mock-sdk.js'") });
    if (path === '/mock-sdk.js') return route.fulfill({ contentType: 'text/javascript', body: mock });
    if (path === '/fixture.js') return route.fulfill({ contentType: 'text/javascript', body: fixture });
    return route.fulfill({ contentType: 'text/html', body: '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Panel test</title><style>body{margin:0;font:16px system-ui}anam-assist-panel{height:100vh}</style></head><body><script type="module">import "/panel.js"; await import("/fixture.js");</script></body></html>' });
  });
  await page.goto('http://localhost:4173/');
  await expect(page.getByRole('button', { name: 'Start conversation' })).toBeEnabled();
});

async function connect(page) {
  await page.getByRole('checkbox', { name: 'Use microphone' }).uncheck();
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect.poll(() => page.evaluate(() => fixture.clients.length)).toBe(1);
  await page.evaluate(() => fixture.stream.resolve([fixture.makeStream()]));
  await expect(page.getByRole('status')).toHaveText('Connected · read-only');
}

test('read-only by default, named activity, text messages and safe transcript rendering', async ({ page }) => {
  await expect(page.getByRole('checkbox', { name: 'Allow light control' })).not.toBeChecked();
  await connect(page);
  await page.getByRole('textbox', { name: 'Message' }).fill('Temperature?');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  expect(await page.evaluate(() => fixture.messages)).toEqual(['Temperature?']);
  const result = await page.evaluate(async () => {
    fixture.clients[0].listeners.messages([{ role: 'assistant', content: '<img src=x onerror=alert(1)>' }]);
    return fixture.clients[0].handlers.ha_read.onStart({ toolCallId: 'call', arguments: {} });
  });
  expect(JSON.parse(result).data.temperature).toBe(20);
  await expect(page.getByRole('list', { name: 'Home activity' })).toContainText('Read home state');
  expect(await page.locator('.transcript img').count()).toBe(0);
});

test('ending while microphone permission is pending stops the eventual track', async ({ page }) => {
  await page.evaluate(() => { fixture.microphone = fixture.deferred(); });
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await page.getByRole('button', { name: 'End', exact: true }).click();
  await page.evaluate(() => fixture.microphone.resolve(fixture.makeStream()));
  await expect.poll(() => page.evaluate(() => fixture.streams[0]?.getTracks()[0].readyState)).toBe('ended');
  expect(await page.evaluate(() => fixture.calls.filter(c => c.type === 'anam_assist/start').length)).toBe(0);
});

test('late bridge creation is revoked after ending', async ({ page }) => {
  await page.evaluate(() => { fixture.start = fixture.deferred(); });
  await page.getByRole('checkbox', { name: 'Use microphone' }).uncheck();
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await page.getByRole('button', { name: 'End', exact: true }).click();
  await page.evaluate(() => fixture.start.resolve({ bridge_id: 'late' }));
  await expect.poll(() => page.evaluate(() => fixture.calls.some(c => c.type === 'anam_assist/stop' && c.bridge_id === 'late'))).toBe(true);
  expect(await page.evaluate(() => fixture.clients.length)).toBe(0);
});

test('stream arriving after connection timeout has its tracks stopped', async ({ page }) => {
  await page.clock.install();
  await page.getByRole('checkbox', { name: 'Use microphone' }).uncheck();
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect.poll(() => page.evaluate(() => fixture.clients.length)).toBe(1);
  await page.clock.fastForward(46000);
  await expect(page.getByRole('alert')).toContainText('timed out');
  await page.evaluate(() => fixture.stream.resolve([fixture.makeStream()]));
  await expect.poll(() => page.evaluate(() => fixture.streams[0].getTracks()[0].readyState)).toBe('ended');
});

for (const cause of ['offline', 'disconnect', 'remove', 'pagehide']) {
  test(`${cause} releases media and revokes bridge`, async ({ page }) => {
    await connect(page);
    await page.evaluate(cause => {
      if (cause === 'disconnect') fixture.disconnect();
      else if (cause === 'remove') fixture.panel.remove();
      else window.dispatchEvent(new Event(cause));
    }, cause);
    await expect.poll(() => page.evaluate(() => fixture.streams[0].getTracks()[0].readyState)).toBe('ended');
    await expect.poll(() => page.evaluate(() => fixture.calls.some(c => c.type === 'anam_assist/stop'))).toBe(true);
    expect(await page.evaluate(() => fixture.listenerCount())).toBe(0);
  });
}

test('pending tool results cannot populate a later conversation', async ({ page }) => {
  await connect(page);
  await page.evaluate(() => {
    fixture.tool = fixture.deferred();
    fixture.toolResult = fixture.clients[0].handlers.ha_read.onStart({ toolCallId: 'call', arguments: {} }).catch(e => e.message);
  });
  await page.getByRole('button', { name: 'End', exact: true }).click();
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect(page.getByRole('status')).toHaveText('Connected · read-only');
  await page.evaluate(() => fixture.tool.resolve({ error: null, data: {} }));
  expect(await page.evaluate(() => fixture.toolResult)).toBe('Conversation ended');
  await expect(page.getByRole('list', { name: 'Home activity' })).not.toContainText('Completed');
});

test('blocked playback offers a working explicit play control', async ({ page }) => {
  await page.evaluate(() => { fixture.play = () => Promise.reject(new Error('blocked')); });
  await connect(page);
  await expect(page.getByRole('button', { name: 'Play audio' })).toBeVisible();
  await page.evaluate(() => { fixture.play = () => Promise.resolve(); });
  await page.getByRole('button', { name: 'Play audio' }).click();
  await expect(page.getByRole('button', { name: 'Play audio' })).toBeHidden();
});

test('synchronous cleanup failure does not leave controls stuck', async ({ page }) => {
  await connect(page);
  await page.evaluate(() => { fixture.cleanup = () => { throw new Error('closed'); }; });
  await page.getByRole('button', { name: 'End', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Start conversation' })).toBeEnabled();
});

test('hanging cleanup is bounded and releases tracks immediately', async ({ page }) => {
  await connect(page);
  await page.clock.install();
  await page.evaluate(() => { fixture.cleanup = () => new Promise(() => {}); });
  await page.getByRole('button', { name: 'End', exact: true }).click();
  expect(await page.evaluate(() => fixture.streams[0].getTracks()[0].readyState)).toBe('ended');
  await page.clock.fastForward(3100);
  await expect(page.getByRole('button', { name: 'Start conversation' })).toBeEnabled();
});

test('permission denial offers typed fallback and permits retry', async ({ page }) => {
  await page.evaluate(() => {
    fixture.microphone = fixture.deferred();
    fixture.microphone.reject(new DOMException('Denied', 'NotAllowedError'));
    fixture.microphone.promise.catch(() => {});
  });
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect(page.getByRole('alert')).toContainText('Microphone access was denied');
  await connect(page);
});

test('portrait layout fits mobile, keyboard navigation and reduced motion', async ({ page, browserName }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const stage = await page.locator('.stage').boundingBox();
  expect(stage.width / stage.height).toBeCloseTo(2 / 3, 2);
  expect(await page.evaluate(() => fixture.panel.scrollWidth <= fixture.panel.clientWidth)).toBe(true);
  await page.keyboard.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
  await expect(page.getByRole('link', { name: 'Skip to conversation' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('region', { name: 'Conversation', exact: true })).toBeFocused();
});

test('ending while playback is pending cannot revive the session', async ({ page }) => {
  await page.evaluate(() => {
    fixture.playback = fixture.deferred();
    fixture.play = () => fixture.playback.promise;
  });
  await page.getByRole('checkbox', { name: 'Use microphone' }).uncheck();
  await page.getByRole('button', { name: 'Start conversation' }).click();
  await expect.poll(() => page.evaluate(() => fixture.clients.length)).toBe(1);
  await page.evaluate(() => fixture.stream.resolve([fixture.makeStream()]));
  await page.getByRole('button', { name: 'End', exact: true }).click();
  await page.evaluate(() => fixture.playback.resolve());
  await expect(page.getByRole('status')).toHaveText('Ready to connect');
  expect(await page.evaluate(() => fixture.streams[0].getTracks()[0].readyState)).toBe('ended');
});

test('session expiry releases media without waiting for user action', async ({ page }) => {
  await page.clock.install();
  await connect(page);
  await page.clock.fastForward(600001);
  await expect(page.getByRole('status')).toHaveText('10-minute session ended');
  expect(await page.evaluate(() => fixture.streams[0].getTracks()[0].readyState)).toBe('ended');
});

test('ended SDK cannot execute a queued tool call', async ({ page }) => {
  await connect(page);
  await page.getByRole('button', { name: 'End', exact: true }).click();
  const result = await page.evaluate(async () => {
    try { await fixture.clients[0].handlers.ha_read.onStart({ toolCallId: 'late', arguments: {} }); }
    catch (error) { return error.message; }
  });
  expect(result).toBe('Conversation ended');
  expect(await page.evaluate(() => fixture.calls.some(c => c.type === 'anam_assist/tool'))).toBe(false);
});

test('replacing HA connection revokes through the original connection', async ({ page }) => {
  await connect(page);
  await page.evaluate(() => {
    fixture.newCalls = [];
    fixture.panel.hass = { connection: {}, callWS: message => { fixture.newCalls.push(message); return Promise.resolve(); } };
  });
  await expect(page.getByRole('status')).toHaveText('Home Assistant reconnected. Start a new conversation.');
  expect(await page.evaluate(() => fixture.calls.some(c => c.type === 'anam_assist/stop'))).toBe(true);
  expect(await page.evaluate(() => fixture.newCalls.length)).toBe(0);
});
