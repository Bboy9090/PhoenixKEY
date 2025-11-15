# Linux Rescue Playbook

Phoenix Key's Linux deck covers everything from minimal shell access to full desktop recovery. This playbook provides scenario-
based runbooks.

## Scenario Matrix

| Scenario | Recommended ISO | Key Actions |
| --- | --- | --- |
| Failed GRUB/EFI | SystemRescue | Run `phoenix-grub-repair`, reinstall bootloader, regenerate EFI entries. |
| Btrfs corruption | SystemRescue | Use `btrfs restore` with Phoenix snapshot rotation; capture logs in `/PhoenixLogs/`. |
| Legacy netbook recovery | Puppy Linux | Boot RAM-resident environment, copy user data with `phoenix-save-data`. |
| Chromebook Developer Mode | Alpine ARM build | Launch `chromeos-flex-prepare`, apply crossystem flags, flash Flex image. |
| Remote headless server | Alpine | Use `phoenix-ssh-relay` to tunnel into remote management network. |
| Forensic capture | Kali | Run `phoenix-forensic-kit` to image disk with `dcfldd` and verify hash. |

## Workflow Highlights

### SystemRescue
- Default environment for disk-level work.
- Includes Phoenix partitioning scripts (`phoenix-partition-plan`) for Ventoy, encrypted vault, and OEM zones.
- Houses Phoenix Tool Scanner daemon for ISO metadata updates.

### Lightweight Desktops
- **Puppy Linux** – Perfect for user data extraction when hardware is limited.
- **Lubuntu** – Offers LXQt desktop for GUI-driven tasks; includes Phoenix Remote Desktop client.

### Security & Forensics
- **Kali** – Contains Phoenix incident response scripts and network reconnaissance bundles.
- Logs stored in encrypted partition to maintain chain of custody.

### Apple Silicon & ARM
- Fidera Ahsari-enhanced SystemRescue builds provide GPU/USB support on M1/M2.
- Use `phoenix-arm-boot` to switch between U-Boot payloads.

## Kernel Parameter Cheat Sheet

| Symptom | Parameter |
| --- | --- |
| Black screen on boot | `nomodeset` |
| Nouveau issues | `nouveau.modeset=0` |
| AMDGPU fallback | `amdgpu.aspm=0` |
| Intel iGPU flicker | `i915.enable_guc=0` |
| USB boot hangs | `usbcore.old_scheme_first=1` |
| RAID detection failure | `rd.driver.pre=dm-mod` |

## Post-Operation Checklist

- All modified filesystems pass `fsck`.
- Boot entries validated with `efibootmgr` or `bless` (Mac).
- Rescue logs synced to Phoenix Auto-Forge change log.
- Customer receives PDF summary generated from PhoenixDocs HTML export.
