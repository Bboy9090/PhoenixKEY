# What Each Tool Does

This catalogue maps every Phoenix Key payload to its mission outcome so technicians can rapidly pick the correct utility on-sit
e.

## Windows Arsenal

| Tool | Category | Primary Outcome |
| --- | --- | --- |
| Windows 7–11 Official ISOs | Installation | Full reinstall and repair of legacy and modern Windows machines with Phoenix Smart Drivers. |
| Phoenix PE | Recovery | Custom WinPE image with Smart Drivers agent, BootCamp deployer, and malware triage scripts. |
| Unattended Templates | Automation | Pre-authored answer files covering clean install, OEM refresh, and forensic capture workflows. |

## Linux Power Deck

| Tool | Category | Primary Outcome |
| --- | --- | --- |
| Ubuntu LTS | Installation | Standard recovery and general-purpose repair environment. |
| Fedora | Installation | Enterprise workstation deployment testing and secure boot validation. |
| Kali | Diagnostics | Security auditing, credential testing, and forensic imaging. |
| Alpine | Lightweight | Minimal rescue shell for resource-constrained hardware. |
| Puppy Linux | Lightweight | RAM-resident desktop for legacy x86 machines. |
| Lubuntu | Lightweight | GUI-driven repair for low-memory systems. |
| SystemRescue | Specialized | Phoenix base OS housing filesystem repair, Btrfs/ZFS tooling, and network utilities. |
| GParted Live | Specialized | Dedicated partition management and disk cloning tasks. |

## macOS Integration Stack

| Tool | Category | Primary Outcome |
| --- | --- | --- |
| Phoenix Mac Tools | Workflow | Guided scripts for NVRAM/SMC reset, EFI cleaning, and Tahoe macOS 26 recovery triggers. |
| Fidera Ahsari Packs | Compatibility | Apple Silicon driver, firmware, and shim provisioning for Tahoe macOS 26 workflows. |
| BootCamp Driver Cache | Deployment | Auto-installers for Windows-on-Mac deployments with hardware detection. |

## Diagnostics & Recovery

| Tool | Category | Primary Outcome |
| --- | --- | --- |
| Clonezilla / Macrium Reflect | Imaging | Disk imaging, bare-metal restore, and delta backups. |
| TestDisk / PhotoRec | Data Recovery | Partition rebuild and carved file recovery. |
| MemTest86 | Hardware | Memory diagnostics with logging for Phoenix System Monitor. |
| CPU/GPU Stress Suite | Hardware | Burn-in tests to confirm system stability prior to redeployment. |
| SMART Console | Hardware | Drive health scoring with exportable reports. |
| BIOS/OEM Toolkits | Emergency | Firmware backup, cross-flash validation, and OEM recovery script runners. |
| Phoenix "Save My Data" | Emergency | Guided triage that copies key user data profiles to safe storage. |
| AV Rescue Disks | Security | Offline malware scanning, rootkit removal, and offline signature updates. |

## Phoenix Signature Services

| Service | Description |
| --- | --- |
| Hybrid Mode Loader | Determines optimal ISO and boot parameters based on detected firmware, GPU, and storage. |
| Phoenix Smart Drivers | Aggregates vendor drivers, slipstreams them into Windows PE, and validates post-install telemetry. |
| Phoenix Thermal-Aware Flashing | Monitors USB temperature sensors during ISO writes to protect flash integrity. |
| Phoenix Key Web GUI | Presents dashboards, documentation, and workflow automation accessible via localhost tether. |
| Offline License Verifier | Confirms entitlements before launching restricted utilities. |
