# M1 Touch ID research

[![CI](https://github.com/Connorbelez/m1-touchid-research/actions/workflows/ci.yml/badge.svg)](https://github.com/Connorbelez/m1-touchid-research/actions/workflows/ci.yml)

A pinned research dossier and unapplied patch candidates for the M1/J293 Apple SEP Touch ID experiment. This is not an installer or a working authentication product. The driver has not been booted on the research machine. Reboot persistence remains unresolved in the cited J293 reports.

Read [the dossier](TOUCH_ID_RESEARCH.md), [storage audit](research/STORAGE_PROTOCOL_AUDIT.md), and [experiment design](research/PERSISTENCE_EXPERIMENT.md). The baseline is Aurora SEP revision `472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc`; only three storage source files are vendored for offline candidate tests. Other source snapshots stay upstream.

## Reproduce the candidate tests

Requires Python 3, Git, and a C compiler. These commands compile injected C failures without opening hardware or modifying a boot image.

```sh
python3 proposals/build-storage-candidate.py
git diff --exit-code -- proposals/store-open-errors.patch
python3 -m unittest discover -s proposals/tests -v
```

The C harness verifies preserved file-open errors. It does not compile the Rust/kernel integration or establish firmware compatibility. `j293-spi-mode2.patch` remains unbuilt and untested. Follow the dossier's qualification gates before any hardware work.

Report findings with the source revision, model, firmware version, operation, expected result, and redacted evidence. Never upload enrollment templates, SEP keybags, calibration data, credentials, or disk images. [Attribution](ATTRIBUTION.md) explains ownership and the mixed source terms. [Roadmap](ROADMAP.md) defines the next review gates.
