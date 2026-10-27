# Anam Assist

An unofficial Home Assistant integration with a talking Anam avatar in your browser.
[Setup guide and architecture →](https://smidge.github.io/anam-assist/)

Anam handles speech, conversation and video. Home Assistant runs the selected scope
of Assist tools over the browser's authenticated connection.

**Experimental preview.** Tested against Home Assistant 2026.10.3. This is not an
official Anam or Home Assistant product, and has not had an independent security
audit. See [SECURITY.md](SECURITY.md) for verification and remaining release checks.

## Install

1. Back up your Home Assistant configuration.
2. Copy `custom_components/anam_assist` from this repository into your Home
   Assistant `custom_components` directory. The browser bundle is included.
3. Restart Home Assistant, then choose **Settings → Devices & services → Add
   integration → Anam Assist**.
4. Enter your Anam API key. Optionally enter a published persona ID; leaving it
   blank uses the public Cara example. Setup validates the credential without
   starting a media session.
5. Open **Anam Assist** in the sidebar using HTTPS and an administrator account.
   Start a session and ask a question about an entity exposed to Assist. You can
   disable the microphone and type instead.

The Anam account must have access to streaming sessions. Sessions consume Anam
usage. Your API key stays in Home Assistant, including its normal backups.
Never put it in dashboard YAML, browser code or a public issue.

Portrait is the default, requesting 768×1152 video. Use a portrait-capable Cara 4
avatar. For older avatars, select landscape through the integration's
**Reconfigure** action. Reconfigure also changes the persona or key; a blank key
keeps the existing credential. The integration copies the persona's avatar,
voice and model and supplies its own prompt and tools. It does not modify the
saved persona.

HACS metadata is included for custom-repository installation. This project is
not listed in HACS's default catalog; manual installation is the verified path.

## What it can do

- Query Assist-exposed entity state and live context.
- Choose a control scope before starting: **Read-only** (default), **Lights only**,
  or **Assist controls**.
- Assist controls supplies all tools offered by Home Assistant's built-in `assist`
  device-control API. Depending on installed integrations and exposed entities,
  this includes switches, fans, cover position, climate target temperature,
  media playback/volume, and exposed scenes or scripts. The exact actions are
  determined by Home Assistant; this is not a generic service-call API.
- Accept voice or typed messages, mute the microphone, stop speech and show a
  local transcript and tool activity.
- Use an optional room selection as conversation context.

**Assist controls can operate sensitive devices**, including locks and covers
when Home Assistant offers those tools. Actions execute without a separate
confirmation. Exposed scripts and scenes can affect devices beyond the entities
you exposed. Review Assist exposure and those scripts before selecting this mode.
Lights-only retains the original light restriction. Old clients cannot silently
upgrade to Assist controls. Home Assistant automations can have additional effects.

Try requests such as "set the study thermostat to 20 degrees", "pause the kitchen
speaker", or "set the bedroom blind to 50%" after exposing the relevant entities.
Music search/play requires a player that provides Home Assistant's search and play
features. Unsupported capabilities are not added by this integration. The separate
administrative `homeassistant` API is never selected.
Room selection does not create an Assist satellite. Wake words, casting, RTSP
streams and unattended kiosk recovery are not implemented. A kiosk can open
`/anam-assist` on your Home Assistant origin, with authentication and browser
microphone permissions.

## Privacy and session behavior

Anam receives audio or typed messages, Assist prompt context and tool results.
**Live context may include all exposed entity states**, even when you ask about
one sensor. Review Assist exposure before use. Session video recording and
stored transcripts are disabled; this does not promise zero provider retention.
The transcript remains in browser page memory.

The panel and server commands require a Home Assistant administrator. Each bridge
session belongs to its original connection and ends after ten minutes. There are
limits of four simultaneous sessions and 100 distinct tool calls per session.
Ending a session or navigating away stops local media. Reconnects require a new
session. An action already sent to a device cannot be undone by pressing End.
A timed-out action may have happened; inspect its state before trying again.

## Updating and removing

End active sessions, back up the configuration, replace the whole component and
restart Home Assistant. Refresh the browser afterwards. Frontend and backend
must be updated together. Remove the integration through Devices & services
before deleting its directory. Existing Assist pipelines are unchanged.

## Development

Use Node 22 and the pinned lockfile:

```sh
npm ci
npm run check
npm run build
npx playwright install --with-deps chromium webkit
npm run test:frontend
```

Backend tests run with Home Assistant's actual Python packages in a disposable,
network-disabled container. See [the CI workflow](.github/workflows/ci.yml) for
reproducible commands. Tests use synthetic state and fake tool executors; they
never operate a home. Browser tests replace the Anam SDK and Home Assistant
connection with test doubles, so they do not establish paid sessions.

Live testing verified a native portrait stream, a temperature query and control of
one exposed light on Home Assistant 2026.10.3. The owner physically confirmed off
and back on; the integration restored the previous 100% brightness. Commands were
typed into the browser, so this does not validate microphone input. A full
clean-install HACS lifecycle and physical mobile-browser testing remain release
checks. Broader Assist controls have synthetic backend coverage, including climate
exposure revocation, but have not yet been physically verified. This preview makes
no stable compatibility or production-readiness claim.

Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md). Report
vulnerabilities privately using [GitHub security advisories](https://github.com/Smidge/anam-assist/security/advisories/new).
The project is MIT licensed; bundled dependencies have separate notices in
[THIRD_PARTY_NOTICES.md](custom_components/anam_assist/THIRD_PARTY_NOTICES.md).

## References

- [Anam client tools](https://anam.ai/docs/personas/tools/client-tools)
- [Anam session tokens](https://anam.ai/docs/api-reference/sessions/create-session-token)
- [Home Assistant LLM API](https://developers.home-assistant.io/docs/core/llm/)
