# Phoenix Emergency Manual

This manual governs catastrophic incidents when standard workflows fail. Escalate only after consulting relevant playbooks.

## Incident Classification

| Level | Description | Response Window |
| --- | --- | --- |
| Level 1 – Critical Data at Risk | Single-disk failure, customer data recoverable | Respond within 30 minutes |
| Level 2 – Multi-System Outage | Multiple devices impacted, potential business downtime | Respond within 15 minutes |
| Level 3 – Device Non-Responsive | Firmware corruption, DFU/ISP required | Immediate response with senior technician |

## Rapid Response Flow

1. **Stabilize Power** – Connect known-good PSU/UPS to target.
2. **Isolate Media** – Physically remove storage if risk of further damage; connect via Phoenix write-blocker.
3. **Launch Phoenix Emergency Console** – Boot Phoenix Key → *Emergency Kits* → `phoenix-emergency`.
4. **Select Incident Type** – Options: *Data Rescue*, *Firmware Recovery*, *Malware Containment*, *Board-Level Diagnostics*.
5. **Follow Automated Checklist** – Console guides through actions, logging all steps.

## Data Rescue Protocol

- Use `phoenix-save-data --imaging` for sector-by-sector clone (ddrescue integration).
- Hash outputs immediately (`sha256sum`) and record in `/PhoenixLogs/incidents/<ticket>/hashes.txt`.
- Do not mount suspect drives read-write until clone verified.

## Firmware Recovery Protocol

- For BIOS/UEFI: Run `phoenix-bios-dump` to backup existing firmware, then flash vendor image from encrypted partition.
- For Apple Silicon DFU: Execute `phoenix-dfu-orchestrator` (requires second Mac) and apply Fidera Ahsari payload if Tahoe 26.
- For embedded controllers (EC): Consult compatibility notes and use vendor-specific flashing tools stored under `Emergency/EC`.

## Malware Containment Protocol

- Boot into Phoenix PE or Linux secure mode.
- Disconnect network (unless running offline AV updates).
- Scan with two distinct AV rescue disks; export reports to incident log.
- If ransomware detected, run `phoenix-ransomware-kit` to capture memory snapshot and ransom note metadata.

## Board-Level Diagnostics

- Deploy `phoenix-board-scan` to inspect power rails, fan curves, and component thermals via external sensors.
- Document findings; escalate to OEM repair if physical faults detected.

## Communication & Documentation

- Maintain incident log in Phoenix Web GUI with timestamped entries.
- Export HTML documentation along with tool outputs for customer review.
- Store artifacts in encrypted partition; sync with BootForge central repository when back online.

## Post-Incident Review

- Conduct debrief, update PhoenixDocs guides with new learnings.
- Tag incident in Phoenix Auto-Forge to trigger follow-up improvements.
- Archive final report to `/PhoenixDocs/incidents/<ticket>/report.pdf`.
