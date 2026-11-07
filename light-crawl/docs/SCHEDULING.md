# Scheduling drift checks on Windows

`scripts/drift.ps1` runs every pack's offline verifier and writes a JSON report
under `runs/`. `scripts/schedule-drift.ps1` registers a daily Windows Task
Scheduler task for it.

## Dry run first

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\schedule-drift.ps1
```

This prints the exact registration command and **does not create a task**.

## Register

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\schedule-drift.ps1 -Register
```

Defaults:

| Setting | Default |
|---|---|
| Task name | `light-crawl-drift` |
| Time | `03:30` local |
| Working directory | repository root |
| Command | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\drift.ps1` |

Custom:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\schedule-drift.ps1 `
  -Register -TaskName "light-crawl-drift-0300" -Time "03:00"
```

Permissions: `Register-ScheduledTask` may require an elevated shell, depending
on local policy. Register it for the account that can read the repository and
the `.venv`.

## Verify

```powershell
Get-ScheduledTask -TaskName "light-crawl-drift" | Format-List TaskName,State
Get-ScheduledTaskInfo -TaskName "light-crawl-drift"
```

Run the check manually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\drift.ps1
```

Offline is the default. To also run live spiders for packs that have one:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\drift.ps1 -Online
```

`-Online` writes live item files under `runs/drift-*.jsonl`; signed/login packs
without a spider still run their local verifier.

Reports are written to `runs/drift-<timestamp>.json`; `runs/` is gitignored.

## Remove

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\schedule-drift.ps1 -Unregister
```

## Notes

- The scheduler does not repair a pack. It only reports pass/fail and stale
  timestamps.
- `site check --write` is the explicit way to update `last_verified_at`.
- Live network checks are not part of the default drift run; the default pack
  verifiers are offline. Add `-Online` when live targets are safe to hit.
- A failed task does not change a pack's timestamp.
