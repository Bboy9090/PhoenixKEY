# Compatibility Notes

Phoenix Key targets heterogeneous environments; this reference highlights firmware, storage, and silicon caveats that influence
depoyment success.

## Firmware Profiles

### Legacy BIOS
- Enable **Legacy Mode** in Phoenix Hybrid Loader when encountering pre-UEFI boards.
- Use lightweight Linux decks (Alpine, Puppy) if RAM < 2 GB.
- Disable Phoenix Smart Drivers auto-download to avoid network stack incompatibilities.

### UEFI (Secure Boot Disabled)
- Default operation mode; Ventoy handles boot chain seamlessly.
- Phoenix Smart Drivers can run in full automation.
- Recommended for diagnostics suites that require unsigned kernels.

### UEFI (Secure Boot Enabled)
- Ensure Phoenix Secure Boot keys are enrolled; otherwise use signed ISOs (Windows, Ubuntu, Fedora).
- Phoenix PE uses Microsoft-signed WinPE binaries; additional drivers must be signed.
- Linux rescue images may need shim/grub-signed variants.

## Storage Controllers

| Controller | Mitigation |
| --- | --- |
| Intel RST / VMD | Enable Phoenix Smart Drivers to stage IRST/VMD packages into Windows PE; add `intel_vmd=1` kernel flag for Linux. |
| AMD RAID | Include latest AMD RAID packages in the encrypted partition; slipstream into Windows installers. |
| NVMe (OEM) | Some OEM NVMe drives need vendor NVMe drivers; ensure Phoenix Smart Drivers caches them ahead of time. |
| Legacy IDE | Force Linux kernels with `libata.noacpi=1` when encountering unreliable IDE controllers. |

## Graphics and Display

- Hybrid Mode Loader selects safe boot parameters (`nomodeset`, `nouveau.modeset=0`) for problematic GPUs.
- For NVIDIA Optimus laptops, prefer Windows installers with integrated DCH drivers and Linux kernels with PRIME support.
- macOS Tahoe 26 recovery flows detect Apple Silicon vs Intel and inject the appropriate Fidera Ahsari shim.

## Apple Hardware

- **Intel Macs** – BootCamp installer auto-runs post-Windows install. Phoenix Mac Tools handles EFI cleanup.
- **Apple Silicon** – Use Fidera Ahsari packs to stage firmware and network drivers within the Tahoe 26 workflow. Booting Linux req
uires Phoenix-provided U-Boot payloads.
- **OCLP Targets** – Provide Phoenix OCLP helper scripts stored in the encrypted partition and referenced from the Mac Repair Guid
e.

## Chromebooks & ARM Boards

- Enable Developer Mode and boot from USB; Phoenix provides ARM-compatible SystemRescue builds.
- Use Linux rescue deck with `console=ttyS0` for serial-over-USB diagnostics.
- Documented in the Linux Rescue Playbook under "ChromeOS Flex & ARM" scenarios.

## Peripheral Requirements

- Keep USB-C to USB-A adapters rated for USB 3.1 Gen2 to maintain Phoenix Thermal-Aware Flashing reliability.
- For offline environments, stage Phoenix Offline License tokens in the encrypted partition.
- Provide 65W+ USB-PD power sources for sustained Apple Silicon recovery sessions.
