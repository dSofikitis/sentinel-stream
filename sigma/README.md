# Sigma rules

Detection rules in [Sigma](https://github.com/SigmaHQ/sigma) format,
loaded by the `detector` service via PySigma. Each YAML file is one
rule; the file name becomes the rule id seen on alerts.

Sample rules land in phase 6 (e.g. impossible-travel auth, brute-force
SSH, port-scan).
