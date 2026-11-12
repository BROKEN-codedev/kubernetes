# Test cases

| Area | Checked behavior |
|---|---|
| Baseline | Literal pod/counter expectations and explicit simulation clock |
| Readiness | Running is insufficient; Ready False, missing condition and deletion are unready |
| Critical | Failed, waiting failure reasons and zero ready evaluated pods |
| Completion | Succeeded pods excluded; completed-only data is UNKNOWN |
| Restarts | Ordinary/init counts; per-pod threshold boundaries; zero threshold |
| Isolation | Other-namespace pods/events excluded; undeclared namespace is an input error |
| Events | Inclusive bounds; old/future exclusion; offsets; timestamp precedence and fallback |
| Missing times | Unusable warning records preserved; UNKNOWN overrides degradation, CRITICAL overrides UNKNOWN; unrelated optional timestamps ignored |
| Validation | Required shapes, malformed arrays, phase, conditions and restart counts |
| CLI | Flags, exclusivity, JSON/errors, help/version and real process exits; text/JSON counts and reasons agree |
| Input boundaries | Oversized file, directory, deep JSON, nonstandard numeric constants, literal constant-name strings, oversized integers |
| Structural boundaries | Duplicate namespace/pod/container identities, boolean condition status, wrong list kind, nonstring event messages |
| Time range | Excessive minute windows and subtraction before year 1 rejected |
| Packaging | Build wheel, install offline in fresh venv, all scenarios from another cwd |

Tests assert behavior and literal expected counts, rather than matching only saved output. `docs/VALIDATION.md` and `docs/evidence/` contain actual executed results.
