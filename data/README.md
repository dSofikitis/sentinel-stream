# data

Seed corpora for offline pipeline testing.

## `sample-events.jsonl`

Eight curated events covering all three classes plus the two attack
scenarios baked into the generator:

- 2 successful auth events
- 2 failed SSH login attempts followed by a success (brute-force tail)
- 2 firewall drops to privileged ports (probe pattern)
- 2 DNS queries, one of which lands on a `.zip` TLD

Use it for a deterministic end-to-end pipe demo without standing up
the generator:

```bash
make demo-from-seed
```

Future runs of `generator` against larger Sigma test corpora can
land here too — keep them small (`< 5 MB`); pull bigger ones at
build time instead of checking them in.
