# Mobile release

Load for an iOS or Android build, store submission or update.

- **Tools**: **EAS** — `eas build:configure`; `eas build -p ios|android --profile preview`; `eas update --branch production` (JS-only update); `--auto-submit` pushes to the stores. **Fastlane** — iOS: `match`, `cert`, `sigh`, `pilot` (TestFlight), `deliver`; Android: `supply` (Play Store), `gradle`.
- **Signing**: iOS through Apple Developer provisioning profiles, automated with `fastlane match`; Android through a Java keystore (`keytool`) with Google Play App Signing and an `.aab` upload key.
- **Distribution**: TestFlight internal (instant) and external; Google Play internal / closed / production tracks, phased with `--rollout 0.1`.
  - **HYPOTHESIS, left unchanged on purpose**: the external TestFlight limit (`≤100` testers, 90-day window) has no source here and may be the *internal* cap (`rules/core.md § No invented rule`); confirm against Apple's docs or Context7 before a release plan depends on it.
- **Approval gates** (`needs_approval`): TestFlight external (stakeholder), store production (PM and QA), certificate rotation (security).
- Store releases cannot be rolled back directly: reduce the phased release to 0%.
