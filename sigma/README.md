# Sigma rules

Detection rules in [Sigma](https://github.com/SigmaHQ/sigma) format,
loaded by the `detector` service. Each YAML file is one rule; the
file name becomes the rule id seen on alerts.

Currently shipped:

- [`ssh-failed-login.yml`](ssh-failed-login.yml) — single failed SSH
  login. Low severity; building block for brute-force.
- [`firewall-drop-from-public-to-priv-port.yml`](firewall-drop-from-public-to-priv-port.yml)
  — public-source-IP firewall drop targeting a privileged dst port.
  Medium severity; signals reconnaissance.
- [`dns-query-suspicious-tld.yml`](dns-query-suspicious-tld.yml) —
  DNS query against a list of high-abuse TLDs (.zip, .top, .xyz, …).
  Low severity; demonstrates list-as-OR matching.
