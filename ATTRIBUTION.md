# Attribution and scope

The SEP implementation is Dj's work in [aurora-silicon/linux](https://github.com/aurora-silicon/linux/tree/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc), discussed in [omacom/linux PR 7](https://github.com/omacom/linux/pull/7). This repository contains only three pinned storage baseline files for reproducible candidate tests, not a full kernel or Touch ID implementation. Those files retain `GPL-2.0-only OR MIT` headers and Dj's copyright; the MIT option is reproduced in `LICENSES/MIT-Dj`. Derived storage patch portions retain those terms. The device-tree patch derives from Linux device-tree material and retains its original GPL/MIT terms in the pinned upstream source.

Connor Beleznay's original research notes, generator, and test harness are MIT licensed, with AI assistance disclosed. The original implementation, protocol findings, and public tester reports belong to their cited authors. See `research/SOURCES.md` for exact URLs and revision.

Machine inventory, public-comment copies, unrelated source snapshots, biometric data, firmware, and raw disk state are excluded from this publication. Research claims describe the September 29 source inspection and are not fresh hardware qualification.
