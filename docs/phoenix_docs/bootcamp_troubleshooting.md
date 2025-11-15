# BootCamp Troubleshooting

Use this guide after deploying or repairing Windows on Mac hardware. It focuses on restoring full device functionality with Phoe
nix Smart Drivers and BootCamp automation.

## Quick Diagnostic Matrix

| Symptom | Root Cause | Resolution |
| --- | --- | --- |
| Missing BootCamp control panel | BootCamp services not installed or corrupted | Run `bootcamp-sync` from Phoenix Mac Tools, then rerun the BootCamp installer from the Phoenix cache. |
| No startup disk option for Windows | EFI entries removed during macOS recovery | Execute `phoenix-efi-cleanse --rebuild` to regenerate BootCamp boot entries. |
| Keyboard/trackpad dead in Windows | Apple SPI drivers missing | Inject latest SPI/SMC drivers using Phoenix Smart Drivers or rerun BootCamp support package. |
| Audio unavailable | Cirrus Logic/Realtek drivers missing | Use `phoenix-driver-inject --bundle audio` to deploy vendor drivers. |
| Discrete GPU not detected | AMD/NVIDIA drivers absent | Run `phoenix-driver-inject --bundle gpu` which stages BootCamp GPU packages. |
| No Wi-Fi on Apple Silicon | Fidera Ahsari layer absent | Ensure Tahoe macOS 26 workflow completed; reapply Fidera Ahsari packs via Mac Repair Guide. |

## Recovery Steps

1. **Collect Logs** – Launch Phoenix Web GUI → Diagnostics → "Collect BootCamp Logs".
2. **Verify Boot Mode** – Confirm Windows installed in UEFI mode. If not, convert using `mbr2gpt /convert` (Windows PE).
3. **Driver Audit** – Run `phoenix-driver-audit` to list missing device IDs.
4. **Apply Driver Bundles** – Use `phoenix-driver-inject` with targeted bundles (`chipset`, `gpu`, `network`, `audio`).
5. **Rebuild Services** – Run `bootcamp-repair --services` to fix BootCamp services and startup tasks.
6. **Validate Input Devices** – For Apple T2 devices, ensure Apple Keyboard Helper service is running.
7. **Finalize** – Reboot and confirm BootCamp control panel detects macOS partition.

## Escalation Paths

- **Persistent BSODs** – Use Windows Event Viewer logs captured by Phoenix to identify faulty driver; revert to previous bundle ve
rsion.
- **Secure Boot/BitLocker** – When BootCamp enables BitLocker, store recovery key in Phoenix encrypted partition.
- **Touch Bar Issues** – Deploy `phoenix-touchbar-restore` to reload Touch Bar firmware for Intel models.

## Customer Handover Checklist

- BootCamp control panel opens without errors.
- Function keys, audio, and trackpad operate normally.
- GPU acceleration active (check Device Manager → Display adapters).
- Wi-Fi and Bluetooth connected.
- Recovery documentation exported to `/PhoenixDocs/bootcamp_session_report.json` for ticketing.
