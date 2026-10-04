# Implementing Touch ID on this M1 Mac running Omarchy

Research date: **2026-09-29 UTC**. Target: **J293 / T8103, MacBook Pro 13-inch (M1, 2020)**.

## 1. Result and implementation decision

**There is a real experimental implementation to adapt, not a need to invent the entire Touch ID stack.** The best starting point is Dj's [Omacom Linux PR #7](https://github.com/omacom/linux/pull/7), from Aurora's `feat/sep` branch. It supplies a SEP driver, sensor transport, persistent storage machinery, `/dev/sep-bio`, and a libfprint patch. The PR is open and unmerged at inspection.

Pin the inspected source to **`472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc`**. Three storage baseline files from the 74-file change are in [research/aurora-sep](research/aurora-sep/); it is not a complete kernel checkout.

The strongest hardware evidence is a [2026-09-29 J293 tester report](https://github.com/omacom/linux/pull/7#issuecomment-5881303279): same-boot enrollment, matching and PAM work with a modified older series, but saved enrollment does not reload. The newer series fails at a post-user master Catacomb save. The tester used system firmware 15.0; ours is **15.3.1**, not the J313/13.5 combination described in the branch's successful persistence notes. Treat this as **feasible experimental development with an unresolved persistence bug**, not a ready installation recipe.

**Recommended path:** adapt the pinned implementation to J293, retain the M1 cold-boot path, fix board configuration and deployment issues, validate read-only xART discovery, then solve and validate enrollment persistence before enabling everyday authentication. Keep password authentication and LUKS passphrase unlock available throughout.

The request to find how to make missing components is addressed in sections 7–12: each gap has an implementation or a falsifiable development experiment. Research alone cannot provide a tested answer to an undocumented, firmware-dependent save/restore protocol. We do **not** yet have every fact needed to guarantee a working deployment; the specific missing evidence is listed in section 16.

## 2. Evidence discipline and correction of older conclusions

Labels used below:

- **LOCAL:** directly inspected on this machine without changing system configuration.
- **SOURCE:** directly inspected source at the pinned revision.
- **REPORTED:** another developer's hardware result; not reproduced here.
- **DESIGN:** our proposed implementation or test, not proven hardware behavior.
- **OPEN:** information that still requires a controlled experiment or additional source evidence.

Important chronology:

1. [Asahi's current M1 support table](https://asahilinux.org/docs/platform/feature-support/m1/) still lists Touch ID as TBA. That describes supported Asahi functionality, not every experimental fork.
2. [September 7 Open Touch ID Linux research](https://github.com/ELI3GANT/open-touchid-linux/blob/main/RESEARCH_NOTE.md) found seven SEP endpoints on J313 and no biometric service. Its cautious conclusion was that initialization might be missing.
3. [Earlier M1 Pro probing](https://github.com/stevederico/Sapporo/issues/48#issuecomment-5543860841) found the same missing service family. The investigator explicitly withdrew boot-policy keys as a proven explanation. Opcode sweeps did not establish an impossibility theorem.
4. [Omarchy's September 11 announcement](https://omarchy.org/news/2026/09/introducing-omarchy-m/) claimed Dj had Touch ID working. Following this lead revealed the implementation above.
5. [September 25 M1 Pro follow-up](https://github.com/omacom/linux/pull/7#issuecomment-5829902915) reached all twelve endpoints when the new driver serviced xART. This supersedes the interpretation that Linux categorically cannot reach SBIO.
6. September 28–29 J293 reports narrow the remaining problem to initialization details, board SPI mode and persistence. Do not carry forward the early “impossible on M-series” conclusion.

[Asahi's SEP notes](https://asahilinux.org/docs/hw/soc/sep/) remain useful protocol references. [Aurora's research overview](https://aurorasilicon.org/research/security/touch-id/) describes an earlier incomplete implementation; its `-ENOSYS` statements must not be substituted for inspection of the newer branch. Likewise, the PR opening instructions and its newer source documentation disagree on several points. Prefer pinned code plus exact-board results, and preserve contradictions as tests rather than silently choosing a convenient claim.

## 3. Actual machine and environment

Evidence: local inventory (local evidence retained privately), copied configuration/source snippets under research/local (local evidence retained privately).

| Item | LOCAL result | Implementation implication |
|---|---|---|
| Model | J293, `apple,t8103` | Base M1, not Intel T1/T2 or M1 Pro |
| Running kernel | `7.1.13-3-2-ARCH` | Preserve the working distribution base and patches |
| Kernel package | `linux-asahi 7.1.13.asahi3-2` | Experimental SEP changes are not installed |
| OS | Arch Linux ARM, aarch64 | Build native ARM64 packages |
| Kernel memory pages | 16,384 bytes | Do not replace protocol page shifts with Linux `PAGE_SHIFT` |
| Asahi OS firmware property | 13.5 | Does not mean actual system SEP firmware is 13.5 |
| System firmware property | **15.3.1** | Validate the 15.x protocol/persistence behavior |
| m1n1 | 1.6.1-1 | M1 cold boot; no demonstrated need for M2 warm-attach patch |
| SEP | `CONFIG_APPLE_SEP=y`, bound at `242400000.sep` | Built-in stub cannot be replaced by simply loading another module |
| SIO | `CONFIG_APPLE_SIO=m`, DT node disabled | Historical SIO path absent; newer driver uses SPI controller transport |
| Mesa / SPI2 | No exposed fingerprint node in running tree | New board DTS required |
| `/chosen/apfs-preboot-uuid` | **Absent** | Stable host-persisted OS identity fallback is required |
| Omarchy | 4.0.3rc4-1 | Inspect installed scripts, not old internet tutorials |
| Lock screen | Quickshell 0.3.1, `omarchy-lock-*` PAM | Hyprlock settings do not control this lock screen |
| Hyprland | 0.56.2-4 | Include lock/suspend/display regression checks |
| Login manager | SDDM 0.21.0-7 | Separate service from desktop locking |
| Linux account UID | **1001** | Must validate against driver's fixed SEP logical user 1000 |
| Root storage | LUKS mapped root, Btrfs | Driver host state is unavailable before passphrase unlock |
| Apple storage | APFS partitions, `iBootSystemContainer` label exists | xART layout and calibration still need private inspection |
| Fingerprint packages | libfprint/fprintd not installed | Installing stock packages alone will not supply this driver |
| Package DB candidates | libfprint 1.94.100-1; fprintd 1.94.5-2 | Versions line up with bundled patch; repo DB may need refresh at build time |
| Rust / headers | `rustc` absent; running-kernel build directory absent | Prepare a matching full build environment |
| Boot | GRUB; `/boot/m1n1`, `/boot/asahi` present | Rollback must cover stage2/DTBs as well as kernel and initramfs |

Current kernel configuration includes Rust, Apple mailbox and 16 KiB pages. The tag `asahi-7.1.13-3`'s SEP file was downloaded separately and is byte-identical to the inspected Asahi stub. This is source comparison, not proof of the exact binary's entire package patch set.

No privileged firmware experiments, device unbinds, raw disk reads, enrollment operations, package installations, PAM changes, or reboots were performed in this research pass.

## 4. Architecture and boundaries

Apple's [biometric security documentation](https://support.apple.com/guide/security/biometric-security-sec067eb0c9e/web) places matching in the Secure Enclave and protects the sensor link. Linux should relay opaque sensor traffic and consume authenticated matching outcomes, not reconstruct fingerprint images. Opaque encrypted Catacomb files can reside on the host; this is distinct from exporting usable plaintext templates.

```text
Quickshell / sudo / polkit / optional SDDM
                  |
           PAM pam_fprintd
                  |
           fprintd system D-Bus
                  |
     libfprint aurora match-on-chip backend
                  |
         /dev/sep-bio (restricted)
                  |
       kernel SEP transaction/state machine
          |                         |
    Apple mailbox + DART       Apple SPI2 / Mesa sensor
          |                         |
          +------ SEP-directed encrypted relay ------+
          |
    Apple-signed SEPOS: xART, SKS, SCRD, SBIO
          |
    persistent state: shared APFS xART + Linux host files
```

The kernel, root-owned daemon, PAM consumer and local configuration remain trusted. An ordinary PAM match does not provide secure boot, protect against a malicious kernel, unlock a LUKS volume, or create a WebAuthn authenticator. The code's host-generated nonce/token is not itself a SEP-signed biometric assertion.

External Magic Keyboard Touch ID is not a shortcut: [Apple documents](https://support.apple.com/guide/security/magic-keyboard-with-touch-id-secf60513daa/web) that matching still takes place in the Mac's SEP and requires secure pairing. Intel T1/T2 implementations use different host transports; their working results do not establish M1 compatibility. The [T2 project](https://github.com/jmurth1234/t2-touchid-linux) can inform userspace design, but should not be installed as an M1 driver.

## 5. Reusable implementation map

All paths in this table are relative to [the pinned source snapshot](research/aurora-sep/). Consult the code, not just names and comments: some comments still describe earlier profiles.

| Component | Source entry points | What to reuse / verify |
|---|---|---|
| Platform selection | `drivers/soc/apple/profile.rs` | T8103 cold boot, 0x30000 shared memory, Sepos13 request dialect; add board/firmware distinctions where demonstrated |
| SEP lifecycle | `sep.rs`, `rxring.rs`, `work_shim.c` | Boot/discovery, deferred work, endpoint readiness, bounded operations |
| Message protocol | `proto.rs`, `transfer.rs`, `control.rs`, `shmem.rs` | Buffer registration, fragmentation, little-endian fields and explicit message packing |
| Board resources | `dt.rs`, `t8103.dtsi`, `t8103-j293.dts` | SEP/SPI resources, manifests, GPIO and per-device firmware filename |
| Persistent anti-replay service | `xarm.rs`, `xart_apfs.rs`, `xart_store.rs` | Service xART to allow higher services to initialize; APFS extent ownership gate |
| Identity / key store | `sks.rs`, `keybag.rs`, `keybag_identity.rs`, `scrd.rs` | Stable OS identity, keybag initialization/restoration, identity session, credentials |
| Sensor relay | `sensor.rs`, `sensor_shim.c`, `drivers/spi/spi-apple.c` | Sensor power, SPI timing, encrypted capture exchange |
| Biometric protocol | `sbio.rs` | Native communication initialization, registration, enrollment, match, persistence ordering |
| Host persistence | `catacomb.rs`, `store.rs`, `store_shim.c` | Opaque state serialization; needs transaction hardening |
| Userspace ABI | `sep-bio.h`, `bio.rs`, `bio_shim.c` | Versioned ioctl states, exclusive session, cancellation, match token lifetime |
| Fingerprint frontend | `tools/aurora-sep/patches/libfprint-1.94.100-apple-sep.patch` | Native misc-device discovery, enrollment progress, verify/identify, deletion |
| Provisioning tools | `extract-mesa-calibration.py`, `apfs-xart-inspect.py` | Local read-only inspection; do not execute the destructive parts of historical recipes |
| Deployment | `load-driver`, `aurora-sep.service`, `fprintd-aurora.conf` | Starting point only; loader changes described below are necessary |

The patch also modifies NVMe, block crypto, trusted keys and FileVault support. This exceeds fingerprint-only scope. **DESIGN:** isolate optional interfaces behind configuration or split a minimal dependency-closed biometric patch series. Do not delete apparently unrelated code before establishing symbol and state dependencies. Include regression tests for storage and key handling if retaining it.

## 6. Concrete hardware and protocol facts

### 6.1 M1 bring-up

The baseline M1 SEP boot protocol is already implemented in [m1n1](https://github.com/AsahiLinux/m1n1/blob/84715318aeb2071c6d8f67041d057eb06bfc0bef/proxyclient/m1n1/hw/sep.py) and the kernel. The message word carries endpoint bits 0–7, tag 8–15, type 16–23, parameter 24–31, data 32–63. Boot types include TZ0 `0x05`, IMG4 `0x06`, shared memory `0x18`; acknowledgements include `0x69`, `0xd2`, `0x6a`. Encoded addresses use a **12-bit shift**, despite this kernel's 16 KiB pages.

Use the driver's typed profiles. T8103 cold-boots SEPOS and uses the firmware reserved-memory region and supplied manifests. T6020's warm-registration workaround is not a universal Apple Silicon requirement. Do not remove SEP randomness from M1 boot code just because an M2 guide says to do so. Service xART requests and observe SBIO/SKS advertisement; do not replace this with endpoint-enable opcode guessing.

The usual twelve-service inventory is a useful diagnostic for these tested firmware builds, not a permanent cross-version ABI. Readiness should depend on the required named services and completed handshakes, not simply `count == 12`.

### 6.2 J293 sensor configuration

SOURCE plus same-board report, still requiring verification on this unit:

| Property | Candidate value |
|---|---|
| SPI2 MMIO | `0x235108000`, range `0x4000` |
| SPI2 interrupt | AIC IRQ 616, level-high |
| SPI2 pins | 128 clock, 129 MOSI, 130 MISO, mux function 1 |
| Sensor CS | Native chip select 0; **no `cs-gpios`** |
| Sensor bus rate | 8 MHz |
| CS setup / hold | 20 ns / 20 ns, hardware timing |
| Power | `enable-gpios = <&pinctrl_ap 108 GPIO_ACTIVE_HIGH>` |
| Data-ready pin | 104 according to J293 patch comment; currently omitted, polling used |
| Sensor ID | T8103 profile expects `0x3352` |
| Calibration lookup | **`apple/mesacal-j293.bin`** |
| SPI mode | **Mode 2** reported necessary on J293; pinned common tree currently supplies mode 1 |

Required candidate DTS change to the J293 `&mesa` override:

```dts
/delete-property/ spi-cpha;
spi-cpol;
```

This selects CPOL=1, CPHA=0. Do not change the entire T8103 family based on one board. A successful driver bind is insufficient: require a sensible sensor identity, protocol reply and real finger capture.

The existing [m1n1 Mesa tracer](https://github.com/AsahiLinux/m1n1/blob/84715318aeb2071c6d8f67041d057eb06bfc0bef/proxyclient/hv/trace_mesa.py) describes macOS SIO/DMA transport and encrypted traffic. The newer implementation uses `spi_sync_transfer()` in `sensor_shim.c`; its SPI controller is FIFO/PIO based. Thus enabling SIO is **not established as a prerequisite** for this implementation. `capture_qualified: false` remains in profiles but has no consumer found in the inspected source; it must not be mistaken for an enforced safety gate. Validate transport pacing, CPU cost and suspend behavior empirically.

### 6.3 Calibration

Use this machine's own calibration. The bundled extractor reads the iBoot System Container and checks candidate structure and manifest markers; it does not cryptographically authenticate IM4M. Review the exact pinned extractor before granting it raw-disk read access. Never use another Mac's calibration or interpret a successful file write as proof of a correct sensor blob.

The generic instructions use `apple/mesa_calibration.bin`, but J293's DTS asks for `apple/mesacal-j293.bin`. Install at the actual requested path, or deliberately change the DTS and package manifest together. Older extractor revisions reportedly exited nonzero after writing output; check both exit status and validated output, do not blindly ignore failures.

No calibration was extracted here. The older `/var/root/mesa_calibration.bin` macOS recipe assumes that file has already been produced; do not assume ordinary macOS creates it automatically on every installation.

### 6.4 Identity and native initialization

Pinned T8103 settings use the Sepos13 protocol, CPX mode 2, identity create version 2, bag type `0x400000`, parent `-1`. `enable_sbio()` sends opcode **`0x73` with `u32(1)`** before ordinary SBIO traffic. These are recovered protocol details, not arbitrary Linux UID settings. The J293 follow-up connects the missing initialization to the earlier `BEGIN_ENROL` `0x101` failure.

Our missing `apfs-preboot-uuid` requires a stable persisted OS UUID fallback. **Follow-up source finding:** this fallback is not implemented in the pinned head: `prepare_os_uuid()` only consumes explicit parameters or the DT property; the profile identity field is unused. Implement loader-managed persistence with the existing two u64 parameters or add the driver persistence path described in [the source audit](research/STORAGE_PROTOCOL_AUDIT.md). Generate once using initialized cryptographic randomness, store privately and durably, and reuse it. Never regenerate it on every boot or silently substitute a macOS user's identity.

The driver uses a fixed SEP logical enrollment user **1000**, while the Linux user here is **1001**. libfprint labels include Linux username/finger metadata and verifies against a caller's gallery. This can work with a shared internal SEP identity domain, but it is not proof of multi-user isolation. Do not mechanically change protocol owner 501, master -1, or logical user 1000 to the local UID. Section 10 specifies the required ownership design and tests.

## 7. Hardest gap: reboot-persistent enrollment

### 7.1 Observed failure boundary

The latest J293 report separates two builds:

- Older series plus SBIO initialization can save three components and match in the same boot, but fails to restore templates after reboot.
- Newer user-before-master path completes physical enrollment but rejects the final master save with status `0x6`; fprintd correctly refuses to record success.

Our static inspection confirms two save orderings in `sbio.rs`. With `persistent_enrol=true`, T8103 enters `save_all_components_user_first()`, saving the completed user then master after a fresh owner export. This is the exact area to investigate. Neither a host-listed finger nor successful `LOAD_KEYBAG` proves that a live template has been restored.

### 7.2 How we can make the missing behavior

**DESIGN — implement a deterministic persistence state machine, informed by targeted traces, not repeated re-enrollment as a permanent workaround.**

1. **Pin the experiment.** Record kernel and libfprint commits, board, system/OS firmware, SPI mode, OS identity generation, keybag binding generation, command ordering and every status. Give each attempt a unique test ID. Keep private identities and opaque payloads out of public logs.
2. **Instrument only the relevant boundaries.** In `save_all_components_user_first`, `save_catacomb`, `restore_catacomb`, `cold_match_continue` / `ensure_restored_after`, keybag restore/designation and device-view proof, log opcode, component class, state bits, returned status, payload length, elapsed time and commit generation. No raw templates or credentials. Distinguish no reply, transport error, wrong-context response, pending state and refusal.
3. **Maintain one identity bag.** Confirm lookup UUID versus recovered/designated bag UUID using the existing `keybag_identity.rs` rules. Do not “fix” restore by provisioning a new bag while retaining old Catacombs. Verify consistent designated session before export, after each save, and before restore.
4. **Compare protocol order on the same firmware.** Use lawful local macOS host-driver analysis and narrow m1n1 traces to recover context-selection, owner export, user/master save, completion/ack, lockout export and restore order. Filter endpoints and metadata aggressively; unlimited tracing can cause timeouts. A trace of encrypted sensor pixels is not the information needed here.
5. **Separate competing hypotheses.** Use the matrix below. Change one dimension at a time on a recoverable test setup. Never interpret undocumented status `0x6` as harmless merely because a prior operation succeeded.
6. **Add explicit firmware capabilities.** Once a sequence is demonstrated, encode it as a named persistence strategy selected by validated protocol capabilities plus board/firmware evidence. Avoid a sprawling collection of unexplained module switches. Unknown combinations fail closed and retain passwords.
7. **Commit a coherent generation.** Persist the related master/owner/user/lockout state and its bag binding as one logical generation. Publish enrollment to libfprint only after all required exports and durable commit succeed. On restart, validate the complete generation and then prove live identities in the SEP.
8. **Prove the fix across restart.** Same-boot match → clean shutdown/cold boot → same finger match without re-enrollment → wrong finger rejection → macOS/Linux cycle → repeat. Also test partial write and failed-save recovery in emulation before controlled hardware tests.

| Hypothesis | Discriminating experiment | Implementation if confirmed |
|---|---|---|
| Save changes selected context/session | Read state and explicitly reselect documented context before master export; compare macOS sequence | Re-establish correct context at each transition; bind replies to the requested component |
| Master is not exportable immediately after user save | Compare readiness transitions and completion acknowledgement timing, using bounded waits | Model pending/ready states explicitly; do not use unbounded sleeps or blindly retry a mutating command |
| Firmware requires a different export order | Compare J293/15.x and working J313 sequence with identical bag generation | Add a validated firmware-specific order while retaining coherent final generation |
| Old blobs bind to a previous bag | Verify stored bag binding and export metadata; test only a coherently created set | Reject mixed generations; implement explicit migration/re-enrollment, preserving unrelated sealed data |
| Missing owner/lockout state causes empty restore | Compare component availability, load status and live counts at each restore step | Require all dependencies and correct owner initialization before user activation |
| Driver reports success before storage is durable | Fault-inject file and sync failures on synthetic stores | Atomic publication with durable journal and error propagation |
| Enclave accepts load but needs device registration/final proof | Observe count before/after serial registration and COMPLETE_INIT | Keep restored state provisional until live device-view proof succeeds |

**Not solved:** the correct J293/15.3.1 ordering and the exact meaning of its master-save refusal have not been established. The source and reports localize the work; they do not justify claiming a tested fix. Merely toggling `persistent_enrol=false`, suppressing the refusal or returning success to fprintd would hide the problem.

The exact instrumentation contract, source-selection defect, save-pending asymmetry and staged hardware experiment are specified in [PERSISTENCE_EXPERIMENT.md](research/PERSISTENCE_EXPERIMENT.md).

### 7.3 Host file transaction hardening

**Two confirmed source-level prerequisites:** the C/Rust file-open boundary collapses all open failures to ENOENT, undermining the no-existing-keybag gate; and refused-create records bypass CRC/shape validation before authorizing another create. See [the follow-up audit and fix candidate](research/STORAGE_PROTOCOL_AUDIT.md). Address these before provisioning experiments; neither is proven to explain the separate master-save status `0x6`.

SOURCE: `catacomb.rs::write()` calls `open_trunc()`, writes header and blob, then fsyncs. A crash after truncation can destroy the previous complete file. CRC16 detects accidental corruption; it does not authenticate hostile changes. `keybag.rs` also uses truncating writes. The small host-state store's intent mechanism does not make all separate files one atomic transaction.

**DESIGN:** implement a root-owned persistence broker or carefully reviewed kernel file shim with these properties:

- Use a dedicated mode-0700 directory, verified ownership, bounded regular files, no symlink traversal, no unexpected hard links, and exclusive writer locking.
- Write new files to a new generation directory on the same filesystem. Fully write and fsync each; include format version, component type, bag binding and generation in a manifest; fsync directories; atomically publish a generation pointer; fsync its parent.
- Preserve last complete host generation for diagnosis, but **never automatically replay an old generation into xART/SEP**. The enclave's anti-replay state is authoritative.
- Journal intent, host durability and observed SEP commit progress. There is no automatic atomic transaction across the filesystem and SEP; ambiguous crash states must stop and require reconciliation, not blindly roll back.
- Report ENOSPC, read-only filesystem, corrupt component, missing component and identity mismatch separately. Do not convert any into “no enrolled fingers” unless the SEP actually reports a valid zero count.
- Unit-test interruption at every storage boundary, then power-loss behavior on expendable hardware. Test Btrfs snapshot restore explicitly: host filesystem rollback does not roll back SEP hardware state.

The required private state inventory includes `aurora-sep-os-uuid.bin` if used, `aurora-sep-keybag.bin`, the selected ref-key slot, `aurora-sep-host-state.bin`, all three `apple-sep-catacomb-*.bin` files, and fprintd records. Snapshot them coherently for diagnosis. Keep them off git and do not copy them between Macs.

## 8. xART/APFS: the most consequential storage challenge

The new driver supplies an xART service backed by the shared Apple APFS `.gl` file. This is what the old stub lacked. It is not an ordinary Linux fingerprint database.

SOURCE: [XART-SAFETY.md](https://github.com/aurora-silicon/linux/blob/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc/tools/aurora-sep/XART-SAFETY.md) describes a narrow supported layout: a complete checksum-valid checkpoint, simple single-node trees, one unencrypted 6 MiB extent, no snapshots/revert/clone state, exactly one physical extent reference owned by the `.gl` inode, and valid unambiguous records. Unsupported layouts must fail closed. The bundled tests demonstrate that a historical signature-window locator can choose the wrong physical start.

### Implementation rules

1. Resolve `.gl` from validated APFS metadata, using the [Apple APFS reference](https://developer.apple.com/support/apple-file-system/Apple-File-System-Reference.pdf) as the format authority. A pattern match, partition label or highest-scoring record window is not authorization to write.
2. Start with `xart_writes=0` and provisioning off. Compare the independent inspector's result with the driver's result. This machine's actual extent has not been inspected.
3. If the layout is unsupported, extend the parser read-only first: bounded B-tree traversal, object-map lookup, correct checkpoint selection, extents/reference validation, integer overflow limits, cycle/depth bounds and adversarial synthetic fixtures. Do not fall back to guessed offsets.
4. Before any writer, prove exclusive ownership for the lifetime of the raw access. The current ordinary block-file open is not in itself an exclusive mount/relocation lock. Reject concurrent APFS mounting and establish how to prevent mapping changes. Revalidate at each attach; never persist a universal sector constant.
5. Keep fresh-record write, durability barrier, old-record retirement and second durability barrier ordered. Verify the block-device fsync/cache behavior actually provides the required ordering on Apple NVMe; do not assume file-level success proves power-fail durability.
6. Check malformed/duplicate revisions before arming writes. Test full store, duplicate revisions, torn records, failed flush, interrupted delete and exhaustion using synthetic media first.
7. Coordinate with SEP anti-replay semantics. Raw disk backups are useful forensic artifacts, **not a universal rollback** for hardware epochs. Repeated provisioning/deletion may make recovery worse. Never use a “reset everything” loop as an automated retry.
8. Require a verified recovery path and off-machine backups before the first real write. Apple distinguishes revive from erase/restore; follow [Apple's recovery instructions](https://support.apple.com/en-us/108900) for the exact machine. Restoring firmware does not promise recovery of previously encrypted data.

These precautions address specific behavior of the chosen implementation, not hypothetical generic risk. The source's own write-safety notes say that prior successful key operations did not necessarily exercise an actual xART write. A harmless test result cannot validate an unexercised write path.

## 9. Kernel, boot and packaging implementation

### 9.1 Build strategy

**DESIGN:** create an isolated full kernel checkout with the stock distribution baseline and the pinned SEP series. Inventory the package's existing patches before rebasing. Preserve 16 KiB page configuration, Apple GPU/DCP, storage, keyboard, encryption and audio settings. The checked-out source snapshot here is insufficient for building.

Build an independently named `linux-asahi-touchid-test` package with a unique kernel release and modules directory. Include matching DTBs and initramfs. Ensure Kconfig actually enables the new driver: it depends on Rust, HW_RANDOM, TRUSTED_KEYS and crypto; `olddefconfig` can remove a requested option if dependencies are missing. Start from `/proc/config.gz`; verify the resulting diff and use `make LLVM=1 rustavailable` with the supported Rust/Clang/bindgen versions of the chosen tree.

Use `CONFIG_APPLE_SEP=m` for the experiment and load after the real root is mounted: host state lives under `/var/lib`. The running built-in stub is not replaceable in-place; booting the experimental kernel is required. Avoid generic DKMS as the first packaging strategy because this patch modifies core SPI, storage and trusted-key interfaces as well as the SEP driver.

A source-only build outline, **not an installation command**:

```sh
# In an isolated COMPLETE kernel checkout with the intended series applied:
zcat /proc/config.gz > .config
scripts/config --module APPLE_SEP
make LLVM=1 olddefconfig
make LLVM=1 rustavailable
# Inspect the config diff and ensure APPLE_SEP survived dependency resolution.
make LLVM=1 -j"$(nproc)" Image modules dtbs
```

Source tests already executed here: **8 passed, 1 skipped** in `tools/aurora-sep/tests`; the skipped test requires `rustc`. They test calibration/extent parsing using synthetic fixtures. They do not test hardware, the full kernel or persistence. No claim of a successful full build is made.

### 9.2 Boot-chain footguns on this installation

LOCAL: `/usr/bin/update-m1n1` treats its **first positional argument as the output TARGET**, not the input m1n1 binary. Therefore the PR's generic `update-m1n1 /path/to/aurora-m1n1.bin` recipe is wrong for this installed script and could overwrite the supplied path. Input is selected via `M1N1`; DTBs via `DTBS`; inspect `/etc/default/update-m1n1` and package hooks first.

The script concatenates stage2, DTBs, compressed U-Boot and configuration into a bundle. It defaults to DTBs from the latest `*-ARCH` modules directory. A custom release suffix can be silently missed, while an automatic package hook can silently select the wrong tree. Explicitly select and verify the intended DTB set when assembling a test bundle.

A one-shot GRUB kernel entry does **not** roll back a globally changed stage2/DTB bundle. Preserve the original bundle and test recovery before modifying the default. Determine the correct per-entry FDT handoff for this boot chain; do not feed GRUB a raw source DTB that loses m1n1's runtime firmware fixups. Inspect the live tree after boot to prove the J293 node/mode actually reached Linux.

M1 needs the cold-boot protocol according to the implementation and follow-up tests. [Omacom m1n1 PR #1](https://github.com/omacom/m1n1/pull/1) specifically preserves M1 behavior while adjusting M2+ warm state. We do not need an unrelated bootloader replacement merely to copy M2 instructions.

Retain a known-good kernel, its initramfs and modules; preserve m1n1/U-Boot/DTB recovery separately. A bad SPI change can break the built-in keyboard at the LUKS prompt. Have an independently tested input/recovery route before the first experimental boot. Check the actual GRUB menu ID rather than copying a menu title that does not exist here.

### 9.3 Loader and service design

Pinned `load-driver` hardcodes `modprobe apple_sep xart_writes=1 provision_keybag=1`. This is unsuitable for a read-only first boot and can duplicate `/etc/modprobe.d` options. Same-board reports describe misleading Rust parameter errors in that situation.

Implement one source of module options and separate modes:

- **Observe:** writes off, provisioning off, endpoint/storage diagnostics only.
- **Provision:** an explicit one-time operation after layout and recovery validation; preserve a provisioning intent and stop on ambiguity.
- **Restore:** normal boot; restore the existing identity and fingerprints without automatic re-provisioning.

Do not retry a one-shot SEP attach by unloading/reloading. Time out visibly and require a fresh boot. Handle missing block-device symlinks through explicit device dependencies or bounded deferred startup after udev; `After=local-fs.target` alone does not prove every device is ready.

Separate biometric readiness from optional trusted-key seal/unseal readiness. The current loader tests `keyctl` and requires a ref-key file; a failure there blocks fprintd even when the biometric path might work. Build a non-enrolling health query that checks the required SEP services, valid identity context, usable sensor and proven restore state. Never mark health successful solely because `/dev/sep-bio` exists.

Package systemd units, module options, library and udev rules together with version constraints. Preserve systemd device sandboxing: permit `/dev/sep-bio` explicitly rather than disabling all protection. Inspect the installed fprintd unit's capability and DevicePolicy settings against driver requirements. fprintd can be D-Bus activated; use the same tested readiness gate for that route.

## 10. Userspace, ownership and authentication security

### 10.1 Prefer the existing libfprint backend

Patch **libfprint 1.94.100** with the bundled patch and retain stock fprintd/PAM interfaces. Build and package against this aarch64 system. Avoid two daemons competing for `net.reactivated.Fprint`. Retain other libfprint drivers if external readers matter; an `aurora`-only build narrows testing and may produce empty hardware metadata artifacts.

For experimental library isolation, a root-owned private prefix plus a service-specific library path is possible, but verify the running daemon loads the intended `.so`. A package with explicit provides/conflicts and rollback is preferable for deployment. Do not overwrite distribution libraries with an untracked `ninja install`.

The [fprintd device API](https://fprint.freedesktop.org/fprintd-dev/Device.html) defines claiming, enrollment, verification, cancellation and status signals. Use it unchanged. Keep authorization checks, device exclusivity and release-on-client-disconnect. A replacement service would have to recreate all of these semantics; that extra work is unnecessary now that a backend exists.

### 10.2 ABI and replay model

SOURCE: ABI version 4 exposes GET_INFO/LIST, ENROL_START/POLL, VERIFY_START/POLL, CANCEL and DELETE operations. **Correction after following the outer dispatch:** ATTEST is implemented in `sbio.rs::bio_ioctl()` before the general `bio.rs` dispatcher. It calls `bio_attest()` and `refkey_attest_sign()` to sign a supplied challenge digest using the machine reference key. That path does not require a successful biometric match, consume its token, or produce an Apple certificate chain. It is a key-possession signing operation, not evidence of fingerprint authentication; runtime operation on this Mac remains untested. The earlier claim that ATTEST lacked implementation was incorrect.

The library checks terminal success, a nonzero token and a monotonic deadline, then compares the matching identity against the requested gallery. The kernel generates and consumes the token using its stored nonce and identity. Its ten-second token lifetime is host state. A stale library comment attributes binding to the enclave; **source-level enforcement here is in the trusted host kernel**. Do not market this token as remotely verifiable SEP proof.

**DESIGN:** test nonce freshness, repeated POLL, duplicate terminal results, cancellation races, descriptor close/reopen, simultaneous PAM callers, delayed callbacks and suspend. Invalidate pending operations across suspend/resume and lock-session changes; CLOCK_MONOTONIC's suspend behavior must not accidentally extend an authorization into a later session. A root or kernel compromise remains outside protection offered by this local authentication design.

### 10.3 User isolation — especially UID 1001 here

Keep SEP protocol slots distinct from Unix accounts. fprintd's per-user gallery must be authoritative for which live SEP identities can authenticate that account. Require:

1. Enrollment/removal authorized through fprintd's existing PolicyKit policy, with password/admin verification appropriate to the chosen policy.
2. A match UUID must be in the requesting user's persisted gallery; another account's enrolled finger must not succeed.
3. Unprivileged users cannot write labels, issue raw ioctls or forge gallery ownership.
4. Username changes, UID reuse, account deletion, duplicate fingers across accounts and capacity exhaustion have explicit behavior.
5. Enrollment, delete-one and delete-all affect precisely the intended identities. Review the backend's whole-device clear operation before exposing multi-user management.

Start with one tested Linux account if necessary, but label that limitation. A complete multi-user implementation should use stable account identifiers and an ownership database, protected by the system service. Do not trust a free-form label as authorization.

### 10.4 Attack and robustness boundaries

Keep `/dev/sep-bio` root/service-only. Review CAP_SYS_ADMIN checks and fprintd's capability bounding set; do not solve access problems with mode 0666. Bound every user buffer, ABI version, reply length and out-of-line allocation. Fuzz protocol parsers with synthetic inputs and test unknown enums as failures.

Require exclusive device sessions and bounded cancellation. The driver already has an exclusive-open guard; verify cleanup after daemon crash and removal. Retain accurate distinction between sensor unavailable, canceled, no comparison and wrong finger. In particular, unavailable live-count data must never become an authoritative zero that triggers destructive reconciliation.

Do not expose a general raw SEP command interface in production. A development-only, root-restricted, bounded probe can help recover a specific protocol transition, but it must be excluded from release builds. Avoid broad opcode sweeps: several known control messages wedge SEP until reset, and arbitrary persistent commands can damage state.

## 11. Omarchy integration on this exact release

### 11.1 Detection and setup

LOCAL: `omarchy-hw-fingerprint` checks USB descriptors and selected vendor IDs. Adding Apple's vendor ID would create false positives and would not expose the integrated sensor. The script's claim that all readers are USB is not applicable to the new misc-device backend.

**DESIGN:** add a backend-aware readiness check using fprintd GetDevices and device capabilities when installed, with a narrow platform/device probe for pre-install discovery. Differentiate “supported hardware, driver missing” from “ready for enrollment.” Do not pretend the mere `apple_sep` platform driver proves biometrics.

The installed setup wizard installs stock libfprint and may replace experimental packages. Update it to preserve the explicitly selected SEP backend and exact version. Keep its good ordering: enroll and verify before changing PAM. Use structured D-Bus status instead of matching localized CLI output with `grep -qi finger` for readiness.

### 11.2 Quickshell lock

LOCAL: `Service.qml` runs two independent `PamContext`s:

- Password: `/etc/pam.d/omarchy-lock-password`.
- Fingerprint: `/etc/pam.d/omarchy-lock-fingerprint`.

The fingerprint file is currently absent. The packaged intended contents are:

```pam
#%PAM-1.0
auth       required                    pam_fprintd.so
account    include                     system-local-login
```

This is a **future candidate**, not applied. SOURCE: [Quickshell v0.3.1 PAM subprocess](https://github.com/quickshell-mirror/quickshell/blob/1a4716cde794a59928d9d9fc15f2afc7a95de360/src/services/pam/subprocess.cpp) calls `pam_authenticate()` and `pam_end()`, with no `pam_acct_mgmt()` call. Thus the account line is not enforced by that upstream authentication path. If account restrictions must govern lock-screen unlock, add an explicit account-management step to the PAM consumer (with deliberate expired-password behavior), or a reviewed authentication helper that performs both calls. Treat this as an explicit product-policy decision for an already logged-in session; test disabled/expired accounts. LOCAL cross-check: the installed `/usr/bin/quickshell` dynamic symbols include `pam_authenticate`, `pam_end` and `pam_start_confdir`, and no `pam_acct_mgmt` symbol. This supports the source finding without exercising authentication.

The password stack stays usable while the fingerprint transaction is pending. Test simultaneous completion and cancellation carefully. The shell retries failed fingerprint contexts after 250 ms; add bounded backoff and suppression for persistent sensor/lockout failures so an unavailable SEP does not cause endless reopen loops. Never let a retry reset SEP lockout.

`omarchy-apply-lock` writes both lock PAM configurations; using it is not a fingerprint-only edit and can overwrite existing password customizations. Review a concrete diff and preserve the previous files before eventual use. Modify packaged Omarchy behavior through a maintained patch/package or supported plugin mechanism, not ad hoc edits in `/usr/share/omarchy`.

### 11.3 sudo and polkit

The stock wizard inserts `auth sufficient pam_fprintd.so` before password authentication, with a lid-closed skip. This means fingerprint **or** password, not both. Validate account restrictions and desired faillock behavior; an early sufficient success skips later auth modules. Preserve the existing account/session includes and never globally weaken `system-auth` to get a demo working.

LOCAL: `/etc/pam.d/polkit-1` is absent, but `/usr/lib/pam.d/polkit-1` exists and includes `system-auth`. The wizard's “missing file” branch creates a simpler stack and changes those semantics. Build the override from the effective vendor configuration, rather than treating absence under `/etc` as absence of policy.

[pam_fprintd's manual](https://man.archlinux.org/man/pam_fprintd.8.en) explains its serialized PAM behavior. A single sudo conversation will normally wait for fingerprint attempts/timeout before password fallback. Choose bounded `timeout` and retry values; do not promise simultaneous password entry there merely because Quickshell can run separate contexts. Test stdin/SSH/noninteractive sudo and retain `sudo -n` semantics.

The lid gate's `[success=1 ...]` is positional: inserting another module changes what is skipped. Test it as a control-flow graph, including failure to read lid state and clamshell operation. Preserve password fallback when the sensor is inaccessible.

### 11.4 SDDM and other consumers

Treat SDDM as a later, separate integration. Do not modify `sddm-greeter` instead of the user authentication service. Decide whether first login after cold boot remains password-only; a Linux experiment should not silently claim Apple's first-login policy is replicated. Fingerprint login does not provide a password for GNOME Keyring/KWallet decryption; keep their normal unlock prompts or password login.

1Password may use a polkit-based system-authentication path, but confirm the application's actual integration separately. Browser passkeys/WebAuthn, Apple Pay, SSH keys and generic SEP keyctl are separate projects. A successful sudo fingerprint match does not automatically enable any of them.

### 11.5 LUKS and early boot

Do not couple disk unlock to this first implementation. The current driver requires `/var/lib` state on the encrypted root, so attempting to use it to unlock that same root creates a dependency cycle. A boolean match is also not an encryption key.

A future design would require an initramfs-safe SEP driver, integrity-protected state available before root mount, a genuine key-release policy bound to a biometric result, signed/trusted boot assumptions, and recovery credentials. A ref-key seal/unseal test does not demonstrate biometric gating. Keep the existing LUKS passphrase slot. A separate supported FIDO2 security-key unlock can be evaluated independently; it is not built-in Touch ID.

## 12. Challenge and footgun register

This is a coverage checklist, not a claim to enumerate unknowable future failures. Each row has an action and a completion criterion.

| ID | Challenge / footgun | Solution or implementation | Completion evidence |
|---|---|---|---|
| C01 | Unsupported stock kernel | Package pinned SEP series on working distro base | Experimental kernel boots with matching modules |
| C02 | Wrong architecture / T1/T2 recipe | Target J293/T8103 path only | Profile and live DT agree |
| C03 | Asahi table vs fork reports | Track supported and experimental states separately | Exact source and hardware result cited |
| C04 | Stub binding mistaken for success | Record handshake and required service readiness | SBIO/SKS respond, not just a sysfs link |
| C05 | Seven endpoints | Service xART initialization | Required higher endpoints appear |
| C06 | M2 warm path copied to M1 | Preserve cold boot on T8103 | Clean attach on stock m1n1 |
| C07 | Hot reload after one-shot attach | Reboot with bounded diagnostics | No misleading rebind success |
| C08 | Page / IOVA unit mismatch | Explicit protocol units, checked conversions | Boundary tests and no DART faults |
| C09 | Firmware/board profile conflation | Validated capability/persistence profiles | J293 + 15.3.1 result recorded |
| C10 | Missing stable OS UUID | Durable host-generated fallback | Identity unchanged across restarts |
| C11 | Wrong calibration or filename | Local validated blob at DTS path | Actual sensor accepts it |
| C12 | Wrong SPI mode despite bind | J293-only mode-2 override | Sensor/device view and capture succeed |
| C13 | Wrong CS or GPIO | Native CS, 20 ns timing, named enable GPIO | Scope/timing evidence or repeated verified captures |
| C14 | SPI changes break keyboard | Restrict timing callback to Mesa bus | Keyboard works at LUKS and desktop |
| C15 | Missing SBIO initialization | Native `0x73/u32(1)` before enrollment | Begin-enroll accepted |
| C16 | Wrong keybag dialect/parent | T8103 Sepos13 create tuple | Provision once, restore thereafter |
| C17 | Guessed `.gl` physical offset | Checksum-valid APFS ownership resolver | Independent inspector agrees |
| C18 | Unsupported APFS layout | Extend read-only parser, fail closed | Synthetic fixtures and real read-only validation |
| C19 | Concurrent APFS remap | Exclusive ownership/lifetime contract | No writer/mount can invalidate extent |
| C20 | xART torn write or epoch drift | Ordered durable records, controlled provisioning | Fault tests and validated recovery behavior |
| C21 | Snapshot/raw backup rollback | Never equate host rollback with SEP rollback | Ambiguous state refused |
| C22 | Cross-generation Catacombs | Explicit bag binding and generation manifest | Mixed state rejected deterministically |
| C23 | Save refusal / empty restore | Section 7 protocol experiment and state machine | Cold-boot match without re-enrollment |
| C24 | Truncate-before-save | Atomic generation publication | Crash injection retains coherent state |
| C25 | ENOSPC, corrupted state | Distinct hard failures, preserve originals | No false enrollment success |
| C26 | Duplicate module options | Single authoritative config source | Clean modprobe with all intended values |
| C27 | Loader conflates keyctl and biometrics | Independent readiness gates | fprintd starts only on biometric readiness |
| C28 | fprintd sandbox blocks device | Narrow DeviceAllow/capability integration | Normal D-Bus operation under sandbox |
| C29 | Stale/default libfprint loads | Package or verify private library path | Running daemon identifies Aurora backend |
| C30 | UI progress mistaken for capture | Only real kernel stage increases count | No false progress without a finger |
| C31 | Zero RNG token | Initialized kernel CSPRNG, reject invalid token | Match accepted only with fresh valid evidence |
| C32 | Replay, cancel, late callback | Session-bound nonce, single consumption, cancel invalidation | Race/replay tests fail closed |
| C33 | UID 1001 vs SEP slot 1000 | Separate account gallery from protocol identity | Correct user passes; other user fails |
| C34 | Whole-device deletion/multi-user | Enforced identity ownership and scoped deletion | Other account remains usable |
| C35 | USB-only detection | Backend-aware discovery | Integrated SEP sensor detected without USB spoofing |
| C36 | Wrong lock screen | Quickshell's actual PAM service | Physical lock/unlock test |
| C37 | Polkit vendor policy overwritten | Preserve effective includes in override | Disabled/expired user behavior retained |
| C38 | PAM skips/fallback/lockout | Model stack control flow and bounded retries | Password works in every failure case |
| C39 | Endless 250 ms retries | Backoff and permanent-failure state | No busy loop or lockout reset |
| C40 | Suspend/resume stale state | Cancel, revalidate services, restore safely | Repeated sleep cycles without re-enrollment |
| C41 | Closed lid/unavailable sensor | Password fallback and correct lid skip | Clamshell unlock remains usable |
| C42 | LUKS circular dependency | Keep first-phase passphrase unlock | Cold boot succeeds without SEP service |
| C43 | Wrong stage2 update argument | Use installed script's actual interface | Correct output bundle verified |
| C44 | GRUB rollback doesn't restore DTB | Separate stage2/FDT rollback | Known-good boot tested after failure |
| C45 | Kernel/firmware updates | Pin combinations and test migration | Upgrade and rollback acceptance runs |
| C46 | Opaque blobs leaked in logs/git | Private storage and metadata-only traces | Artifact review before publication |
| C47 | Reference-key signature mistaken for biometric attestation | Follow outer ioctl dispatch and signing preconditions | No fingerprint/WebAuthn claim from ATTEST alone |
| C48 | Broad storage/key changes | Dependency analysis and optional feature split | NVMe/FileVault/keyctl regression checks |
| C49 | Closed PR mistaken for merged fix | Read merged flag and actual code | Patch inclusion established by diff |
| C50 | Untested sensor damage/calibration repair | macOS hardware baseline before low-level debugging | Known-good hardware separately established |
| C51 | Corrupt primary Catacomb silently selects legacy store | Typed errors; authoritative generation; explicit migration | Corruption and I/O fault tests never select fallback |
| C52 | Reference tracer dumps buffers and has always-true channel filter | Metadata-only tracer, corrected endpoint filter, board-derived pins | No payload output; bounded, loss-detecting traces |
| C53 | Master save-pending gate differs by strategy | Record actual state and compare validated firmware sequence | Coherent saved generation survives cold boot; skipping save alone is insufficient |

Historical Asahi issues [#591](https://github.com/AsahiLinux/linux/issues/591), [#594](https://github.com/AsahiLinux/linux/issues/594), [#598](https://github.com/AsahiLinux/linux/issues/598) identify IOVA cleanup, asynchronous boot observability and mailbox timeout IRQ handling concerns. PRs [#592](https://github.com/AsahiLinux/linux/pull/592), [#593](https://github.com/AsahiLinux/linux/pull/593) and [#599](https://github.com/AsahiLinux/linux/pull/599) are closed **without merging**. Verify behavior against the chosen new driver/base; do not mechanically cherry-pick stale fixes or assume newer branch numbers imply resolution.

## 13. Staged implementation work packages

These are dependency-ordered engineering tasks. They are not instructions to run mutations during this research session.

### W0 — Reproducible source and host baseline

Pin full kernel/base and libfprint revisions; save package recipes/config; preserve original boot artifacts. Confirm macOS Touch ID hardware health and off-machine recovery. Collect public firmware versions plus private calibration/ADT details only where necessary. Deliverable: reproducible build manifest and known-good recovery route.

### W1 — J293 observation kernel

Apply board SPI mode, exact firmware filename, known GPIO and native-CS behavior. Retain M1 cold boot and implement the missing stable OS identity fallback. Fix loader to permit read-only bring-up with no provisioning. Build and validate DT schema, full kernel and initramfs. Deliverable: boot log proving intact desktop/keyboard/storage and required SEP services, with xART still read-only.

### W2 — Storage and lifetime hardening

Audit extent ownership, block locking, failure ordering, host transaction writes, parameter parsing, boot timeout and service readiness. Add synthetic parser/crash/race tests. Deliverable: inspectable patch set and read-only agreement between independent storage parsers; no unresolved write-location ambiguity.

### W3 — Minimal hardware enrollment experiment

After storage/recovery prerequisites are satisfied, provision once, enroll through fprintd, verify enrolled and wrong fingers, and capture metadata around each persistence step. Avoid mixing raw enroll utilities with fprintd. Deliverable: a proven same-boot match with exact source/firmware and no false positive or password regression.

### W4 — J293 persistence fix

Execute the section 7 hypothesis matrix. Implement the validated save/restore strategy and atomic host generations. Deliverable: repeated cold-boot and macOS/Linux-cycle verification **without re-enrollment**, plus controlled failure recovery. This is the current critical path.

### W5 — Account and service integration

Validate UID 1001 ownership and negative multi-user cases; version/package libfprint; harden daemon startup/cancel/resume. Deliverable: fprintd API works under its real systemd sandbox and correctly scopes identity galleries.

### W6 — Omarchy deployment

Patch discovery/setup to preserve the custom backend. Add Quickshell fingerprint PAM after proven enrollment/restore; preserve password policy. Integrate sudo/polkit with reviewed stack diffs, then optionally SDDM. Deliverable: UI and password fallback acceptance results and package-managed rollback.

### W7 — Release qualification

Run the matrix below, external code/security review, update testing and migration checks. Ship only the tested board/firmware combinations, with health/status UI for unsupported combinations. No blanket “M1/M2 supported” statement based on one J293.

## 14. Acceptance tests and rollback

| Test | Required outcome |
|---|---|
| Correct enrolled finger | One fresh authorized match, scoped to the active request |
| Different/unregistered finger | Failure, never authentication success |
| No finger, dirty/wet/partial touch | Bounded retry/guidance; password remains usable |
| Cancel / Escape / close client | Operation ends, claim released, late result cannot unlock |
| Two concurrent callers | Correct serialization; no result crosses sessions |
| Wrong account / UID reuse / deleted account | No authorization from another user's gallery |
| Locked or expired account | Enforced according to explicit application/PAM policy |
| No device / daemon crash / malformed reply | Fail closed for fingerprint, usable password fallback |
| Enrollment canceled halfway | No orphaned successful host record; recoverable SEP state |
| Delete-one / delete-last / full capacity | Correct identity removed; no unrelated data reset |
| Clean reboot, then cold power cycle | Match without re-enrollment and valid live identity count |
| Boot macOS, then Linux | Linux and macOS remain usable; persistence state consistent |
| Suspend / lid close / resume repeatedly | No stale success, wedged claims or unexplained resets |
| Downgrade/upgrade firmware or driver | Known compatibility or explicit refusal, no silent re-provisioning |
| ENOSPC / partial write / failed fsync | No claimed durable enrollment; coherent diagnosis/recovery |
| Btrfs snapshot restore | Stale SEP-bound state detected rather than replayed |
| Synthetic APFS corruption/relocation | Read/write authorization refused |
| Quickshell lock + wrong fingerprint + password | Remains locked on failure; correct password unlocks |
| sudo without cached timestamp | Fingerprint path truly tested; denial/fallback work |
| polkit and SDDM separately | Real consumer behavior verified, not inferred from sudo |
| LUKS boot with SEP unavailable | Existing passphrase and keyboard still work |
| System regression | Display/GPU, Touch Bar, keyboard, NVMe, audio, power and thermals unchanged within measured tolerances |

Suggested qualification target: at least 10 cold boots and 20 suspend/resume cycles with no loss of identity, plus repeated positive and negative finger tests. These are engineering acceptance targets, not a measured biometric false-accept certification.

Rollback deployment changes in reverse dependency order: restore reviewed PAM files/remove added overrides, stop optional biometric activation, restore distribution libfprint, boot the known-good kernel and restore the matching stage2/FDT bundle if changed. Preserve private state for diagnosis. **Do not erase keybags, wipe `.gl`, restore stale raw xART images, or factory-reset the sensor as an ordinary rollback.**

## 15. Research artifacts and verification

- README (see the linked upstream sources): entry point.
- Local inventory (local evidence retained privately): sanitized hardware/firmware/package facts.
- [Follow-up storage/protocol audit](research/STORAGE_PROTOCOL_AUDIT.md): concrete errno, marker-validation and missing-UUID findings, with implementation details.
- [Candidate storage error patch](proposals/store-open-errors.patch): preserves open errors across the C/Rust boundary; 27 C-level injected open cases passed.
- [Candidate J293 SPI patch](proposals/j293-spi-mode2.patch): unapplied, checked to apply against the snapshot; not built or hardware-tested.
- Quickshell v0.3.1 PAM source (see the linked upstream sources): confirms the upstream consumer does not perform account management.
- [Pinned implementation snapshot](research/aurora-sep/): three storage source files from the PR head; other references remain upstream.
- PR metadata (see the linked upstream sources) and timestamped comments (see the linked upstream sources): provenance and latest J293 reports.
- PR file list (see the linked upstream sources): scope of the source changes.
- Asahi installed-tag SEP source (see the linked upstream sources): baseline comparison.
- [M1 implementation notes](https://github.com/aurora-silicon/linux/blob/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc/tools/aurora-sep/M1-SUPPORT.md): protocol and tested-scope details.
- [xART design constraints](https://github.com/aurora-silicon/linux/blob/472f69313a7bd563786f5e2e6c9a2af3d5c1d3cc/tools/aurora-sep/XART-SAFETY.md): narrow storage support and remaining write validation.
- Aurora PR #52 metadata (see the linked upstream sources): J293 provisioning/loader diagnostics; some fixes have since been integrated differently, so compare code before applying.
- `research/SHA256SUMS` and `research/SOURCES.md`: artifact integrity and source locations.

Test command actually run:

```sh
python -m unittest discover -s research/aurora-sep/tools/aurora-sep/tests -v
```

Result: nine Python test entries, eight passed, one skipped because Rust is not installed. The skipped test would compile extracted entropy methods with stubs. No real SEP, raw disk, fingerprint or PAM operation was exercised.

## 16. Remaining facts needed before saying “implementation-ready”

1. **This machine's APFS `.gl` extent/ownership and calibration validity.** Requires reviewed local raw-device reads, not web research. The block device is not readable by the current unprivileged account; no elevated read was attempted.
2. **J293 + system firmware 15.3.1 save/restore protocol.** Requires a controlled hardware experiment or a tested patch for this combination. The current public J293 result explicitly lacks persistence.
3. **Crash consistency across host state and SEP anti-replay state.** Atomic files are necessary but insufficient; the coupled protocol needs failure-injection evidence.
4. **A complete build and boot of the chosen integrated series.** Neither the partial snapshot nor source-only tests establish this.
5. **UID 1001 and negative multi-user behavior.** The fixed logical SEP user is a design boundary requiring explicit tests.
6. **The exact recovery/FDT handoff procedure for a test boot on this installation.** A one-shot GRUB entry alone cannot protect a globally modified bundle.
7. **Security and regression review of the broad experimental kernel series.** Especially raw APFS writes, kernel file access, trusted-key code and storage changes.

These are concrete remaining work items, not reasons to abandon the goal. The path to making each missing component is specified above, but it would be misleading to present untested hypotheses as completed solutions or to claim that research has already removed every blocker.

## 17. Research log

- Inspected actual hardware, package versions, page size, firmware properties, boot script and effective authentication configuration.
- Located early SEP/SBIO negative reports, Asahi stub source and current support table.
- Followed the conflicting Omarchy announcement to Dj's GitHub implementation rather than stopping at the unsupported status page.
- Retrieved current PR metadata/comments and pinned the 74-file implementation snapshot.
- Found same-board J293 enrollment/authentication evidence and explicit persistence failure; matched its firmware family to this Mac's 15.3.1 property.
- Audited board mode/calibration mismatch, loader duplication, host identity fallback, fixed SEP user versus local UID, host-token trust boundary, in-place state writes and stage2 command semantics.
- Ran upstream synthetic source tests; recorded passes and the missing-Rust skip.
- Produced a dependency-ordered implementation design, persistence experiment matrix, 50-item challenge register, and acceptance/rollback plan.

### Continuation audit — 2026-09-29

Rechecked the live PR head (unchanged). Confirmed the missing OS UUID fallback and two keybag gate defects through source control flow. Prepared an unapplied errno-preservation patch and compiled a synthetic C fault-injection harness: 27 open cases passed. Full Rust/kernel compilation and hardware persistence remain unverified. See the linked follow-up audit for exact limitations.

### Persistence instrumentation audit — 2026-09-29

Inspected concrete save/restore call sites and the reference Mesa tracer. Added three source-backed challenges (C51–C53) and an [experiment specification](research/PERSISTENCE_EXPERIMENT.md) covering trace fields, insertion points, interpretation, stop conditions and acceptance criteria. These findings refine the hardware experiment; they do not establish the correct firmware sequence. Also corrected the ATTEST implementation claim by following the outer ioctl dispatch into reference-key signing; it exists but does not prove a biometric match.

### Completion audit — 2026-09-29

[Requirement-by-requirement audit](research/COMPLETION_AUDIT.md): the research artifacts are delivered, but exact-firmware persistence and hardware qualification remain incomplete. The live upstream head is unchanged. The latest J293 report already has both components at state `Some(7)`, so merely adding a save-pending check cannot explain or fix its refusal. Further resolution requires controlled hardware evidence or new upstream results.
