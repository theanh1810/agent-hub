# Mobile flow

1. **Device setup**: `xcrun simctl boot` / `emulator -avd ...`; install `.app` / `.apk`; reset state between flows.
2. **Frameworks**: **Detox** (React Native): `device.launchApp({ newInstance, permissions, url })`, matchers `by.id` / `by.text`. **Maestro**: declarative YAML; deep links, biometric stubs, push.
3. **Network capture (L3)**: Charles / `mitmproxy`, Detox `device.captureViewHierarchyString()` plus the native HTTP log, or a debug interceptor in the app.
4. **Mobile checks**, each action logged with the screen it reached: permissions; deep links (`device.openURL` / Maestro `openLink`); biometrics (`device.matchFace()` / `matchFinger()`); push; backgrounding (`device.sendToHome()` then resume); orientation (`device.setOrientation`).
5. **Evidence**: a screenshot at each assertion and on failure → `{workspace_root}/.cm-tmp/{task_id}/`, per `skills/testing-e2e/references/evidence-paths.md`.
