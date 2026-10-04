# Completion audit and current research boundary

Date: 2026-09-29. This audit evaluates the original requested outcome: enough technical information to implement Touch ID on this M1 Omarchy installation, including solutions for missing components. It does not equate an extensive report with a proven solution.

| Requirement | Authoritative evidence reviewed | Result |
|---|---|---|
| Identify this machine and installed integration | `local/inventory.json`, copied installed boot/PAM/lock scripts | Research complete for inspected configuration; no experimental changes |
| Find actual implementation and support status | Pinned 74-file source snapshot, PR metadata, September 29 live API recheck | Experimental implementation identified; open/unmerged head unchanged |
| Explain hardware/firmware/kernel/userspace chain | Main dossier sections 3–11 and source audits | Documented, with observed versus proposed behavior distinguished |
| Identify challenges and how to address them | 53-entry register; W0–W7; storage audit and experiment specification | Concrete fixes or experiments specified; not all validated |
| Track research in Markdown | `TOUCH_ID_RESEARCH.md`, `STORAGE_PROTOCOL_AUDIT.md`, `PERSISTENCE_EXPERIMENT.md` | Delivered |
| Supply implementation candidates where tractable | Two unapplied patches; application checks; 27 C open fault cases | Limited candidates verified at stated scope, not a built kernel |
| Determine correct J293/15.3.1 persistence sequence | Current same-board report still refuses master SAVE on newer series; older series fails cold restore | **Incomplete: decisive hardware evidence missing** |
| Establish private on-device prerequisites | Local APFS raw device not read; calibration not extracted; stable OS identity absent in DT | Incomplete; collection and validation specified |
| Establish reboot, ownership and failure correctness | Acceptance matrix; no experimental driver boot or biometric operations here | Incomplete; synthetic tests cannot establish these properties |
| Guarantee every blocker has a working solution | Explicit unresolved facts in main dossier section 16 | Not achieved; no such claim is justified |

## Revalidated upstream result

`FINAL_UPSTREAM_CHECK.json` records the live PR check. Head remains `472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc`, open and unmerged. Its latest update is still September 29 at 00:29:26 UTC. The latest J293 comment remains the report of same-boot authentication with broken reboot persistence. No new resolution was found in this recheck.

The source audit's save-pending asymmetry is real, but the report explicitly says both components were `Some(7)` before refusal. This rules out a missing pending bit as the explanation for that reported attempt. The experiment document now makes this limitation explicit.

## Blocking condition and next evidence needed

The same critical missing fact has persisted across at least three consecutive goal turns: the correct save/restore behavior on J293 with this firmware family. Source review produced useful prerequisites and corrections, but cannot establish undocumented firmware acceptance and cross-reboot state transitions. More report expansion or synthetic tests would not supply that evidence.

The next material step needs either:

1. A controlled hardware investigation on this J293, with backup/recovery readiness, a tested kernel+DTB recovery path and participation during reboot/fingerprint tests; or
2. New upstream exact-board/firmware results establishing the sequence, followed by local qualification.

A question about hardware experiment availability and backup/DFU recovery readiness has been sent to the user and has no answer in the current session. Research authorization has not been treated as readiness to reboot or provision persistent enclave state on the daily-use machine. No request to contact upstream or publish logs was inferred.

The goal is blocked on that missing evidence/readiness, not complete. The research documents and candidates remain available for implementation. A full implementation/build/test phase may resume when the hardware path is established; this audit is not a claim that those engineering tasks have already been performed.
