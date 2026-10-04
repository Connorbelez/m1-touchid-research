# J293 persistence: discriminating experiment and instrumentation design

Research date: 2026-09-29. Driver revision: `472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc`. Target: J293/T8103, system firmware 15.3.1. **Design only: no experimental boot, provisioning or biometric operation has been performed on this machine.**

## Question to answer

Why does the reported J293 user-first enrollment sequence refuse the following master SAVE_CATACOMB with status `0x6`, and why does the older sequence fail to restore live identities after reboot? These are separate observations from different builds. Do not assume a single cause, or treat a same-boot match as a persistence test.

Evidence: [latest same-board report](https://github.com/omacom/linux/pull/7#issuecomment-5881303279), [pinned SBIO implementation](https://github.com/aurora-silicon/linux/blob/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc/drivers/soc/apple/sbio.rs), [keybag identity rules](https://github.com/aurora-silicon/linux/blob/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc/drivers/soc/apple/keybag_identity.rs). The local firmware differs from the reporter's 15.0, so reproducing their result is itself an experiment.

## Additional source findings affecting interpretation

### Restore can silently change its source of truth

`catacomb.rs::read()` returns `Option<KVec<u8>>`. Missing files, EIO, allocation failure, bad magic, size mismatch and CRC failure all produce `None`. `sbio.rs::read_stored()` tries that file first, then the host store's same kind key after **any** such failure. Host-store read errors are also collapsed to `None`. `restore_catacomb()` turns that result into `NoStoredFile`.

This establishes two source-level defects in diagnostics/policy: corruption is indistinguishable from absence, and a failed primary read can select another copy without establishing an equivalent generation. It does **not** prove stale copies are present on this machine or that the enclave accepts them. Even enclave rejection would make the observed restore failure misleading.

Implementation: change the reader boundary to `Result<Option<ValidatedCatacomb>>`, with `None` reserved for verified ENOENT. Preserve I/O, allocation, format and checksum errors. Make the new generation manifest authoritative. Legacy host-store import must be an explicit one-time migration with bag-binding and generation validation; a runtime read failure must never trigger automatic legacy selection. Emit the selected source and a private generation label before LOAD. If the new format has no trustworthy binding information, stop and reconcile rather than infer equivalence from matching component IDs or file timestamps.

Acceptance: valid primary wins; corrupt/unreadable primary stops even when a valid legacy copy exists; missing primary plus legacy copy requires explicit migration; legacy I/O errors remain errors; mismatched bag/generation never reaches LOAD. Add tests at the real reader API, not only a duplicate parser in another language.

### The legacy Mesa tracer is unsuitable unchanged

The snapshotted m1n1 tracer (see the linked upstream sources) contains:

- `if msg.EP == 0x18 or 0x19:` — Python interprets this as `(msg.EP == 0x18) or 0x19`, so it is always true. Replace with `msg.EP in (0x18, 0x19)` when adapting the tracer.
- `chexdump(data)` in `log_mesa()` and writing `large_message.bin` for large receive buffers. Disabling just the file write does not remove buffer disclosure.
- `RegMonitor.poll()` over DMA regions and verbose SPI tracing, which also need removal or metadata-only replacements.
- A hardcoded GPIO map `0xc4: mesa_pwr`; the J293 driver uses GPIO108. Discover board pins from the actual device tree instead of treating that map as J293 evidence.
- Its own warning that traffic is encrypted after power-on. Sensor bus capture alone does not recover SEP host save/restore ordering.

Implementation: create a separate metadata-only tracer with an explicit endpoint allowlist, no buffer dumps, no generic memory monitor and bounded output. Keep the original as reference. For this persistence question, prioritize SBIO/SKS/xART host transactions over SPI pixel traffic. Hypervisor setup and supported macOS/firmware combination still require a separately validated boot procedure; this file is not an instruction to run the tracer on the daily-use installation.

## Instrumentation contract

Add opt-in structured trace events to the driver in a full isolated checkout. Keep them disabled by default. Prefer a bounded trace buffer over unconditional kernel log messages; record buffer overflow so missing events cannot be mistaken for missing firmware operations. Do not add state-changing queries just to log an event. Any additional state query belongs to a separately labeled experiment because it can change timing.

Each event records:

| Field | Meaning |
|---|---|
| schema | Version of trace record format |
| boot/test ID | Random label for this experiment; never a hardware serial |
| event sequence | Monotonic sequence; detect drops and ordering gaps |
| monotonic timestamp | Time within this boot; never compare raw values across boots |
| operation ID | Correlate one request, reply and durable-write result |
| phase | Initialization, enrollment, export, confirmation, restore, proof, match |
| component | master, owner, enrollment-user, lockout, identity-bag |
| opcode | Actual protocol opcode; do not infer from a friendly message |
| result kind | Transport failure, timeout, firmware answer, host error |
| result code | Firmware status or errno in its own namespace |
| length | Bounded response size, not response bytes |
| component state | Raw bits from an already performed state query, plus query event ID |
| source/generation | Authoritative host source and private generation label |
| host stage | Write begun, file sync complete, publication complete |
| identity binding | Same/different/unknown against expected bag and OS identity |

Do not log templates, sensor images, calibration, key material, nonces, opaque blobs, raw bag UUIDs, hardware serials or authentication tokens. If cross-boot identity comparison requires labels, keep the mapping in the protected experiment directory; publish only equality results and run-local labels. An ordinary hash of a low-entropy secret is not safe anonymization.

## Exact insertion points and existing evidence

| Location in `sbio.rs` | Current behavior | Additional evidence needed |
|---|---|---|
| `open_fresh_context` | Fresh context exports eligible components and, on persistent profiles, owner | Trace owner export/confirmation and its binding before physical enrollment |
| `save_all_components_user_first` | Reads states before user and master; requires user save-pending; requires master active but saves it regardless of pending bit | Preserve raw state and which strategy selected; distinguish master state `0x3` from `0x7` |
| `save_catacomb` | SAVE `0x6c`, validate length/carried user, host write+fsync, CONFIRM `0x37` | Separate every boundary and failure; associate resulting host copy with the request |
| `run_enrolment` | Saves components, then resnapshots identity bag before reporting success | Record bag snapshot result; never infer it from successful component confirms |
| `save_after_match` | Saves lockout, conditionally user/master, then bag snapshot | Match mutates persistence too: record a separate generation and failure |
| `restore_catacomb` | Loads `0x6d`, checks component state, may retry a cold-transition user load | Trace selected source, first and second load separately, identity counts and exact reason for retry |
| `confirm_active` | Accepts active bit after querying state | This is component readiness, not proof of restored fingerprints |
| `complete_bringup` / device-view proof | Uses identity count and readiness to gate matching | Record final live count and readiness; no authentication success without an actual match |

The pinned constants name bits `0x1` cold, `0x2` active, `0x4` save-pending. These are the implementation's recovered semantics, not a complete public firmware specification. `0x101` is treated as already-active for LOAD; it must not be assigned that meaning globally across opcodes. `0x8002` is a cold-transition observation requiring follow-up proof. **Status `0x6` remains undecoded.**

An important asymmetry is already visible: user-first completion saves an active master unconditionally, while the alternate completion and post-match paths require its save-pending bit. The published J293 report already records **both states as `Some(7)` immediately before the refused master save**. Therefore, a missing save-pending bit does not explain that reported failure; checking the bit alone cannot fix it. Retain the state field to detect whether this 15.3.1 machine follows the same path. Simply skipping that save is not a solution: a previous host master image may be incompatible with the newly confirmed user. Prove correct generation binding and cold restoration before adopting any conditional-save strategy.

## Staged experiment

1. Establish backup/recovery readiness and a validated reversible kernel+DTB boot procedure. Fix the storage prerequisites in [the audit](STORAGE_PROTOCOL_AUDIT.md), stable OS identity, J293 mode/calibration and authoritative restore source. Build and test in a full checkout. No blind installation of the PR's loader.
2. Freeze a configuration manifest: exact kernel/libfprint/tool revisions, compiler/config, firmware properties, mode, parameter set and trace schema. Record identities privately; do not copy another device's files. Disable automatic GUI retries during tests.
3. Observe initialization with provisioning disabled. Confirm UUID availability, xART geometry/ownership validation, endpoint readiness and absence of unexpected writes. This cannot prove that later mutation is safe, but rejects incorrect setup before enrollment.
4. Perform one controlled enrollment only when the previous stages pass. Collect the naturally occurring component-state and save/confirm sequence. On first persistence failure, stop the attempt, preserve its host state and metadata, and do not automatically re-enroll or delete files.
5. Classify the failure: transport versus firmware refusal; user versus master; SAVE versus host fsync versus CONFIRM versus bag resnapshot. Verify host source/generation and stable identity before changing firmware order.
6. Compare the failed transition with a working same-firmware host trace, if available. If no such trace can be collected, restrict changes to a hypothesis supported by the recorded state and published exact-board evidence. Never run a sweep of mutating opcodes.
7. Implement one strategy change in an isolated build. Reconcile the previous partially advanced state first; do not call each retry a fresh experiment while reusing ambiguous files. Keep existing xART hardware anti-replay state authoritative.
8. Only after coherent save success, test cold reboot restore, live identity proof and actual positive/negative verification. Repeat after an ordinary successful match, because matching can update the template and bag snapshot. Then test suspend/resume and a macOS/Linux cycle.

## Stop conditions and solution criteria

Stop on incomplete traces, unknown identity binding, primary-store corruption, contradictory component IDs, raw xART validation failure, transport desynchronization, unexpected anti-replay behavior, or any missing durable-write acknowledgement. Preserve evidence rather than retrying mutation automatically.

A solution requires all of: deterministic save/restore strategy for J293/15.3.1; coherent durable host generation; preserved enclave anti-replay behavior; repeatable cold-boot live identities; correct positive and negative matching; propagated failures through libfprint/fprintd; multi-user ownership checks; and recovery behavior under interrupted persistence. A clean trace, an active bit or a populated fprintd directory proves only part of that chain.

## Current outcome

Static inspection now identifies the exact trace boundaries, a restore-source ambiguity, a potentially relevant save-pending asymmetry, and concrete problems in the reference tracer. None supplies the missing hardware observation. The correct J293/15.3.1 persistence sequence is still an open experimental result, not a finished implementation.
