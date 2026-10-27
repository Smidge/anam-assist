import { createClient, AnamEvent } from '@anam-ai/js-sdk';

class AnamAssistPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.phase = 'idle';
    this.generation = 0;
    this.onPageHide = () => void this.stop();
    this.onOffline = () => void this.stop('Connection lost. Start a new conversation.');
  }
  set hass(value) {
    if (this._hass && value.connection !== this._hass.connection && this.phase !== 'idle') void this.stop('Home Assistant reconnected. Start a new conversation.');
    this._hass = value;
    if (this.isConnected && !this.initialized) this.init();
  }
  connectedCallback() {
    window.addEventListener('pagehide', this.onPageHide);
    window.addEventListener('offline', this.onOffline);
    if (this._hass && !this.initialized) this.init();
  }
  disconnectedCallback() {
    window.removeEventListener('pagehide', this.onPageHide);
    window.removeEventListener('offline', this.onOffline);
    void this.stop();
  }
  $(selector) { return this.shadowRoot.querySelector(selector); }
  async init() {
    this.initialized = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;height:100%;overflow:auto;color:var(--primary-text-color,#202124);background:var(--primary-background-color,#fafafa);font-family:var(--paper-font-body1_-_font-family,system-ui)}
        *{box-sizing:border-box}section,aside{min-width:0}button,summary,a{touch-action:manipulation}.skip{position:absolute;z-index:2;inset-inline-start:16px;top:0;padding:12px;background:var(--card-background-color,#fff);color:inherit;transform:translateY(-120%)}.skip:focus{transform:none}header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;padding:20px 28px;border-bottom:1px solid var(--divider-color,#ddd)}
        .title{display:flex;align-items:center;gap:12px}h1{font-size:22px;font-weight:500;margin:0}h2{font-size:18px;font-weight:500;margin:0 0 16px}p{line-height:1.6;margin:0 0 16px}.muted{color:var(--secondary-text-color,#62666b)}
        main{max-width:1200px;margin:auto;padding:28px;display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:32px}
        .stage{aspect-ratio:2/3;max-width:480px;margin-inline:auto;position:relative;background:#171b20;border-radius:12px;overflow:hidden;display:grid;place-items:center}video{width:100%;height:100%;object-fit:contain;position:absolute;inset:0}
        .placeholder{position:relative;color:#d8dee6;text-align:center;max-width:310px;padding:24px}.placeholder p{color:#b6bec8}.placeholder h2{font-size:26px}
        .controls{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}button,input,select{font:inherit}button{min-height:44px;border:1px solid var(--divider-color,#c6c9cc);border-radius:8px;padding:10px 16px;background:var(--card-background-color,#fff);color:inherit;cursor:pointer}
        button.primary{background:var(--primary-color,#007fad);color:var(--text-primary-color,#fff);border-color:transparent}button:disabled{opacity:.5;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid var(--primary-color,#007fad);outline-offset:3px}
        select,input[type=text]{width:100%;min-height:44px;padding:10px;border:1px solid var(--divider-color,#aaa);border-radius:8px;background:var(--card-background-color,#fff);color:inherit}label{display:block;margin:0 0 8px}.check{display:flex;align-items:center;gap:10px;min-height:44px;margin:12px 0}.check input{width:20px;height:20px}
        .settings{padding-bottom:24px;border-bottom:1px solid var(--divider-color,#ddd);margin-bottom:24px}.composer{display:flex;gap:8px}.composer input{min-width:0}.error{color:var(--error-color,#b71c1c);margin:12px 0;overflow-wrap:anywhere}.log{list-style:none;padding:0;margin:0}.log li{padding:12px 0;border-bottom:1px solid var(--divider-color,#ddd);line-height:1.5;overflow-wrap:anywhere}.log small{display:block;color:var(--secondary-text-color,#62666b)}
        details{margin-top:24px}summary{cursor:pointer;min-height:44px;padding:12px 0}.transcript p{padding:8px 0;margin:0;overflow-wrap:anywhere}.status{font-size:14px;color:var(--secondary-text-color,#62666b)}[hidden]{display:none!important}
        @media(max-width:760px){header{padding:16px}main{padding:16px;grid-template-columns:1fr;gap:24px}.stage{aspect-ratio:2/3}.controls button{flex:1}.composer button{padding:10px}.settings{padding-bottom:16px}}
        @media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
      </style>
      <a class="skip" href="#conversation">Skip to conversation</a><header><div class="title"><button id="menu" aria-label="Open Home Assistant menu">Menu</button><h1>Anam Assist</h1></div><span class="status" role="status">Ready to connect</span></header>
      <main><section id="conversation" tabindex="-1" aria-label="Conversation">
        <div class="stage"><video autoplay playsinline aria-label="Anam avatar"></video><div class="placeholder"><h2>A face for your home</h2><p>Start a conversation, then speak or type a request.</p></div></div>
        <div class="controls"><button class="primary" id="start">Start conversation</button><button id="end" disabled>End</button><button id="mute" disabled aria-pressed="false">Mute microphone</button><button id="interrupt" disabled>Stop speaking</button><button id="play" hidden>Play audio</button></div>
        <p class="error" role="alert" hidden></p>
        <form class="composer"><label for="message" hidden>Message</label><input id="message" name="message" type="text" aria-label="Message" placeholder="Ask about your home…" maxlength="2000" autocomplete="off" disabled><button id="send" type="submit" disabled>Send</button></form>
        <details><summary>Conversation transcript</summary><div class="transcript"></div></details>
      </section><aside>
        <section class="settings"><h2>This conversation</h2><label for="room">Screen location</label><select id="room" name="room"><option value="">Ask which room</option></select>
          <label class="check"><input id="microphone" name="microphone" type="checkbox" checked>Use microphone</label>
          <label for="control">Home controls</label><select id="control" name="control" aria-describedby="scope"><option value="read_only">Read-only</option><option value="lights">Lights only</option><option value="assist">Assist controls</option></select>
          <p class="muted" id="scope" aria-live="polite">Read exposed entity states without changing devices.</p>
          <p class="muted">Audio, typed messages and Assist context go to Anam. Context tools can return all exposed entity states. Recording and stored transcripts are off. Sessions end after 10 minutes or when you leave this page.</p>
        </section>
        <section><h2>Home activity</h2><p class="muted" id="empty">Tool calls and their results will appear here.</p><ol class="log" aria-live="polite" aria-label="Home activity"></ol></section>
      </aside></main>`;
    this.$('.skip').onclick = event => { event.preventDefault(); this.$('#conversation').focus(); };
    this.$('#menu').onclick = () => this.dispatchEvent(new Event('hass-toggle-menu', { bubbles: true, composed: true }));
    this.$('#control').onchange = () => {
      this.$('#scope').textContent = {
        read_only: 'Read exposed entity states without changing devices.',
        lights: 'Control exposed lights, including brightness.',
        assist: 'Allow all tools supplied by Home Assistant’s Assist device-control API. Depending on your setup, this can operate locks, covers, heating and exposed scripts or scenes. Review Assist exposure first. Actions run without a separate confirmation.'
      }[this.$('#control').value];
    };
    this.$('#start').onclick = () => void this.start();
    this.$('#end').onclick = () => void this.stop();
    this.$('#interrupt').onclick = () => void this.clientAction('interruptPersona');
    this.$('#mute').onclick = async () => {
      const generation = this.generation;
      const muted = !this.muted;
      if (!await this.clientAction(muted ? 'muteInputAudio' : 'unmuteInputAudio') || generation !== this.generation) return;
      this.muted = muted;
      this.$('#mute').textContent = this.muted ? 'Unmute microphone' : 'Mute microphone';
      this.$('#mute').setAttribute('aria-pressed', String(this.muted));
    };
    this.$('#play').onclick = async () => {
      const generation = this.generation;
      try { await this.$('video').play(); if (generation === this.generation) this.$('#play').hidden = true; }
      catch { if (generation === this.generation) this.error('Your browser blocked playback. Check its sound permissions.'); }
    };
    this.$('form').onsubmit = event => {
      event.preventDefault();
      const input = this.$('#message');
      if (!input.value.trim() || this.phase !== 'connected') return;
      try { this.client.sendUserMessage(input.value.trim()); input.value = ''; }
      catch { this.error('The message could not be sent. End this session and reconnect.'); }
    };
    try {
      const info = await this._hass.callWS({ type: 'anam_assist/info' });
      for (const area of info.areas.sort((a, b) => a.name.localeCompare(b.name))) {
        this.$('#room').add(new Option(area.name, area.id));
      }
    } catch { this.error('Could not load Home Assistant. Refresh the page and sign in again.'); }
  }
  async clientAction(method) {
    const generation = this.generation;
    try {
      if (this.phase !== 'connected' || !this.client) return false;
      await this.client[method]();
      return true;
    } catch {
      if (generation === this.generation) this.error('The audio control failed. End this session and reconnect.');
      return false;
    }
  }
  error(message) {
    this.$('.error').textContent = message;
    this.$('.error').hidden = !message;
  }
  state(phase, label) {
    this.phase = phase;
    this.$('.status').textContent = label;
    this.$('#start').disabled = phase !== 'idle';
    this.$('#end').disabled = phase === 'idle' || phase === 'stopping';
    for (const id of ['#room', '#microphone', '#control']) this.$(id).disabled = phase !== 'idle';
    for (const id of ['#message', '#send', '#interrupt']) this.$(id).disabled = phase !== 'connected';
    this.$('#mute').disabled = phase !== 'connected' || !this.$('#microphone').checked;
  }
  activity(name, detail) {
    this.$('#empty').hidden = true;
    const item = document.createElement('li');
    item.textContent = name;
    const small = document.createElement('small');
    small.textContent = detail;
    item.append(small);
    this.$('.log').prepend(item);
    while (this.$('.log').children.length > 20) this.$('.log').lastChild.remove();
  }
  async start() {
    if (this.phase !== 'idle') return;
    if (!window.isSecureContext) { this.error('Open Home Assistant over HTTPS to use the microphone.'); return; }
    const generation = ++this.generation;
    const hass = this._hass;
    const connection = hass.connection;
    const disconnected = () => { if (generation === this.generation) void this.stop('Home Assistant disconnected. Start a new conversation.'); };
    connection?.addEventListener?.('disconnected', disconnected);
    this.removeConnectionListener = () => connection?.removeEventListener?.('disconnected', disconnected);
    this.sessionHass = hass;
    this.error('');
    this.state('connecting', 'Connecting…');
    this.$('.transcript').replaceChildren();
    this.$('.log').replaceChildren();
    this.$('#empty').hidden = false;
    let client;
    let bridge;
    try {
      if (this.$('#microphone').checked) {
        const mic = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false });
        if (generation !== this.generation) { mic.getTracks().forEach(t => t.stop()); return; }
        this.mic = mic;
      }
      bridge = await hass.callWS({ type: 'anam_assist/start', control_mode: this.$('#control').value, area_id: this.$('#room').value });
      if (generation !== this.generation) {
        void Promise.resolve().then(() => hass.callWS({ type: 'anam_assist/stop', bridge_id: bridge.bridge_id })).catch(() => {}); return;
      }
      this.bridge = bridge;
      this.sessionTimer = setTimeout(() => void this.stop('10-minute session ended'), bridge.expires_in * 1000);
      client = createClient(bridge.session_token, { disableInputAudio: !this.$('#microphone').checked });
      this.client = client;
      const toolLabel = name => bridge.tool_labels?.[name] || 'Home Assistant tool';
      client.addListener(AnamEvent.TOOL_CALL_STARTED, payload => {
        if (generation === this.generation) this.activity(toolLabel(payload.toolName), 'Requested by Anam');
      });
      client.addListener(AnamEvent.TOOL_CALL_FAILED, payload => {
        if (generation === this.generation) this.activity(toolLabel(payload.toolName), payload.errorMessage || 'Anam tool call failed');
      });
      for (const name of bridge.tools) client.registerToolCallHandler(name, {
        onStart: async payload => {
          if (generation !== this.generation) throw new Error('Conversation ended');
          const started = performance.now();
          this.activity(toolLabel(name), 'Running…');
          try {
            const result = await hass.callWS({ type: 'anam_assist/tool', bridge_id: bridge.bridge_id, call_id: payload.toolCallId, name, arguments: payload.arguments });
            if (generation !== this.generation) throw new Error('Conversation ended');
            this.activity(toolLabel(name), `${result.error ? 'Failed' : 'Completed'} · ${Math.round(performance.now() - started)} ms`);
            return JSON.stringify(result);
          } catch (error) {
            if (generation === this.generation) this.activity(toolLabel(name), 'Failed to contact Home Assistant');
            throw new Error(error.message || 'Home Assistant tool failed');
          }
        }
      });
      client.addListener(AnamEvent.MESSAGE_HISTORY_UPDATED, messages => {
        if (generation !== this.generation) return;
        this.$('.transcript').replaceChildren(...messages.slice(-30).map(message => {
          const p = document.createElement('p');
          p.textContent = `${message.role === 'user' ? 'You' : 'Home'}: ${message.content}`;
          return p;
        }));
      });
      client.addListener(AnamEvent.CONNECTION_CLOSED, () => {
        if (generation === this.generation) void this.stop('Connection ended');
      });
      let connectTimer;
      const timeout = new Promise((_, reject) => { connectTimer = setTimeout(() => reject(new Error('Anam connection timed out. Try again.')), 45000); });
      const streamPromise = client.stream(this.mic).then(streams => {
        if (generation !== this.generation) {
          streams.flatMap(stream => stream.getTracks()).forEach(track => track.stop());
          void Promise.resolve().then(() => client.stopStreaming()).catch(() => {});
        }
        return streams;
      });
      let streams;
      try { streams = await Promise.race([streamPromise, timeout]); }
      finally { clearTimeout(connectTimer); }
      if (generation !== this.generation) return;
      const tracks = [...new Map(streams.flatMap(s => s.getTracks()).map(t => [t.id, t])).values()];
      this.$('video').srcObject = new MediaStream(tracks);
      this.$('.placeholder').hidden = true;
      try { await this.$('video').play(); } catch { if (generation === this.generation) this.$('#play').hidden = false; }
      if (generation !== this.generation) return;
      this.muted = false;
      this.$('#mute').textContent = 'Mute microphone';
      this.$('#mute').setAttribute('aria-pressed', 'false');
      this.state('connected', { read_only: 'Connected · read-only', lights: 'Connected · lights only', assist: 'Connected · Assist controls' }[this.$('#control').value]);
      this.activity('Conversation', 'Connected');
    } catch (error) {
      if (generation !== this.generation) return;
      const stopping = this.stop();
      const stoppedGeneration = this.generation;
      await stopping;
      if (stoppedGeneration !== this.generation) return;
      this.error(error.name === 'NotAllowedError' ? 'Microphone access was denied. Allow it in browser settings, or untick Use microphone and type instead.' : (error.message || 'Could not start Anam. Check your integration settings.'));
    }
  }
  async stop(label = 'Ready to connect') {
    const generation = ++this.generation;
    clearTimeout(this.sessionTimer);
    this.removeConnectionListener?.();
    this.removeConnectionListener = null;
    const client = this.client;
    const bridge = this.bridge;
    const hass = this.sessionHass;
    this.sessionHass = null;
    this.client = null;
    this.bridge = null;
    this.mic?.getTracks().forEach(track => track.stop());
    this.mic = null;
    if (!this.initialized) return;
    this.state('stopping', 'Ending…');
    this.$('video').srcObject?.getTracks().forEach(track => track.stop());
    this.$('video').srcObject = null;
    this.$('.placeholder').hidden = false;
    this.$('#play').hidden = true;
    let cleanupTimer;
    await Promise.race([
      Promise.allSettled([
        Promise.resolve().then(() => client?.stopStreaming()),
        bridge ? Promise.resolve().then(() => hass.callWS({ type: 'anam_assist/stop', bridge_id: bridge.bridge_id })) : undefined,
      ]),
      new Promise(resolve => { cleanupTimer = setTimeout(resolve, 3000); }),
    ]);
    clearTimeout(cleanupTimer);
    if (generation === this.generation) this.state('idle', label);
  }
}
if (!customElements.get('anam-assist-panel')) customElements.define('anam-assist-panel', AnamAssistPanel);
