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
- [x] ConfigMap — 2026-09-04. `REDIS_HOST`/`REDIS_PORT` externalized from
      the Deployment's hardcoded `env` into `k8s/urlshort-configmap.yaml`,
      referenced via `configMapKeyRef`. Debugged a self-introduced typo
      (`REDIS_PORT: "6739"`) down to the fix, which surfaced the real
      concept: ConfigMap-sourced env vars resolve once at container start
      and don't live-reload — editing the ConfigMap alone didn't fix
      anything until pods were recreated. `kubectl rollout restart` named
      as the idiomatic tool for that going forward (over manual delete or
      scale-to-0-and-back, which is what was actually used this time).
- [x] Resource requests/limits — 2026-09-05. `k8s/urlshort-deployment.yaml`
      carries memory (`128Mi`/`64Mi`) and CPU (`250m`/`100m`) requests and
      limits. CPU throttling actually provoked and felt: a scratch load
      script against `/shorten` plus `/sys/fs/cgroup/cpu.stat` before/after
      showed `nr_throttled` roughly doubling and ~522ms of real throttled
      time over a ~2s run. Landed the concept that CPU limits throttle
      (process slows, keeps running) where memory limits OOMKill (process
      dies) — distinct failure modes. Memory OOMKill itself not separately
      provoked yet (open, not blocking). See
      [MEMORY.md](MEMORY.md#resource-requestslimits--cpu-throttling-demonstrated-memory-oomkill-not-yet)
      and [EVAL_LOG.md](EVAL_LOG.md).
- [x] livenessProbe / readinessProbe (and why they differ) — 2026-09-05.
      Added `/healthz` (liveness) and a new `/readyz` (readiness, real
      `redis.Redis().ping()` check) to `app/app.py`, wired into
      `k8s/urlshort-deployment.yaml`. Landed the design principle live:
      liveness triggers a disruptive restart so it stays narrow/lenient
      and never checks downstream deps; readiness gates traffic routing
      (cheap, reversible) so it's the one allowed to depend on Redis, and
      should react fast. First draft got the timing backwards (readiness
      slower than liveness) and was corrected. Felt for real via a genuine
      failure: after wiring the probes, `urlshort` pods stuck at `0/1
      Ready` — turned out to be a stale local `urlshort:local` image
      (`imagePullPolicy: IfNotPresent` reusing a cached image that
      predated `/readyz`), diagnosed via a `404` in `kubectl describe`
      events down to the `docker build` → `kind load docker-image` →
      `kubectl rollout restart` loop. Full detail across three entries in
      [EVAL_LOG.md](EVAL_LOG.md).
- [x] Deployment rollouts (rolling update on a spec change, rollback) —
      2026-09-06. Shipped a `created_at` feature as a rolling update;
      watched `maxSurge: 1` / `maxUnavailable: 0` (the 25% defaults at
      `replicas: 3`) govern the replacement, with `kubectl rollout status`
      as the done signal. Then deliberately shipped a broken `/readyz`
      (always 503): the rollout **wedged** (1 surge pod stuck `0/1`, old RS
      held at `3/3`, service never blipped, `rollout status` hangs until
      `progressDeadlineSeconds`) and `kubectl rollout undo` recovered it
      with zero downtime. Landed: readiness probe is what gates the rollout
      and makes "a bad image can't take the service down" real; the
      Deployment keeps old ReplicaSets (default `revisionHistoryLimit: 10`)
      each holding a full pod template so `undo` is just a scale-swap; and
      `rollout undo` can't restore old code here because every revision's
      template points at the mutable `urlshort:local` tag — needs immutable
      refs (`:git-sha` / digest), the same discipline GitOps pipelines
      enforce. `CHANGE-CAUSE` / `kubernetes.io/change-cause` annotation
      also covered. See [EVAL_LOG.md](EVAL_LOG.md) (two 2026-09-06 entries).

## In progress / not started

- [ ] kubectl debugging (`describe`, `logs`, events) under a real failure —
      exercised again 2026-09-06 (chased a `/shorten` 500 across replicas
      with `kubectl logs -l app=urlshort --prefix`; read a wedged rollout
      via `describe deployment` conditions + per-pod `describe` events),
      but still not run as its own dedicated focused exercise.
- [ ] Service — LoadBalancer type still open (ClusterIP and NodePort done).
- [ ] Secret — not started. Nothing in `urlshort` is actually sensitive yet
      (just `REDIS_HOST`/`REDIS_PORT`, now in a ConfigMap); would need an
      invented scenario (e.g. an admin API key) to make this real rather
      than mechanical.
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
