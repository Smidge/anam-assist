function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
window.fixture = {
  deferred, clients: [], calls: [], messages: [], streams: [],
  stream: deferred(), start: null, tool: null, microphone: null,
  cleanup: () => Promise.resolve(), play: () => Promise.resolve(),
  makeStream() {
    const canvas = document.createElement('canvas');
    const stream = canvas.captureStream();
    this.streams.push(stream);
    return stream;
  },
};
HTMLMediaElement.prototype.play = function () { return window.fixture.play(); };
Object.defineProperty(MediaDevices.prototype, 'getUserMedia', {
  value: () => fixture.microphone?.promise || Promise.resolve(fixture.makeStream()),
});
const listeners = new Map();
fixture.connection = {
  addEventListener(name, callback) { listeners.set(callback, name); },
  removeEventListener(name, callback) { listeners.delete(callback); },
};
fixture.disconnect = () => [...listeners].forEach(([callback]) => callback());
fixture.listenerCount = () => listeners.size;
fixture.hass = {
  connection: fixture.connection,
  callWS(message) {
    fixture.calls.push(message);
    switch (message.type) {
      case 'anam_assist/info': return Promise.resolve({ areas: [{ name: 'Living room', id: 'living' }] });
      case 'anam_assist/start': return fixture.start?.promise || Promise.resolve({ bridge_id: 'bridge', session_token: 'fake', tools: ['ha_read'], tool_labels: { ha_read: 'Read home state' }, expires_in: 600 });
      case 'anam_assist/tool': return fixture.tool?.promise || Promise.resolve({ error: null, data: { temperature: 20 } });
      case 'anam_assist/stop': return Promise.resolve();
    }
  },
};
fixture.panel = document.createElement('anam-assist-panel');
document.body.append(fixture.panel);
fixture.panel.hass = fixture.hass;
