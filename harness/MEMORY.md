# MEMORY.md — Decisions & Context

Accumulating log of real decisions made in this repo, why, and what got
tried and abandoned. Append new entries at the top (most recent first).
Each entry: **Decision**, **Why**, **Tried/abandoned** (if applicable),
**Confidence** (confirmed from source vs. inferred).

---

## Deployment rollouts covered; mutable `urlshort:local` tag is now a known landmine

**Decision / what landed (2026-09-06):** Deployment rollouts done as a
concept — rolling-update strategy (`maxSurge`/`maxUnavailable`, 25% defaults
→ `1`/`0` at `replicas: 3`), `kubectl rollout status`/`history`/`undo`,
`kubernetes.io/change-cause`, `progressDeadlineSeconds`, and the safety
property that a readiness probe makes a bad rollout *wedge* (old pods keep
serving) instead of taking the service down. A deliberately-broken `/readyz`
(always 503) was shipped to feel the wedge, then recovered with `rollout
undo`. Full episodes in [EVAL_LOG.md](EVAL_LOG.md).
**Recurring theme, now explicit:** the single mutable image tag
`urlshort:local` (rebuilt + `kind load`ed in place every change) has now
bitten twice — the 2026-09-05 stale-image `/readyz` 404, and 2026-09-06's
"`rollout undo` restores the pod template but every revision's template
names the same moving tag, so it can't actually restore old code." The
app is not yet on immutable tags. Worth doing at some point (`:git-sha`,
digest) — it's also the exact mechanism GitOps/ArgoCD relies on, so it may
land naturally when Helm/ArgoCD come up rather than as its own task. Not
currently blocking anything.
**Cluster note:** after the session the good `created_at` image was rebuilt
and reloaded so the node's `urlshort:local` cache matches the running code
(the broken `/readyz` build had overwritten it). Running pods were left
alone. `app/app.py` in the working tree has the `created_at` feature
(uncommitted as of session end) and the *good* `/readyz`.
**Confidence:** Confirmed (this session).

## Resource requests/limits — CPU throttling demonstrated, memory OOMKill not yet

