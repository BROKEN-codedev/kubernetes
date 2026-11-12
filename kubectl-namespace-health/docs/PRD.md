# Product requirements

Project: **Build kubectl Namespace Health Plugin for Kubernetes (Simulated)**.
Student: Ayaan Jindal, B.Tech in Applied AI, Semester 1, Polaris School of Technology.
Mentor: Abhishek Jagtap. Prepared/implemented: 11 November 2026.

## Problem and users

Namespace triage requires reading separate pod and event output. Students, developers and platform engineers benefit from one concise, explainable snapshot of readiness, restarts and recent warnings.

## Required behavior

Select a namespace from simulated PodList/EventList JSON. Validate the input. Count ready/not-ready/completed pods, cumulative ordinary/init restarts and recent Warning records. Return a text or JSON report with reasons and a documented exit code. Support fixed-clock healthy/degraded/critical/empty examples and custom fixtures. Run without a cluster or runtime dependency.

## Acceptance

- The four scenarios return 0, 1, 2 and 3 respectively.
- Namespace data never leaks into another namespace's counts.
- Ready conditions, completed pods, thresholds, timezones and boundary timestamps are handled as documented.
- Invalid data is not silently healthy; input errors are distinguishable from valid empty reports.
- The installed command works outside the source tree and discovers its bundled fixtures.
- Meaningful unit/CLI/installation checks pass. Formal statement coverage target: >=85%, measured with coverage.py where available. The separate stdlib trace measure must be named accurately.
- README, design, test table, real validation evidence, CI configuration and a demo script exist.

## Limits

This is not a live monitoring system, Kubernetes core patch or root-cause detector. Cumulative restart counts do not establish a time-based rate. Local tests do not establish a successful remote CI run. Repository publishing, a real demo recording and mentor acceptance remain external/manual steps. There is no evidence that coding was completed during the earlier requested logbook period.
