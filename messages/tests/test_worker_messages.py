from __future__ import annotations

from specvsreality_messages import (
    InitRepoMessage,
    WindToHeadMessage,
    parse_worker_message,
)


def test_init_repo_round_trip_json() -> None:
    raw = '{"message_type":"init_repo","repo_id":"42"}'
    msg = parse_worker_message(raw)
    assert isinstance(msg, InitRepoMessage)
    assert msg.repo_id == "42"


def test_wind_to_head_round_trip_json() -> None:
    raw = '{"message_type":"wind_to_head","repo_id":"7"}'
    msg = parse_worker_message(raw)
    assert isinstance(msg, WindToHeadMessage)
    assert msg.repo_id == "7"
