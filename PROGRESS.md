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
- [x] Resource requests/limits — memory (`128Mi`/`64Mi`) and CPU
      (`250m`/`100m`) set in `k8s/urlshort-deployment.yaml`. CPU throttling
      actually provoked: a load script against `/shorten` plus
      `/sys/fs/cgroup/cpu.stat` before/after showed `nr_throttled` roughly
      doubling and ~522ms of real throttled time over a ~2s run. Landed
      that CPU limits throttle (slows, keeps running) vs. memory limits
      OOMKill (dies) — distinct failure modes, felt not just described.
      Memory OOMKill itself not separately provoked yet.
- [x] livenessProbe / readinessProbe (and why they differ) — added
      `/healthz` (liveness) and `/readyz` (readiness, real Redis `.ping()`)
      to the app, wired into the Deployment. Landed why they're not
      interchangeable: liveness restarts (disruptive, so stays narrow —
      never checks downstream deps) vs. readiness gates traffic (cheap,
      reversible, so it's the one allowed to depend on Redis). Felt for
      real: pods stuck `0/1 Ready` after wiring probes, root-caused via a
      `404` in `kubectl describe` events to a stale local `urlshort:local`
      image (`imagePullPolicy: IfNotPresent` never re-pulling on its own)
      — fixed via rebuild → `kind load docker-image` → `rollout restart`.

## Concepts — still open

- [ ] kubectl debugging (`describe`, `logs`, events) under a real failure —
      touched on lightly (read a 500 back to a connection-refused in
      `logs`; also used `describe`/`exec env` to chase the ConfigMap typo
      below; also the stale-image 404-on-readiness episode), not yet
      forced by an actual crash/misconfig as its own focused exercise
- [ ] Deployment rollouts specifically (rolling update on a spec change,
      rollback) — replica self-healing done, rollout behavior still open
- [ ] Service — ClusterIP and NodePort both done; LoadBalancer still open
- [ ] Secret
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
- 2026-09-05 — added CPU requests/limits (`250m`/`100m`) alongside the
  existing memory ones. Built a scratch `xargs`+`curl` load script and used
  `kubectl exec ... cat /sys/fs/cgroup/cpu.stat` before/after as ground
  truth (no `metrics-server` in this cluster) to actually provoke and
  observe CPU throttling — `nr_throttled` roughly doubled over a ~2s run.
  Landed CPU-limit-throttles vs. memory-limit-OOMKills as distinct failure
  modes. User flagged wanting a general CPU-scheduling/latency refresher
  (self-directed). Then added `/healthz`/`/readyz` and wired liveness/
  readiness probes into the Deployment — caught real bugs in the first
  `/readyz` draft in review (status code never actually set, ICMP ping
  instead of a real Redis check, new dependency missing from
  `requirements.txt`) and a probe-timing mistake (readiness slower to
  react than liveness, backwards from the cost asymmetry between a
  restart and a rotation-pull). After wiring, pods stuck `0/1 Ready`;
  diagnosed a `404` (not a connection error) down to a stale local
  `urlshort:local` image predating `/readyz` — `kind`'s node never re-pulls
  a non-`:latest` tag on its own. Fixed via `docker build` → `kind load
  docker-image` → `kubectl rollout restart`. Resource
  requests/limits + health probes phase now complete. Next planned: pick
  from kubectl-debugging-as-its-own-exercise, Deployment rollouts, Secret,
  or LoadBalancer Service.
