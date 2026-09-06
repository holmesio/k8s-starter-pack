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

---

## 2026-09-04 - ConfigMap typo (`REDIS_PORT: "6739"`) causing connection refused

**What broke:** After externalizing `REDIS_HOST`/`REDIS_PORT` into a new
`k8s/urlshort-configmap.yaml` ConfigMap and wiring the Deployment
(`k8s/urlshort-deployment.yaml`) to pull both via `configMapKeyRef`, curling the
app through `kubectl port-forward deployment/urlshort-deployment 8000:8000`
returned connection refused / hung.
**Error/symptom:** Pods were `Running`/`Ready`; `kubectl logs` showed no
clear error. `kubectl describe pod` showed the env entries only as
unresolved references (`<set to the key 'REDIS_PORT' of config map
'urlshort-config'> Optional: false`) — describe does not resolve
`configMapKeyRef` to its actual value, so it looked "fine" at a glance.
**Diagnosis path:** `describe` being a dead end here was itself the key
lesson. Moved to `kubectl exec <pod> -- env | grep REDIS`, which printed
both the ConfigMap-sourced vars (`REDIS_PORT=6739`) and Kubernetes'
auto-injected Service-discovery vars for the same Redis Service
(`REDIS_SERVICE_SERVICE_PORT=6379`, `REDIS_SERVICE_PORT_6379_TCP_PORT=6379`).
Comparing the two side by side surfaced the mismatch — `6739` vs `6379` —
i.e. a fat-fingered ConfigMap value, not a wiring problem.
**Fix:** Corrected `REDIS_PORT` to `"6379"` in `k8s/urlshort-configmap.yaml`
and reapplied. Existing pods did *not* pick up the new value on their own —
editing/reapplying the ConfigMap object doesn't touch already-running
containers. Pods were deleted and recreated by the ReplicaSet to pick up
the corrected env var.
**Concept this reinforced:** (1) `kubectl describe pod` shows the
*reference* for `valueFrom`/`configMapKeyRef` env vars, never the resolved
value — `exec ... env` (or `describe configmap`) is the way to see ground
truth. (2) ConfigMap-sourced env vars are resolved once, at container
start, and are never live-reloaded; changing the ConfigMap requires forcing
pod recreation to take effect (`kubectl rollout restart deployment/...` is
the idiomatic way — respects the rolling-update strategy — versus the
manual delete-and-recreate used this time, which briefly drops all
replicas). (3) Kubernetes auto-injects `<SVCNAME>_SERVICE_HOST`/`_PORT`
(and related `_TCP_*`) env vars into every pod for every Service that
existed at pod start — a second, legacy service-discovery mechanism
alongside cluster DNS, and incidentally useful here as a ground-truth
value to diff a suspected-wrong config against.

---

## 2026-09-05 - CPU throttling under load at `cpu: limits: 250m`

