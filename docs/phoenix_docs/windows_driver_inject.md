# Windows Driver Inject Guide

The Phoenix Smart Drivers pipeline automates Windows PE customization so installers always ship with the right storage, network,
and platform drivers. Follow this guide to extend or troubleshoot the process.

## Pipeline Overview

1. **Inventory Hardware** – `phoenix-driver-audit` scans the target system via WinPE or existing Windows.
2. **Resolve Dependencies** – Missing drivers are pulled from vendor mirrors or the Phoenix encrypted partition cache.
3. **Slipstream** – `phoenix-driver-inject` stages drivers into WinPE (`boot.wim`) and install images (`install.wim`).
4. **Validate** – `phoenix-driver-verify` boots the modified WinPE in a VM sandbox to confirm driver load success.

## Common Scenarios

### Intel RST / VMD Laptops
- Run `phoenix-driver-inject --bundle storage --target intel-rst`.
- Confirms `iaStorVD.sys` and supporting inf files are added to both boot and install images.
- Adds `iaStorVD` services to the PE registry hive.

### AMD Ryzen Mobile
- Use `--bundle chipset` to add PSP and I2C controller drivers.
- Stage GPU drivers via `--bundle gpu` if using discrete Radeon hardware.

### Apple BootCamp Targets
- Triggered automatically when Phoenix detects Apple hardware.
- Injects BootCamp-specific storage, keyboard, and trackpad drivers.
- Optionally includes Fidera Ahsari packages when preparing Tahoe macOS 26 dual-boot support.

## Manual Overrides

```bash
phoenix-driver-inject \
  --image /isos/Windows11.iso \
  --bundle storage --bundle network \
  --additional-driver /drivers/custom/ven1234.inf \
  --output /isos/Windows11-phoenix.iso
```

- `--additional-driver` accepts folders or INF files to stage bespoke vendor payloads.
- Use `--skip-verify` in air-gapped environments, then run manual testing.

## Troubleshooting

| Symptom | Resolution |
| --- | --- |
| WinPE fails to see drive | Confirm storage bundle applied; check `setupact.log` for driver load errors. |
| Drivers missing after install | Ensure `install.wim` indexes were patched; use `--all-indexes` option for multi-SKU ISOs. |
| Slipstream takes too long | Enable caching: `phoenix-driver-inject --enable-cache` to reuse extracted WIMs. |
| Signature enforcement blocks driver | Run `bcdedit /set testsigning on` during install, then replace with signed driver. |

## Verification Checklist

- `phoenix-driver-verify` reports zero missing devices.
- Modified ISO checksum recorded in Phoenix Auto-Forge logs.
- BootCamp and Apple Silicon-specific drivers validated where applicable.
- Document changes in `/PhoenixDocs/windows_driver_notes.md` for audit compliance.
