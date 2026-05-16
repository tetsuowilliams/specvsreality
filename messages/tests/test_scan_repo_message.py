from __future__ import annotations

from specvsreality_messages import ScanRepoMessage, parse_worker_message


def test_scan_repo_round_trip_json() -> None:
    raw = '{"message_type":"scan_repo","repo_id":"42"}'
    msg = parse_worker_message(raw)
    assert isinstance(msg, ScanRepoMessage)
    assert msg.repo_id == "42"