**What we tested:** `k8s/urlshort-deployment.yaml` already carried
`resources.limits.cpu: 250m` / `requests.cpu: 100m` (added same session,
alongside the earlier memory limits). Wanted to confirm the limit actually
throttles under load rather than just trusting the YAML — CPU limits fail
differently from memory limits (throttled, not OOMKilled), so the failure
mode needed to be observed directly, not inferred.
**Method:** No `metrics-server` in this kind cluster, so `kubectl top pod`
wasn't available, and no load-test binary (`hey`/`ab`/`wrk`) was installed
either. Wrote a small `xargs -P 30` + `curl` script (scratchpad, not
committed) firing 1000 concurrent `POST /shorten` requests at the NodePort
Service — chosen over `/healthz` because it round-trips to Redis and does
real per-request work. Captured `/sys/fs/cgroup/cpu.stat` inside a pod via
`kubectl exec` before and after the run as the ground-truth signal, since
it's the kernel's own throttling counters rather than a derived metric.
**Result:** One replica's `cpu.stat` went from `nr_periods 457 /
nr_throttled 13 / throttled_usec 900373` to `510 / 26 / 1422203` over the
~2s test — i.e. of the ~53 scheduling periods (100ms each) that occurred
during the run, roughly 13 hit the 250m quota and got throttled, adding
up to ~522ms of actual throttled time. All 3 replicas showed the same
pattern. Request latencies from `curl` stayed modest (30-80ms) — the
throttling was real and measurable at the kernel level, but not dramatic
enough to be obvious from client-side latency alone at this concurrency.
**Concept this confirmed:** A CPU `limit` doesn't kill the container the
way a memory limit does — the kernel's CFS bandwidth controller just
withholds CPU time once the cgroup exceeds its quota within a scheduling
period, so the process keeps running, just slower. `nr_throttled` /
`throttled_usec` in `cpu.stat` are the direct evidence of this happening,
and are worth reaching for over `kubectl top` (which shows usage, not
throttling) or raw client latency (which can under-represent it) when
confirming a CPU limit is actually binding.

---

## 2026-09-05 - Readiness probe stuck failing (404) after adding `/readyz`

**What broke:** Added `livenessProbe` (`/healthz`) and `readinessProbe`
(`/readyz`) to `k8s/urlshort-deployment.yaml`, plus a new `/readyz` route in
`app/app.py` that pings Redis. After applying, `urlshort` pods stayed
`Running` but `0/1 Ready` indefinitely. First hypothesis tested (by the
user): a stale Redis connection — deleted and reapplied the Redis pod.
Readiness stayed failed regardless.
**Error/symptom:** `kubectl describe pod` on an `urlshort` pod showed
`Warning  Unhealthy ... Readiness probe failed: HTTP probe failed with
statuscode: 404` — repeating on every probe interval, no restarts (liveness
was passing fine throughout, since `/healthz` did exist).
**Diagnosis path:** The 404 (not a connection error/timeout) was the key
detail — it meant the request was reaching the container fine, but the
route itself wasn't there, which pointed away from Redis/networking
entirely. `kubectl describe pod` also showed `Container image
"urlshort:local" already present on machine and can be accessed by the
pod` on Pulled — i.e. kubelet reused a cached local image rather than
fetching anything new. Confirmed: the running container predated the
`/readyz` route being added to `app.py` — it had simply never been rebuilt
into the image.
**Fix:** `docker build -t urlshort:local app/` → `kind load docker-image
urlshort:local --name k8s-starter` → `kubectl rollout restart
deployment/urlshort-deployment`. All three steps were necessary: build
alone doesn't reach the `kind` node's containerd, load alone doesn't touch
already-running pods, and restart alone (without a rebuild/reload first)
would've just recreated pods against the same stale image.
**Concept this reinforced:** With a non-`:latest` tag (`urlshort:local`),
`imagePullPolicy` defaults to `IfNotPresent` — kubelet will happily keep
using whatever image already sits under that tag on the node and never
notices a rebuild on the host. `docker build` → `kind load docker-image` →
force pod recreation (`rollout restart`, since the Deployment spec itself
didn't change) is the full loop required to actually run new code in this
local-cluster setup — a gap that's easy to hit repeatedly until it's
internalized. Also: an HTTP 404 on a probe is a distinct, meaningful signal
from a connection error/timeout — it says "I reached the app, the route
just isn't there" and should redirect diagnosis away from
networking/dependency theories entirely.

---

## 2026-09-05 - `/readyz` implementation bugs caught in review before deploy

**What we caught:** Reviewing the first draft of `/readyz` in `app/app.py`
before it was wired into the readinessProbe surfaced three separate
issues, none of which would have been obvious from `kubectl` output alone:
(1) it returned bare `200`/`-1` values from the FastAPI handler, which
FastAPI serializes as the JSON *body* — the actual HTTP status stayed `200`
in both branches, so a probe reading it would never have detected a
failure at all; (2) it used the third-party `ping3` library to ICMP-ping
`f"{REDIS_HOST}:{REDIS_PORT}"` (a malformed target for ICMP, and ICMP also
needs `CAP_NET_RAW`, which containers often lack) rather than checking
whether Redis itself was actually responding; (3) the new `ping3`
dependency was added to `pyproject.toml`/`uv.lock` but never to
`requirements.txt`, which is what `Dockerfile` actually installs from — so
the built image would have `ImportError`ed on startup regardless of (1)
and (2).
**Fix:** Rewrote `/readyz` to call the existing `redis.Redis` client's own
`.ping()` (real Redis-protocol check) and `raise HTTPException(status_code=
503)` on `redis.RedisError` (broadened from `ConnectionError` to also catch
`TimeoutError`, a sibling exception in redis-py's hierarchy, not a
subclass). Added `socket_connect_timeout`/`socket_timeout` to the Redis
client so the endpoint fails fast rather than hanging past what the probe's
own `timeoutSeconds` would otherwise silently absorb. `ping3` dependency
dropped entirely rather than reconciled into `requirements.txt`.
**Concept this reinforced:** A probe endpoint's correctness lives or dies
on details that are invisible from the YAML side — an HTTP handler
returning a value isn't the same as setting a status code, and a
Kubernetes probe only ever looks at the status code. Also surfaced the
liveness/readiness design principle concretely: liveness triggers a
disruptive restart, so it should stay narrow/self-contained (never check
downstream dependencies, or an outage in one dependency restart-loops every
consumer of it); readiness gates traffic routing, which is cheap and
reversible, so it's the one allowed — even expected — to depend on the
outside world.

---

## 2026-09-05 - Readiness probe timing set backwards from its own design goal

**What we caught:** First draft of the readiness/liveness probe timing had
readiness *slower* to react than liveness — `periodSeconds: 10` /
`failureThreshold: 3` (~30-40s to detect a failure) versus liveness's
`periodSeconds: 5` / `failureThreshold: 5` (~25-35s). That's backwards:
liveness failures trigger a disruptive restart and should stay lenient;
readiness failures just pull a pod from Service rotation (cheap,
reversible) and should react fast, since every second of delay there is
live user traffic being routed to a pod that can't serve it.
**Fix:** Readiness tightened to `initialDelaySeconds: 3` /
`periodSeconds: 1` / `failureThreshold: 3` (~3s to detect and pull from
rotation), liveness left as the more forgiving of the two.
**Concept this reinforced:** Probe *values* need to reflect the asymmetric
cost of what each probe triggers, not just be "reasonable-looking numbers"
independently. Flagged as a separate, real tradeoff worth keeping in mind:
`periodSeconds: 1` is also a permanent steady-state cost (a real Redis
round-trip every second, forever, × replica count), not just a detection
window — worth revisiting if this were headed to a real deployment rather
than a local learning exercise.

---

## 2026-09-06 - `/shorten` 500 after rollout, traceback on a different replica

**What broke:** Shipped a `created_at` feature (write `datetime` to Redis on
`/shorten`, surface it in `/stats`) via the full rebuild → `kind load` →
`kubectl rollout restart` loop. Rollout reported `successfully rolled out`,
all 3 pods `1/1 Ready` — and `/shorten` returned HTTP 500 every call.
**Error/symptom:** First look at `kubectl logs <pod>` showed only `/healthz`
and `/readyz` 200s, no traceback — looked like the error wasn't being
logged at all.
**Diagnosis path:** The missing-traceback was a red herring caused by
replica count. With 3 pods behind the Service, kube-proxy sent the failing
`/shorten` call to one pod, and `kubectl logs <pod>` was tailing a
different one that had only ever served probe traffic. `kubectl logs -l
app=urlshort --prefix --tail=-1` (all matching pods, pod name prefixed on
each line) surfaced the uvicorn traceback immediately. Two bugs, both in
the new code: (1) `import datetime` then calling `datetime.now()` —
`AttributeError`, needed `from datetime import datetime`; (2) even fixed,
`r.set(key, datetime.now())` throws redis-py `DataError` on a raw datetime
object — needs `str(...)` / `.isoformat()`.
**Fix:** `from datetime import datetime` + `r.set(f"created_at:{code}",
str(datetime.now()))`, rebuilt and re-rolled. `/stats` now returns
`created_at`.
**Concept this reinforced:** (1) "Rollout succeeded" ≠ "feature works" — the
rollout only ever checks the readiness probe, which here only pinged Redis
and never exercised `/shorten`, so a 100%-broken endpoint rolled out
green. (2) With N replicas, `kubectl logs <single-pod>` is a coin flip for
finding a request-specific error; `kubectl logs -l <selector> --prefix
--tail=-1` (or `deployment/<name>`, one pod) is the move. (3) redis-py
values must be str/bytes/int/float — it does not serialize arbitrary
objects.

---

## 2026-09-06 - Wedged rollout: broken `/readyz` deploy stalls, service stays up

**What we tested (deliberate break):** With the `created_at` version healthy
on 3 replicas, shipped a version where `/readyz` always returns 503, to see
what a rollout does when the new pods can never go Ready. Prediction under
test (user's): that K8s terminates the 3 old pods to make room, so the new
(broken) ones "just won't be ready."
**What actually happened:** Exactly one new pod was created
(`7cdcccbdfd-*`, `0/1 Running`, `Readiness probe failed: statuscode: 503`
repeating). The old ReplicaSet stayed `3/3` Ready and untouched. `curl
/stats/<code>` kept working throughout. `kubectl rollout status` printed
`Waiting for deployment ... 1 out of 3 new replicas have been updated...`
and never returned (would exit non-zero only after
`progressDeadlineSeconds`, default 600s → `ProgressDeadlineExceeded`).
`kubectl describe deployment` showed `Available True /
MinimumReplicasAvailable` and `Progressing True / ReplicaSetUpdated`.
**Why:** `replicas: 3` with the default 25% rolling-update knobs resolves to
`maxSurge: 1` (rounds up) / `maxUnavailable: 0` (rounds down). So: at most
4 pods total, at least 3 available at all times. The Deployment created its
1 surge pod and then wedged — can't add a 2nd new pod (would exceed surge),
can't kill any old pod (would breach `maxUnavailable: 0`) until the new pod
reports Ready, which it never does. The readiness probe is the load-bearing
piece: it's what defines "Ready" and therefore what blocks the old pods
from being reaped.
**Recovery:** `kubectl rollout undo deployment/urlshort-deployment` — scaled
the broken ReplicaSet back to 0, left the old one at 3. Zero-downtime
because the old RS's 3 pods were still running the whole time; no pod
creation / image pull was needed.
**The trap surfaced (not hit, but real):** every ReplicaSet in
`rollout history` (8 revisions) has an identical pod template —
`image: urlshort:local` in all of them, differing only by the
`kubectl.kubernetes.io/restartedAt` annotation. `urlshort:local` is a
mutable tag (functionally `:latest`), and `docker build` + `kind load`
keeps overwriting what it points to. `rollout undo` faithfully restores the
pod *template*, but the template's image reference never uniquely
identified any code. It worked this time only because the rollback needed
no new pods; had a fresh pod been created (higher `maxUnavailable`, waited
out the deadline, manual `delete pod`), it would have pulled the
now-broken bits cached under `urlshort:local` (`imagePullPolicy:
IfNotPresent` for a non-`:latest` tag) and `rollout undo` would have
reported success while still serving broken code. Same root cause as the
2026-09-05 stale-image 404. Real fix is immutable image refs
(`:git-sha` / `:1.4.2` / `@sha256:…`), which is also why GitOps pipelines
pin a tag/digest into the manifest per build. After the session the good
image was rebuilt and reloaded so the node's `urlshort:local` cache
matches the running code again (pods not restarted).
