# k8s-starter-pack

A hands-on Kubernetes learning project. The goal is Kubernetes fluency, not
Python fluency — the application in [app/](app/) is a small FastAPI + Redis
URL shortener with click analytics, prewritten by Claude Code as scaffolding
to deploy. It exists to give Kubernetes concepts something real to attach
to (a datastore dependency, config, metrics), not as a Python exercise in
its own right.

The Kubernetes side — manifests in [k8s/](k8s/), and everything that follows
(Helm charts, ArgoCD config) — is the actual subject of this repo, worked
through hands-on rather than copied from a tutorial.

- [CLAUDE.md](CLAUDE.md) — the approach/tone this repo's sessions follow.
- [PROGRESS.md](PROGRESS.md) — what's built, what's covered, what's next.

## Local environment

- `kind` cluster named `k8s-starter` (`kind create cluster --name k8s-starter`)
- App image: `docker build -t urlshort:local app/`, then
  `kind load docker-image urlshort:local --name k8s-starter`
- Manifests applied individually from [k8s/](k8s/) via `kubectl apply -f`
