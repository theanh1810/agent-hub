# security domain desktop mobile
<Owner: skills/review-checklist/SKILL.md>
<Read when: a diff touches a desktop or mobile app, a privileged helper, an updater, a local daemon, a native-messaging host or a local IPC endpoint>

---

Deep-link binding, webview bridge origin checks, exported components, data surviving logout and pending-action display are already in `skills/review-checklist/references/security-surfaces.md` (§ Client surfaces); this file adds local IPC and the privileged helper, with the few app-state gaps left over. Base checks: `skills/review-checklist/references/security-depth.md`. Rating: `refs/roles/reviewer/finding-bar.md` § Confidence and severity, after `skills/review-checklist/references/security.md` § What is a finding fixing what qualifies, and this file adds none. Browser-side webview behavior is in `skills/review-checklist/references/security-domain-client-side.md`, native memory and loader safety in `skills/review-checklist/references/security-domain-memory-binary.md`, update authenticity in `skills/review-checklist/references/security-domain-supply-chain.md`.

## When to use

The target is a desktop or mobile app, privileged helper, updater, local daemon, webview host, deep-link handler, browser native-messaging host or local IPC client or server. The untrusted actor may be a downloaded document, remote web content, another local app, another OS user, a confined process or a lower-privilege account; state the starting capability instead of treating every local user alike.

## Core discipline

- Name the realistic attacker: another app, another OS user, a confined child, an untrusted document or a remote origin. Harming oneself within the same account and authority is not a boundary violation.
- Paths, process names, bundle or package IDs and claimed sender fields are not peer authentication; use OS peer credentials, code identity, capability handles or protected channel state.
- The bridge or helper authorizes each operation and the final resource after parsing; a trusted UI or broker does not make attacker-influenced arguments trusted.
- OS confinement, signing, entitlements, permissions, keychain access rules, exported-component policy and prompts are real controls when pinned and visible.
- Signing, manifest merge, OS version, device policy, setup-package access rules or packaging that the repository does not show are `needs_validation`.

## Callback and handoff classes

- **App and account handoff confusion**: sign-in, magic-link, invite, device-pairing, passwordless or payment callbacks return to the wrong app on the device, profile, tenant or pending transaction. Bind state to the initiating app identity, current session, account, provider, operation and expiry.
- **File-open and intent authority**: an associated file, share intent, drag-and-drop item, clipboard record, notification action or open-file event triggers a privileged operation without confirming content type, sender trust where it applies, current user intent and the final target.

## Webview file-access classes

- **File and universal access**: remote content reads app-local files, privileged custom schemes or internal origins because file access, universal access, mixed content, debug interfaces or custom protocol handlers join origins unexpectedly. A permissive-looking setting with no reachable protected content is hardening.
- **Over-broad bridge**: web content picks arbitrary files, commands, IPC methods, credentials or system actions through a generic bridge. Check method allowlists, normalized arguments, user or tenant authority, gesture or confirmation requirements and what the return value discloses.

## Local IPC classes

- **Peer authentication gaps**: Unix sockets, named pipes, XPC, Binder, D-Bus, native messaging, RPC, shared memory or host-address listeners accept a lower-trust peer without checking OS credentials, code identity, confinement token or channel ownership. Needs a meaningful method or disclosure behind the channel.
- **Claimed principal versus channel identity**: the authenticated process or channel belongs to one app or user, but request fields select another user, tenant, profile or capability. Bind each method and resource to the peer credential, not a caller-declared identifier.
- **Lifecycle and correlation confusion**: predictable request IDs, reused handles, stale channels, inherited descriptors, world-writable socket paths or restart behavior let one peer answer, cancel or reuse another's operation. Read creation permissions and cleanup of socket files, locks, ports and shared mappings.
- **Local automation endpoints**: an externally invokable endpoint performs work meant for the app itself; read the merged manifest or registration, intent filters, permission or signature level, path grants and alias entries. Status unknown after packaging is `needs_validation`.

## Privileged helper and local file classes

- **Helper as confused deputy**: a low-privilege caller selects a privileged command, file, service, user or system setting without per-operation authorization. Read sudo, polkit, elevation-prompt and XPC helper rules, and confirm the helper validates normalized arguments itself.
- **Setup, update and repair path trust**: a privileged helper reads manifests, scripts, packages, symlinks, working directories or repair state that a lower-trust actor can write after authorization. Bind authorization to immutable content and safe destination paths.
- **File ownership and check-then-use**: the app checks a path, then follows a replacement, symlink, mount or case and normalization change during a privileged read or write. Use descriptor-relative operations and verify final ownership; parsing after the file is open belongs to the memory-safety domain.
- **Local secret boundary mismatch**: a keychain item, token file, backup, log, clipboard, notification preview or local configuration readable by another app, profile or user with less authority. Plaintext readable only by the same intended OS account is not automatically a vulnerability; state the lower-trust reader and the credential's power.

## Application state and device lifecycle classes

- **Leftovers across accounts**: widgets, background tasks, notification content, local databases, webview storage or biometric approvals that outlast logout, an account change or a device restore and show up under the next account; read backup, restore and multi-profile behavior.
- **Deferred authorization**: a shortcut, share sheet, biometric prompt or queued operation authorizes something other than what was displayed, runs after expiry, or picks up another profile's pending state. Bind confirmation to the normalized action, resource, account and current foreground state.

## Universal moves

- Enumerate every process, app component, local endpoint, URI scheme, file association, webview origin and helper; record OS identity, runtime privilege, caller and callable operation.
- Read the final packaging inputs (merged manifest, entitlements, setup-package rules, native-messaging registration, protocol handlers, access rules at creation): source declarations can be overwritten downstream.
- Account switch, logout and device restore need a run on an isolated machine or emulator with dummy profiles; where none is available the candidate is `needs_validation` naming that local run, and other users' apps, credentials and production services are never touched.

## Validation rules

1. Name the attacker's starting capability, the OS or app principal crossed, the entry channel, the accepted argument or state, and the unauthorized operation or disclosure.
2. Confirm the confinement, peer credential, signing, entitlement, permission, consent and setup-package controls that apply; unknown packaging or runtime facts are `needs_validation`.
3. Webview bridges cite both the navigation or origin control and the privileged native sink; IPC cites peer authentication and per-resource authorization; helpers verify the final normalized destination.
4. Local proof stays bounded, uses dummy content and accounts, and stops once the boundary result is shown, without extending into persistence or wider system change.
5. `confirmed` needs a full source and local evidence chain; `needs_validation` names the exact OS, manifest, signing, access-rule or device-lifecycle fact required.
