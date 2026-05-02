import random

from sentinel_detector.anomaly import Anomaly, featurize
from sentinel_detector.events_warmup import warmup_corpus


def test_featurize_returns_fixed_length() -> None:
    ev = {
        "received_at": "2026-05-02T03:14:00Z",
        "severity": "warning",
        "src_port": 51234,
        "dst_port": 22,
        "src_ip": "203.0.113.42",
    }
    f = featurize(ev)
    assert len(f) == 5
    assert all(isinstance(v, float) for v in f)


def test_featurize_handles_missing_fields() -> None:
    f = featurize({})
    assert len(f) == 5


def test_anomaly_fits_and_scores() -> None:
    random.seed(7)
    model = Anomaly(contamination=0.1, random_state=7)
    model.fit(warmup_corpus(200))
    res = model.score({"severity": "info", "src_port": 50000, "dst_port": 443, "src_ip": "10.0.0.1"})
    assert 0.0 <= res.score <= 1.0


def test_anomaly_flags_obvious_outlier_higher_than_normal() -> None:
    random.seed(7)
    model = Anomaly(contamination=0.1, random_state=7)
    model.fit(warmup_corpus(500))
    normal = model.score(
        {
            "received_at": "2026-05-02T11:00:00Z",
            "severity": "info",
            "src_port": 50000,
            "dst_port": 443,
            "src_ip": "10.0.0.1",
        }
    )
    weird = model.score(
        {
            "received_at": "2026-05-02T03:00:00Z",
            "severity": "critical",
            "src_port": 65530,
            "dst_port": 1,
            "src_ip": "203.0.113.250",
        }
    )
    # The 03:00 critical-severity event to a privileged port from a
    # public IP is more anomalous than the daytime info event.
    assert weird.score > normal.score
