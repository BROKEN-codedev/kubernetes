# Admission webhook readiness investigation

This fork is used for an OJT open-source project investigating Kubernetes issue [138465](https://github.com/kubernetes/kubernetes/issues/138465), which reports webhook requests reaching unready or terminating Pods.

## Current status

Repository setup is complete: the upstream repository has been forked and a dedicated issue branch has been created. This initial commit records the investigation scope. No reproduction, regression test, bug fix or upstream pull request has been completed.

## Planned work

1. Review the issue discussion and related upstream changes, including pull requests 138496 and 139237.
2. Prepare a controlled validating-webhook experiment and record the Kubernetes version and routing settings.
3. Correlate Pod readiness, EndpointSlice state and webhook request logs, distinguishing new connections from reused connections.
4. Add meaningful regression coverage for any confirmed remaining gap and propose a focused change when supported by the evidence.
5. Record test results, limitations and reproduction instructions.

## Contribution notes

This is fork-only coursework documentation and should be excluded from any upstream code contribution. AI assistance was used to prepare this note and the repository setup. The human author is responsible for reviewing submitted changes and following [CONTRIBUTING.md](CONTRIBUTING.md).
