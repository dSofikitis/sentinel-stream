# sentinel-detector

The detection brain. Consumes `events.enriched` and runs two layers
in parallel:

- **Sigma rules** — declarative YAML detections from
  [SigmaHQ](https://github.com/SigmaHQ/sigma). Lives in `sigma/` at
  the repo root.
- **Isolation Forest** — sklearn-based anomaly model on numeric event
  features (rate, hour-of-day, dst_port entropy, etc.). Catches what
  Sigma rules don't pre-encode.

Matches produce events on the `alerts` topic.

Implementation lands in phase 6. The current commit only ships a stub
to keep CI green.
