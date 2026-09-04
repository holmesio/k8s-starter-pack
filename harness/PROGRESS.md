# PROGRESS.md (harness) — Concept Tracker

This is the concept-completion checklist referenced by
[PROJECT.md](PROJECT.md)'s ground rules — check this before proposing what
to work on next. It tracks the concept sequence only. For the narrative
session log and exact commands/manifests used, the root
[../PROGRESS.md](../PROGRESS.md) remains the source of truth; this file
summarizes status without re-deriving that history.

## Done

- [x] Pod — 2026-09-03. Bare `k8s/pod.yaml` (original bare-Pod version, since
      converted) running the app container, applied and verified with
      `kubectl get pods` / port-forward.
- [x] Pod spec immutability — 2026-09-03. `kubectl apply` rejected an
      in-place edit to the running app Pod's `env`; required delete/recreate.
      Metadata (labels) turned out mutable in place, unlike `spec`. This is
      what directly motivated moving to a Deployment.
- [x] Labels/selectors — 2026-09-03. Labeled `redis-pod.yaml`; consumed by
      the Service's `selector` to find it.
- [x] Service (ClusterIP) — 2026-09-03. Built `redis-service.yaml` after
      predicting (correctly) that a raw Pod IP would break on restart.
      Verified by killing/recreating the Redis Pod twice and confirming the
      app kept working unchanged via the Service's stable ClusterIP/DNS name.
- [x] Cluster DNS for Services — 2026-09-03. `urlshort` reaches Redis via
      `REDIS_HOST=redis-service`, no IP involved.
- [x] Deployment / self-healing — 2026-09-03. Converted `urlshort` from bare
      Pod to a 3-replica Deployment; deleted one Pod directly and watched
      the ReplicaSet recreate it unprompted.
- [x] Service (NodePort) — 2026-09-03. `urlshort` exposed externally via
      `k8s/urlshort-service.yaml`; full shorten → redirect → stats loop
      verified end-to-end against `<node-ip>:<nodePort>`.

## In progress / not started

- [ ] kubectl debugging (`describe`, `logs`, events) under a real failure —
      touched lightly (read a 500 back to a connection-refused in `logs`),
      not yet forced by an actual crash/misconfig as its own focused
      exercise.
- [ ] Deployment rollouts specifically (rolling update on a spec change,
      rollback) — replica self-healing done, rollout behavior still open.
- [ ] Service — LoadBalancer type still open (ClusterIP and NodePort done).
- [ ] ConfigMap — not started. Planned next: externalize `REDIS_HOST` (and
      similar) out of the Deployment spec's hardcoded `env`.
- [ ] Secret — not started.
- [ ] Resource requests/limits — not started.
- [ ] livenessProbe / readinessProbe (and why they differ) — not started.
- [ ] In-cluster DNS / service discovery beyond the single Service case
      already covered — not started (multi-service networking, deliberately
      broken config to debug).
- [ ] Prometheus/Grafana in-cluster observability — not started. App already
      exposes `/metrics`; nothing scrapes it yet.
- [ ] Helm (templating, values, chart structure) — not started.
- [ ] ArgoCD (Application manifest, sync policy, drift detection) — not
      started.

## Later, if wanted (not front-loaded)

- [ ] Kustomize
- [ ] Ingress controllers
- [ ] NetworkPolicies
- [ ] RBAC
- [ ] Autoscaling (HPA)
- [ ] Multi-node cluster concerns
