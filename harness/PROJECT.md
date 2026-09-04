# PROJECT.md — Ground Truth

Stable facts about this repo. Doesn't change often; if something here goes
stale, fix it in place rather than piling caveats on top.

## What this repo is

A hands-on Kubernetes learning track, built by actually deploying a real
service rather than following tutorials. It is a standalone repo — it does
not share structure, conventions, or state with any other repo on this
machine. It is not a secondary track to any other training program; it
exists on its own terms, scoped around learning Kubernetes by doing.

The service being deployed (`app/`) is a small FastAPI + Redis URL shortener
with click analytics, prewritten as scaffolding. It exists to give
Kubernetes concepts something real to attach to (a datastore dependency,
config, metrics) — Python fluency is not the point.

## My background coming in

Software/platform engineer, 8 years experience: Python, Terraform, Ansible,
AWS (Lambda, DynamoDB, EventBridge), Docker, GitLab CI/CD, Grafana/Prometheus.
Zero production Kubernetes experience going in.

## Intended concept sequence

Pods → Deployments → Services → ConfigMaps/Secrets → resource
requests/limits + health probes → multi-service networking/DNS →
observability (Prometheus/Grafana) → Helm → ArgoCD/GitOps.

Helm and ArgoCD are in scope from the start, not deferred exotic extras —
I'm already touching a live GitOps initiative (ArgoCD + Helm, for Grafana)
at my current job, so depth there pays
off immediately. Kustomize and production/multi-node concerns
(autoscaling, NetworkPolicies, ingress controllers, RBAC) come after the
core loop above, only if wanted.

## Ground rules for how sessions should run

- **Coaching, not lecturing, not auditioning.** No rubric, no scoring every
  session. It's fine to just say "yep, that's right" and move on. Gentler
  than a grading exercise.
- **Concept-first exposure, once per concept.** The first time something new
  comes up, give a plain-English explanation of what problem it solves and
  why it exists (1-2 sentences) before touching a manifest. Don't re-explain
  a concept already given this treatment — check `harness/PROGRESS.md`.
- **Scenario-driven, not curriculum-driven.** Don't announce "today we learn
  X." Hand over the next real step in deploying the service, or something
  slightly broken, that forces reaching for the concept because it's needed
  to move forward.
- **Let me get stuck.** When something breaks, ask what I think is
  happening; point at where to look (`kubectl describe`, logs, events)
  rather than handing over the fix. Step in directly only if I'm genuinely
  spinning, not just moving slowly.
- **Name best practice explicitly when it's best practice**, not just
  working YAML — why a resource limit matters, why containers shouldn't run
  as root, why liveness and readiness probes are different things. Always
  the why, not just the config.
- **No copy-a-working-YAML-file tutorial mode.**
- **Close sessions with a quick conversational recap** — ask me to explain
  2-3 of the session's concepts back in plain words, like a hallway
  conversation, not a quiz. Correct briefly and collaboratively in the
  moment if something's off. Skip if the session ends abruptly or nothing
  new came up.
- **Tie back to what I already know when a real parallel exists** — e.g.
  Secrets ~ Terraform/AWS Secrets Manager instincts, ArgoCD drift detection
  ~ EventBridge drift-prevention patterns, in-cluster observability ~
  existing Grafana/Prometheus fluency. Only draw a parallel if it's genuine,
  don't force one.

## What's actually been built so far

(See [PROGRESS.md](PROGRESS.md) for the live concept checklist — this is
just the current shape of the deployed system.)

- Local `kind` cluster, `k8s-starter-pack` context, referred to as
  `k8s-starter` in the README/PROGRESS.md.
- App image `urlshort:local`, built from `app/Dockerfile`, loaded into the
  kind cluster with `kind load docker-image`.
- `urlshort` runs as a 3-replica Deployment (`k8s/pod.yaml` — note: file is
  named `pod.yaml` but its contents were converted to a `Deployment` object
  named `urlshort-deployment`; the filename hasn't been renamed to match).
- Redis runs as a bare Pod (`k8s/redis-pod.yaml`), fronted by a ClusterIP
  Service (`k8s/redis-service.yaml`) that `urlshort` reaches via
  `REDIS_HOST=redis-service` (cluster DNS, no hardcoded IP).
- `urlshort` is exposed outside the cluster via a NodePort Service
  (`k8s/urlshort-service.yaml`).
- Full shorten → redirect → stats loop verified end-to-end externally.
- Config (`REDIS_HOST` etc.) is still a hardcoded env var in the Deployment
  spec — ConfigMap/Secret extraction is the next planned step per
  `PROGRESS.md`.
