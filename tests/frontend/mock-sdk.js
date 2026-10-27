export const AnamEvent = {
  TOOL_CALL_STARTED: 'tool-started', TOOL_CALL_FAILED: 'tool-failed',
  MESSAGE_HISTORY_UPDATED: 'messages', CONNECTION_CLOSED: 'closed',
};
export function createClient() {
  const client = {
    handlers: {}, listeners: {}, stopped: 0,
    registerToolCallHandler(name, handler) { this.handlers[name] = handler; },
    addListener(name, callback) { this.listeners[name] = callback; },
    stream() { return window.fixture.stream.promise; },
    stopStreaming() { this.stopped++; return window.fixture.cleanup(); },
    sendUserMessage(message) { window.fixture.messages.push(message); },
    interruptPersona() {}, muteInputAudio() {}, unmuteInputAudio() {},
  };
  window.fixture.clients.push(client);
  return client;
}
