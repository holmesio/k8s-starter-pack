# Progress

Tracking two things: what's actually deployed/running, and which concepts
have gotten genuine first-exposure treatment (per [CLAUDE.md](CLAUDE.md))
vs. still open. Update as sessions happen, not retroactively.

## The service

URL shortener with click analytics — FastAPI + Redis, `/metrics` exposed for
Prometheus. Code in [app/](app/). Image `urlshort:local`, built and loaded
into a local `kind` cluster (`kind-k8s-starter`). `urlshort` is now a
Deployment (3 replicas, `k8s/urlshort-deployment.yaml` — renamed from `pod.yaml`
to match its actual contents); Redis is still a bare Pod
(`k8s/redis-pod.yaml`), wired to `urlshort` via `k8s/redis-service.yaml`.
`urlshort` is now also exposed via a NodePort Service
(`k8s/urlshort-service.yaml`), verified end-to-end (shorten → redirect →
stats) against `<node-ip>:30813` — no more port-forward needed.
`REDIS_HOST`/`REDIS_PORT` are externalized into a ConfigMap
(`k8s/urlshort-configmap.yaml`), referenced from the Deployment via
`configMapKeyRef`.

## Concepts — first exposure done

- [x] Pod — bare `k8s/pod.yaml` running the app container, applied and
      verified with `kubectl get pods` / port-forward.
- [x] Pod spec immutability — `kubectl apply` rejected an in-place edit to
      the running app Pod's `env`; had to delete/recreate. Metadata
      (labels) turned out mutable in place, unlike `spec`. Directly
      motivates Deployments, next.
- [x] Labels/selectors — labeled `redis-pod.yaml`, used by the Service's
      `selector` to find it.
- [x] Service (ClusterIP) — built `redis-service.yaml` after predicting
      (correctly) that a raw Pod IP would break on restart. Proved it by
      killing/recreating the Redis Pod twice and confirming the app kept
      working unchanged, addressing Redis via the Service's stable
      ClusterIP/DNS name instead of a Pod IP.
- [x] Cluster DNS for Services — `urlshort` reaches Redis via
      `REDIS_HOST=redis-service`, no IP involved.
- [x] Deployment / self-healing — converted `urlshort` from bare Pod to a
      3-replica Deployment; deleted one Pod directly and watched the
      ReplicaSet recreate it unprompted, no manual intervention.
- [x] ConfigMap — externalized `REDIS_HOST`/`REDIS_PORT` out of the
      Deployment's hardcoded `env` into `k8s/urlshort-configmap.yaml`, wired
      via `configMapKeyRef`. Introduced a typo (`REDIS_PORT: "6739"`)
      debugging it surfaced the key follow-up concept: env vars sourced
      from a ConfigMap are resolved once at container start, not
      live-reloaded — editing the ConfigMap alone didn't fix anything
      until pods were recreated (`kubectl rollout restart` is the
      idiomatic way, over manual delete or scale-to-0-and-back).

## Concepts — still open

- [ ] kubectl debugging (`describe`, `logs`, events) under a real failure —
      touched on lightly (read a 500 back to a connection-refused in
      `logs`; also used `describe`/`exec env` to chase the ConfigMap typo
      below), not yet forced by an actual crash/misconfig as its own
      focused exercise
- [ ] Deployment rollouts specifically (rolling update on a spec change,
      rollback) — replica self-healing done, rollout behavior still open
- [ ] Service — ClusterIP and NodePort both done; LoadBalancer still open
- [ ] Secret
- [ ] Resource requests/limits
- [ ] livenessProbe / readinessProbe (and why they differ)
- [ ] In-cluster DNS / service discovery
- [ ] Prometheus/Grafana in-cluster observability
- [ ] Helm (templating, values, chart structure)
- [ ] ArgoCD (Application manifest, sync policy, drift detection)

## Later, if wanted (not front-loaded)

- [ ] Kustomize
- [ ] Ingress controllers
- [ ] NetworkPolicies
- [ ] RBAC
- [ ] Autoscaling (HPA)
- [ ] Multi-node cluster concerns

## Session log

- 2026-09-03 — repo initialized, CLAUDE.md and PROGRESS.md written.
- 2026-09-03 — service chosen (urlshort: FastAPI + Redis) and built; local
  `kind` cluster up. Walked bare Pod → hit Pod-spec immutability firsthand →
  Redis as its own Pod + ClusterIP Service (debugged a stale-Pod-IP failure
  down to it) → `urlshort` converted to a 3-replica Deployment (watched
  self-healing after a manual `kubectl delete pod`) → `urlshort` exposed via
  NodePort Service (debugged a `port` vs `nodePort` mix-up down to it).
  Full shorten → redirect → stats loop verified end-to-end externally.
- 2026-09-04 — externalized `REDIS_HOST`/`REDIS_PORT` into a ConfigMap
  (`k8s/urlshort-configmap.yaml`), wired via `configMapKeyRef`; renamed
  `k8s/pod.yaml` → `k8s/urlshort-deployment.yaml` to match its actual contents.
  Introduced a typo (`REDIS_PORT: "6739"`) doing it, debugged down via
  `kubectl exec ... env` compared against Kubernetes' auto-injected
  `<SVC>_SERVICE_PORT` vars — landed the concept that ConfigMap-sourced env
  vars only resolve at container start, not live. Next planned: Secret (once
  there's an actually-sensitive value to justify it) or resource
  requests/limits + health probes.
