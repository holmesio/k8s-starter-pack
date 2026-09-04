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

## Filename/content drift: `k8s/pod.yaml` now holds a Deployment

**Note, not a decision:** `k8s/pod.yaml` was edited in place to become a
`Deployment` (`urlshort-deployment`, 3 replicas) rather than being
renamed or replaced by a new file. The filename hasn't been updated to
match. Flagging so a future session doesn't assume the file's name
describes its current contents.
**Confidence:** Confirmed (read directly from the file).

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
