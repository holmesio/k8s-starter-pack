# EVAL_LOG.md — Debugging Episode Log

One entry per real debugging episode: what broke, the actual error, how it
was diagnosed (including dead ends), and the fix. These double as a
standalone record of real debugging experience, so write them specific
enough to reread cold later.

**Logging starts fresh from here going forward** — an entry gets appended
automatically after every debugging session, not only when flagged as
worth logging.

The three entries below are backfilled from the 2026-09-03 commit message
and root `PROGRESS.md`, before this log existed. Exact error text/output
wasn't captured at the time, so the symptom and diagnosis-path fields are
reconstructed at the level of detail the source material supports —
noted inline where detail is missing rather than invented.

---

## 2026-09-03 - Pod spec immutability on `kubectl apply`

**What broke:** Tried to update the running `urlshort` app Pod's `env` in
place via `kubectl apply` on an edited bare-Pod manifest.
**Error/symptom:** `kubectl apply` rejected the edit (exact error text not
captured/reconstructable from source material — root `PROGRESS.md` records
the outcome, not the literal message). Editing `metadata` (labels) on the
same Pod worked fine in place.
**Diagnosis path:** Not documented step-by-step in the source material.
What's known: the failure isolated to `spec` fields specifically, since a
`metadata`-only edit on the same object succeeded.
**Fix:** Delete and recreate the Pod with the new `env` value, rather than
editing in place.
**Concept this reinforced:** Pod `spec` is immutable after creation
(`metadata` is not) — this is a direct, felt motivation for Deployments,
which manage Pod replacement declaratively instead of requiring manual
delete/recreate.

---

## 2026-09-03 - Stale Redis Pod IP breaking `urlshort` after restart

**What broke:** `urlshort` lost its connection to Redis after the Redis Pod
was killed and recreated.
**Error/symptom:** Not captured verbatim — root `PROGRESS.md` describes
this as a "stale-Pod-IP failure" debugged down to its root cause. Consistent
with `urlshort` having been configured to talk to Redis via a Pod IP
directly, which changes on every Pod recreation.
**Diagnosis path:** Not documented step-by-step in the source material.
What's known: the failure was traced to addressing Redis by Pod IP instead
of a stable name/address.
**Fix:** Put a ClusterIP Service (`k8s/redis-service.yaml`) in front of the
Redis Pod, and point `urlshort` at the Service's DNS name
(`REDIS_HOST=redis-service`) instead of a Pod IP. Verified by killing and
recreating the Redis Pod twice afterward and confirming `urlshort` kept
working unchanged both times.
**Concept this reinforced:** Pod IPs are not stable across restarts;
Services exist to give a stable virtual IP/DNS name in front of a set of
Pods selected by label, so dependents never need to track individual Pod
IPs.

---

## 2026-09-03 - NodePort `port` vs `nodePort` field mix-up

**What broke:** External access to `urlshort` via the NodePort Service
didn't work as initially configured.
**Error/symptom:** Not captured verbatim — root `PROGRESS.md` describes
this as a "`port` vs `nodePort` mix-up" debugged down to its root cause.
Consistent with confusing the Service's cluster-internal `port` field with
the externally-reachable `nodePort` field (or omitting/misusing one of
them) in `k8s/urlshort-service.yaml`.
**Diagnosis path:** Not documented step-by-step in the source material.
**Fix:** Corrected the Service manifest's port fields so the external
`<node-ip>:<nodePort>` address routes to the Pod's `containerPort` via the
Service's `port`/`targetPort`. Verified end-to-end with the full
shorten → redirect → stats loop from outside the cluster.
**Concept this reinforced:** A NodePort Service has three distinct port
numbers in play — `targetPort` (container), `port` (cluster-internal
Service port), and `nodePort` (external, cluster-wide) — and mixing them up
is a common, easy-to-make misconfiguration.