**Decision:** `k8s/urlshort-deployment.yaml` now carries both memory
(`limits.memory: 128Mi` / `requests.memory: 64Mi`, added earlier same
session) and CPU (`limits.cpu: 250m` / `requests.cpu: 100m`) resources.
**Why:** Direct next step per `PROGRESS.md`. CPU limits were picked over a
larger value specifically so throttling would be reachable with a modest
load test, since CPU limits fail differently from memory limits (throttled
via the kernel's CFS bandwidth controller, not OOMKilled) and that
difference needed to be felt, not just described.
**Debugging/demo episode:** No `metrics-server` in this `kind` cluster
(`kubectl top pod` unavailable) and no load-test binary installed, so used
a scratch `xargs -P 30` + `curl` script hammering `POST /shorten` through
the NodePort Service, and read `/sys/fs/cgroup/cpu.stat` inside a pod
before/after via `kubectl exec` as ground truth. `nr_throttled` roughly
doubled and `throttled_usec` climbed ~522ms over a ~2s run — real,
measurable throttling. See [EVAL_LOG.md](EVAL_LOG.md) for the full episode.
**Concept landed:** CPU limit → throttled (process keeps running, slower);
memory limit → OOMKilled (process dies). Client-observed latency stayed
modest (30-80ms) despite clear throttling at the cgroup level — partly
because the NodePort Service spread the 1000-request load across all 3
replicas (kube-proxy round-robin), and partly because this app's per-request
work is mostly I/O-bound (waiting on the Redis round-trip, which doesn't
count against the CPU quota) rather than CPU-bound — throttling can only
delay the small CPU-bound slice of each request.
**Open thread:** The user flagged wanting a general refresher on CPU
scheduling / latency fundamentals (why I/O-wait doesn't count against a
CPU quota, why throttling doesn't show up 1:1 in latency) — self-directed,
not something to re-teach unprompted next session, but worth being aware
of if CPU-bound explanations come up again (e.g. HPA later). Also: an
actual memory OOMKill has still not been provoked directly (only inferred
from the limit being set) — worth doing if a natural scenario arises,
though not currently treated as blocking the resource-limits concept being
considered landed.
**Confidence:** Confirmed (this session).

## `kind` as the local cluster tool

**Decision:** Use `kind` for the local cluster, not `minikube`.
**Why:** No `minikube` installed in this environment; `kind` is what's
available (per root `CLAUDE.md`'s environment note). Not evidence of a
deliberate comparison between the two — it's an environment constraint.
**Confidence:** Confirmed (stated directly in root `CLAUDE.md`).

## urlshort (FastAPI + Redis) chosen as the service to deploy

**Decision:** Deploy a small FastAPI + Redis URL shortener with click
analytics, rather than a toy single-container app.
**Why:** Needed something with a real datastore dependency, config
surface, and metrics endpoint so Kubernetes concepts (Services, ConfigMaps,
observability) have something genuine to attach to, per the root README's
stated intent ("Kubernetes fluency, not Python fluency").
**Confidence:** Confirmed (root `README.md` states this reasoning
directly).

## Redis deployed as a bare Pod, not a Deployment (so far)

**Decision:** Redis currently runs as a standalone Pod (`k8s/redis-pod.yaml`),
while `urlshort` was converted to a Deployment.
**Why:** Inferred — this looks like a deliberate sequencing choice: keep
Redis as a bare Pod so the Pod-spec-immutability and stale-Pod-IP failure
modes stayed visible and had to be solved with a Service, before
introducing Deployments on the app tier. Not explicitly stated as
intentional anywhere in the repo, so treat this as a working theory, not
confirmed fact — worth confirming with the user if it matters later (e.g.
before converting Redis to a Deployment/StatefulSet).
**Confidence:** Inferred.

## NodePort chosen to expose `urlshort` externally (not LoadBalancer)

**Decision:** `urlshort-service.yaml` uses `type: NodePort`.
**Why:** Inferred — on a local `kind` cluster there's no cloud load
balancer controller, so `LoadBalancer` wouldn't provision a real external
IP without extra setup (e.g. `cloud-provider-kind` or MetalLB). NodePort is
the direct, dependency-free way to reach a Service from outside a local
cluster. LoadBalancer is explicitly still on the open concept list
([PROGRESS.md](PROGRESS.md)), suggesting this was a "simplest thing that
works locally" choice rather than a final decision on Service types.
**Confidence:** Inferred.

## Filename/content drift: `k8s/pod.yaml` now holds a Deployment (resolved)

**Note, historical:** `k8s/pod.yaml` was edited in place to become a
`Deployment` (`urlshort-deployment`, 3 replicas) without being renamed.
**Resolved 2026-09-04:** file renamed to `k8s/urlshort-deployment.yaml` when the
ConfigMap work touched it anyway. No longer a live discrepancy — kept here
only as a record that the rename happened and why the name changed.
**Confidence:** Confirmed (read directly from the file).

## ConfigMap introduced for `REDIS_HOST`/`REDIS_PORT`

**Decision:** Externalized `REDIS_HOST`/`REDIS_PORT` from the Deployment's
hardcoded `env` into `k8s/urlshort-configmap.yaml`, referenced via
`configMapKeyRef`.
**Why:** Direct next step per `PROGRESS.md` — keep config separate from the
workload spec so it isn't tied to the Deployment's lifecycle.
**Debugging episode:** Introduced a typo, `REDIS_PORT: "6739"` instead of
`"6379"`. `kubectl describe pod` doesn't resolve `configMapKeyRef` values
(only shows the reference); the fix came from `kubectl exec ... -- env`
compared against Kubernetes' auto-injected `<SVCNAME>_SERVICE_PORT` env
vars (which reflect the real Service, not the ConfigMap) as a ground-truth
check. See [EVAL_LOG.md](EVAL_LOG.md) for the full episode.
**Concept landed:** ConfigMap-sourced env vars resolve once at container
start and are never live-reloaded. Editing the ConfigMap object alone did
nothing to already-running pods — they had to be recreated (this session
did it via manual delete; `kubectl rollout restart deployment/...` was
named as the more idiomatic tool going forward, since it respects the
rolling-update strategy instead of dropping to zero available pods).
**Confidence:** Confirmed (this session).

---

## Analogies to prior work that have already landed

None yet. Root `CLAUDE.md` lists candidate parallels to draw on (Secrets ~
Terraform/AWS Secrets Manager, ArgoCD drift detection ~ EventBridge
drift-prevention, in-cluster observability ~ existing Grafana/Prometheus
fluency), but none of these have actually come up in a session yet per the
git history — add an entry here only once one is actually used and lands.

---

<!-- Template for new entries:

## <short title>

**Decision:** what was decided
**Why:** the reasoning
**Tried/abandoned:** what was tried first and didn't work, if anything
**Confidence:** confirmed (from user/commit/file) vs. inferred

-->
