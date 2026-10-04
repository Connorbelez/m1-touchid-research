# Candidate implementation changes

`j293-spi-mode2.patch` is an unapplied board-only candidate against Aurora SEP commit `472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc`. It translates the same-board SPI mode finding into a reviewable diff. It has not been built or hardware-tested here and does not solve enrollment persistence.

Do not apply it to the installed DTB or boot bundle directly. Apply in the full isolated kernel checkout described in the main dossier, then build and validate the resulting DTB and boot handoff.

`store-open-errors.patch` is an unapplied fix candidate for the storage C/Rust error boundary. Generate it reproducibly with `python proposals/build-storage-candidate.py`; run its isolated C fault tests with `python -m unittest discover -s proposals/tests -v`. The Rust side and full kernel integration have not been compiled. See [the audit](../research/STORAGE_PROTOCOL_AUDIT.md).
