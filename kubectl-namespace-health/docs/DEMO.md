# 2-3 minute demo

Run these commands from the project root with Python 3.11+. Say that the data is simulated and that the reference clock is fixed.

**0:00-0:25:** Explain the problem: readiness, restart and event information is normally spread across separate output. This tool gives a single namespace snapshot with reasons.

**0:25-1:15:** Run each separately:

```bash
python3 -m ns_health --scenario healthy
python3 -m ns_health --scenario degraded
python3 -m ns_health --scenario critical
python3 -m ns_health --scenario empty
```

Explain the status/reasons. Expected exits are 0/1/2/3. On macOS/zsh, `echo $?` immediately after a command displays that command's exit code. A nonzero health result is intentional.

**1:15-1:40:** Show `python3 -m ns_health --scenario degraded --json`. Explain namespace isolation, cumulative restarts and the fixed event-time window.

**1:40–2:10** Run `python3 -m unittest discover -s tests -q`. Show the measured results in `docs/VALIDATION.md` and explain how the packaging test exercises the installed wheel.

**2:10-2:40:** Explain limitations: no live cluster, thresholds are application policies, no automatic repair. State which external checks remain pending. Demonstrate kubectl invocation only if installed and configured locally.

## Viva practice

1. **Running versus Ready?** Running describes lifecycle; the Pod Ready condition indicates readiness. This tool requires both plus no deletion timestamp.
2. **Why are restarts not a rate?** restartCount is cumulative status data; a single snapshot does not show when restarts happened.
3. **Why a fixed clock?** Bundled event examples remain deterministic and visibly simulated instead of becoming stale or pretending to be live.
4. **Why exit codes?** Scripts can react to health without parsing prose. Usage failures are distinguished by stderr/usage output.
5. **Why simulation?** It demonstrates parsing, aggregation, policy and tests without access to a cluster; live behavior needs separate integration validation.

This file is a script for a future recording, not evidence that a video exists.

Use `RUN_AND_TEST.md` for the full installation, test and formal coverage commands. The final audit fixed acceptance of NaN/Infinity in custom JSON fixtures; this does not change the four demonstration statuses.
