from __future__ import annotations

from specvsreality_messages import (
    InitRepoMessage,
    SpecScanMessage,
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


def test_spec_scan_round_trip_json() -> None:
    raw = (
        '{"message_type":"spec_scan","repo_id":"1","commit_id":99,'
        '"spec_folder":"specs/my-feature"}'
    )
    msg = parse_worker_message(raw)
    assert isinstance(msg, SpecScanMessage)
    assert msg.repo_id == "1"
    assert msg.commit_id == 99
    assert msg.spec_folder == "specs/my-feature"
    assert msg.extract_spec is True


def test_spec_scan_extract_spec_false_round_trip_json() -> None:
    raw = (
        '{"message_type":"spec_scan","repo_id":"1","commit_id":99,'
        '"spec_folder":"specs/my-feature","extract_spec":false}'
    )
    msg = parse_worker_message(raw)
    assert isinstance(msg, SpecScanMessage)
    assert msg.extract_spec is False
