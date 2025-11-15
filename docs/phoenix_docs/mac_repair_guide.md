# Mac Repair Guide

The Phoenix Mac Tools suite provides scripted recoveries for Intel and Apple Silicon Macs while respecting macOS licensing. Use
this guide as the operational checklist before engaging customer hardware.

## Intake & Verification

1. **Authenticate Ownership** – Confirm service authorization and gather device serial.
2. **Snapshot Logs** – Capture current boot logs (hold `Cmd+V` on startup) and photograph screen states if necessary.
3. **Inventory Storage** – Run the SystemRescue `disk-inventory` script to map APFS containers, BootCamp partitions, and firmware
versions.

## Standard Recovery Flow

1. **Phoenix Mac Tools Menu** – Boot Phoenix Key, select *Phoenix Mac Tools*.
2. **Run Diagnostics** – Execute:
   - `smc-status` – Reports fan curves and temperature sensors.
   - `nvram-snapshot` – Archives NVRAM variables to the encrypted partition.
3. **Perform Resets** – Follow prompts for NVRAM and SMC reset sequences tailored to the model.
4. **EFI Cleanup** – Launch `phoenix-efi-cleanse` to remove orphaned boot entries and rebuild the BootCamp chain.
5. **Select Recovery Path**:
   - **Intel macOS Reinstall** – Prompts user to attach official macOS installer USB.
   - **Apple Silicon Tahoe 26** – Engages Fidera Ahsari compatibility layer (details below).
   - **BootCamp Repair** – Opens BootCamp Troubleshooting guide within the Web GUI.

## Tahoe macOS 26 (Apple Silicon)

1. **Detect Architecture** – `phoenix-arm-detect` verifies chip ID and secure boot policy.
2. **Stage Fidera Ahsari Packs** – Copies firmware shims, Rosetta scaffolding, and network drivers into the target's DFU staging a
rea.
3. **Initiate Recovery** – Launches Apple's official recovery assistant via `apple_silicon_recover`.
4. **Post-Recovery Validation** – Runs `tahoe-verify` to ensure kernel extensions, UEFI firmware, and Rosetta packages are activat
ed.
5. **Escalation** – If DFU restore fails, reference *Phoenix Emergency Manual* for board-level recovery flow.

## Intel macOS + BootCamp

1. **Installer Prep** – Confirm inserted macOS installer contains latest patches; use `macos-validate` to check build numbers.
2. **BootCamp Drivers** – Run `bootcamp-sync` to refresh the BootCamp driver cache.
3. **Windows Coexistence** – After macOS reinstall, use *BootCamp Troubleshooting* checklists to reapply Windows boot entries.

## Data Preservation

- Use Phoenix "Save My Data" utility before any reinstall operations.
- For APFS snapshots, mount with `apfs-auto-mount` and clone using `rsync --apfs-full-sync`.
- Document preserved paths in the Phoenix Web GUI session log.

## Final QA Checklist

- macOS boots to desktop without error dialogs.
- Secure Boot status restored to original configuration.
- BootCamp partition (if present) is visible from Startup Manager and Windows boots correctly.
- Customer data restored from Phoenix backups where applicable.
- Phoenix session log exported to service ticket.
