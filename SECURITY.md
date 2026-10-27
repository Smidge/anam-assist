# Security model and release gates

Anam Assist is an unofficial integration. This experimental preview has not had an independent
security audit and is not a stable release.

## Boundaries

- Home Assistant authenticates every WebSocket command. All four commands require
  an administrator. The sidebar flag alone is not an authorization check.
- The Anam API key remains on the HA server, in the config entry and HA backups.
  Reconfiguration never sends the saved key back as a form default. Outbound API
  requests use a fixed HTTPS origin, certificate validation and no redirects.
- The browser receives a short-lived Anam session token. Browser extensions and
  scripts with access to the HA origin can access the session. This integration
  cannot isolate itself from a compromised HA installation or administrator.
- Bridge IDs are random, connection-bound and expire after ten minutes. They
  grant only the tools selected at session creation. Tool names use stable opaque
  identifiers; HA names remain server-side. Unknown IDs fail closed.
- Control is opt-in per session and limited to exposed lights. Scenes, switches,
  scripts, locks, covers and climate control are excluded. Existing automations
  triggered by a light change can still have other effects.
- Exposure and tool availability are resolved using the Assist API at execution
  time. Sessions are checked again after asynchronous lookups. Ending a session
  prevents queued work from executing; actions already dispatched cannot be undone.
- Call IDs are bound to their arguments and cached before execution. An uncertain
  outcome is not retried automatically. Limits bound arguments, calls, concurrent
  sessions, lock waits and outbound request duration.

## Data disclosure

Anam receives microphone audio or typed messages, the selected persona, Assist's
prompt context and tool results. Live-context tools may return all exposed entity
states, not just the single value requested. Review Assist exposure before use.
Recording and stored transcripts are disabled in session options; this is not a
promise of zero provider retention. Browser transcripts remain in page memory.

Treat model output, device names and tool arguments as untrusted. Prompt
instructions are behavioural guidance, not an authorization boundary. The server
must enforce permissions regardless of what the model says.

## Verification and remaining release checks

Automated tests cover argument and response bounds, replay protection, connection
ownership, cancellation, real Home Assistant config-flow results and exposure
filtering. A synthetic light service verifies that the real light intent rejects
hidden entities and accepts exposed lights. Chromium and WebKit tests cover late
media, reconnects, denied microphone access, playback failure and session expiry.
These tests do not establish physical device behavior or full network transport.

Before a stable release:

- Exercise a clean install, reload, upgrade and removal through a real Home
  Assistant instance, including HTTP/WebSocket authentication.
- Verify a real light action and its physical result with the owner.
- Check microphone/audio behavior on physical mobile browsers.
- Complete HACS validation and compatibility testing beyond Home Assistant
  2026.10.3. No wider version support is claimed.
- Obtain an independent security review before making any audit claim.

## Reporting a vulnerability

Use [private vulnerability reporting](https://github.com/Smidge/anam-assist/security/advisories/new).
Do not file a public issue with exploit details or credentials. Include affected
versions, expected and observed behavior, and a minimal synthetic reproduction.
There is no guaranteed response time or paid support commitment.

Do not include API keys, HA backups, transcripts or home-state payloads in public
issues. If a key was exposed, revoke it with Anam and reconfigure the integration.
