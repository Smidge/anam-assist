# Contributing

Use synthetic names and state in tests and issues. Do not attach Home Assistant
backups, credentials, real transcripts, session tokens or unredacted logs.
Report security issues privately through the repository's Security tab.

Run the checks in `.github/workflows/ci.yml` before submitting a pull request.
Commit the rebuilt browser bundle alongside source changes. Keep runtime
dependencies pinned and include their license notices.

Changes to tool permissions need tests for denied as well as allowed calls.
Changes to session behavior need cancellation, disconnect and late-response
coverage. Mocked tests do not replace a declared live compatibility check.
Do not expand home control beyond lights without a separate design review.
