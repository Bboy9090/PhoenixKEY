# PhoenixDocs Knowledge Base

The Phoenix Key ships with a fully offline documentation hub designed for field technicians who need clear guidance without an
internet connection. Each guide in this collection maps directly to the operational flows defined in the [Legendary Forge Bluep
rint](../phoenix_key_legendary_blueprint.md) and can be rendered as HTML for the Phoenix Web GUI or viewed locally as Markdown.

## How to Use This Library

1. **Browse by Scenario** – The left navigation categorises guides by deployment or recovery objective.
2. **Follow the Playbooks** – Every document contains checklist-driven tasks and escalation paths.
3. **Capture Notes** – Use the Phoenix Web GUI to append field notes; the manifest keeps metadata synchronised.
4. **Sync Regularly** – Run `bootforge build-phoenix-docs` after updating Markdown so the offline HTML stays current.

## Document Roster

| Guide | Purpose |
| --- | --- |
| [What Each Tool Does](tool_reference.md) | Feature-level overview of bundled utilities and ISOs. |
| [Compatibility Notes](compatibility_notes.md) | Platform-specific gotchas, firmware requirements, and hardware quirks. |
| [Mac Repair Guide](mac_repair_guide.md) | Phoenix Mac Tools workflow for Intel, Apple Silicon, and Tahoe macOS 26 recovery. |
| [BootCamp Troubleshooting](bootcamp_troubleshooting.md) | Rapid response checklists for Windows-on-Mac deployments. |
| [Windows Driver Inject Guide](windows_driver_inject.md) | Instructions for leveraging Phoenix Smart Drivers in Windows PE. |
| [Linux Rescue Playbook](linux_rescue_playbook.md) | Scenario-based Linux recovery operations and kernel tuning presets. |
| [Phoenix Emergency Manual](phoenix_emergency_manual.md) | Triage procedures for catastrophic failures and last-resort options. |

## Rendering Offline HTML

Run the Phoenix Docs builder to convert Markdown to themed HTML artefacts suitable for the Phoenix Web GUI:

```bash
python main.py build-phoenix-docs --output dist/phoenix_docs_html
```

The builder writes a manifest (`phoenix_docs_manifest.json`) describing every guide so the GUI can surface context-sensitive hel
p.
