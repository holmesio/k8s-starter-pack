# MEMORY.md — Decisions & Context

Accumulating log of real decisions made in this repo, why, and what got
tried and abandoned. Append new entries at the top (most recent first).
Each entry: **Decision**, **Why**, **Tried/abandoned** (if applicable),
**Confidence** (confirmed from source vs. inferred).

---

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
