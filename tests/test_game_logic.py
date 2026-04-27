import sys
import os
import json
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic_utils import (
    check_guess,
    update_score,
    parse_guess,
    get_range_for_difficulty,
    guess_distance,
    closeness_percent,
    history_summary,
    guess_temperature,
    confidence_score,
    build_game_event,
    validate_game_event,
    append_json_log,
    append_error_log,
)


# ── check_guess ───────────────────────────────────────────────────────────────

def test_correct_guess_returns_win():
    outcome, _ = check_guess(50, 50)
    assert outcome == "Win"

def test_correct_guess_message():
    _, message = check_guess(50, 50)
    assert "Correct" in message

def test_guess_too_high():
    outcome, _ = check_guess(60, 50)
    assert outcome == "Too High"

def test_guess_too_high_hint_says_lower():
    _, message = check_guess(60, 50)
    assert "LOWER" in message

def test_guess_too_low():
    outcome, _ = check_guess(40, 50)
    assert outcome == "Too Low"

def test_guess_too_low_hint_says_higher():
    _, message = check_guess(40, 50)
    assert "HIGHER" in message

def test_guess_boundary_low_end():
    outcome, _ = check_guess(1, 1)
    assert outcome == "Win"

def test_guess_boundary_high_end():
    outcome, _ = check_guess(100, 100)
    assert outcome == "Win"

def test_one_below_secret_is_too_low():
    outcome, _ = check_guess(49, 50)
    assert outcome == "Too Low"

def test_one_above_secret_is_too_high():
    outcome, _ = check_guess(51, 50)
    assert outcome == "Too High"


# ── update_score ──────────────────────────────────────────────────────────────

def test_win_on_first_attempt_gives_max_points():
    score = update_score(0, "Win", 1)
    assert score == 90  # 100 - 10*1

def test_win_score_decreases_with_more_attempts():
    early = update_score(0, "Win", 2)
    late  = update_score(0, "Win", 5)
    assert early > late

def test_win_score_never_below_10():
    score = update_score(0, "Win", 100)
    assert score >= 10

def test_wrong_guess_deducts_points():
    score = update_score(50, "Too High", 1)
    assert score == 45

def test_too_low_also_deducts_points():
    score = update_score(50, "Too Low", 1)
    assert score == 45

def test_score_never_goes_negative():
    score = update_score(0, "Too High", 1)
    assert score == 0

def test_unknown_outcome_leaves_score_unchanged():
    score = update_score(42, "Unknown", 1)
    assert score == 42


# ── parse_guess ───────────────────────────────────────────────────────────────

def test_valid_integer_string():
    ok, value, err = parse_guess("25")
    assert ok is True
    assert value == 25
    assert err is None

def test_empty_string_is_invalid():
    ok, value, err = parse_guess("")
    assert ok is False
    assert value is None

def test_none_input_is_invalid():
    ok, value, err = parse_guess(None)
    assert ok is False

def test_letters_are_invalid():
    ok, _, err = parse_guess("abc")
    assert ok is False
    assert err is not None

def test_decimal_rounds_to_int():
    ok, value, _ = parse_guess("7.0")
    assert ok is True
    assert value == 7

def test_negative_number_parses():
    ok, value, _ = parse_guess("-5")
    assert ok is True
    assert value == -5

def test_comma_is_invalid():
    ok, _, _ = parse_guess("1,000")
    assert ok is False

def test_decimal_input_is_handled_gracefully():
    ok, value, err = parse_guess("3.14")
    assert ok is True
    assert err is None
    assert value == 3.14

def test_negative_input_is_handled_gracefully():
    ok, value, err = parse_guess("-5")
    assert ok is True
    assert err is None
    assert value == -5

def test_very_large_integer_is_handled_gracefully():
    ok, value, err = parse_guess("9007199254740993")
    assert ok is True
    assert err is None
    assert isinstance(value, int)

def test_extremely_large_scientific_notation_is_rejected():
    ok, value, err = parse_guess("1e10000")
    assert ok is False
    assert value is None
    assert err is not None


# ── get_range_for_difficulty ──────────────────────────────────────────────────

def test_easy_range():
    low, high = get_range_for_difficulty("Easy")
    assert low == 1 and high == 20

def test_normal_range():
    low, high = get_range_for_difficulty("Normal")
    assert low == 1 and high == 50

def test_hard_range():
    low, high = get_range_for_difficulty("Hard")
    assert low == 1 and high == 100

def test_out_of_range_negative_guess_is_rejected_by_game_rules():
    low, high = get_range_for_difficulty("Easy")
    guess = -5
    assert not (low <= guess <= high)

def test_out_of_range_huge_guess_is_rejected_by_game_rules():
    low, high = get_range_for_difficulty("Hard")
    guess = 10**30
    assert not (low <= guess <= high)


# ── guess history helpers ────────────────────────────────────────────────────

def test_guess_distance_is_absolute_difference():
    assert guess_distance(40, 50) == 10
    assert guess_distance(60, 50) == 10


def test_closeness_percent_hits_100_for_correct_guess():
    assert closeness_percent(50, 50, 1, 100) == 100


def test_closeness_percent_decreases_as_guess_moves_away():
    close = closeness_percent(49, 50, 1, 100)
    far = closeness_percent(25, 50, 1, 100)
    assert close > far


def test_history_summary_builds_sidebar_rows():
    rows = history_summary([40, 60, 50], 50, 1, 100)
    assert rows[0]["attempt"] == 1
    assert rows[0]["guess"] == 40
    assert rows[0]["distance"] == 10
    assert rows[2]["closeness"] == 100
    assert rows[2]["temperature"] == "Hot"


def test_guess_temperature_labels_closeness_levels():
    assert guess_temperature(50, 50, 1, 100) == "Hot"
    assert guess_temperature(48, 50, 1, 100) in {"Hot", "Warm"}
    assert guess_temperature(40, 100, 1, 100) == "Cold"
    assert guess_temperature(1, 100, 1, 100) == "Ice"


# ── full game simulation ──────────────────────────────────────────────────────

def test_robot_plays_and_wins():
    secret = 37
    score = 0
    attempts = 0
    status = "playing"

    guesses = [50, 25, 37]  # high, low, correct

    for guess in guesses:
        attempts += 1
        outcome, _ = check_guess(guess, secret)
        score = update_score(score, outcome, attempts)
        if outcome == "Win":
            status = "won"
            break

    assert status == "won"
    assert attempts == 3
    assert score > 0
    print(f"✅ Robot won in {attempts} attempts with a score of {score}!")


def test_robot_loses_when_out_of_attempts():
    secret = 37
    attempt_limit = 3
    score = 0
    attempts = 0
    status = "playing"

    wrong_guesses = [10, 20, 30]  # all too low, never wins

    for guess in wrong_guesses:
        attempts += 1
        outcome, _ = check_guess(guess, secret)
        score = update_score(score, outcome, attempts)
        if outcome == "Win":
            status = "won"
            break
        if attempts >= attempt_limit:
            status = "lost"
            break

    assert status == "lost"
    assert score == 0  # started at 0, deducted to floor of 0
    print(f"🤖 Robot lost after {attempts} attempts as expected.")


# ── reliability mechanisms ────────────────────────────────────────────────────

def test_confidence_score_win_is_one():
    assert confidence_score(50, 50, 1, 100, "Win") == 1.0


def test_confidence_score_non_win_stays_in_bounds():
    score = confidence_score(40, 50, 1, 100, "Too Low")
    assert 0.0 <= score <= 1.0


def test_validate_game_event_accepts_valid_payload():
    event = build_game_event("Normal", 42, "Too Low", 2, 5, 0.72)
    ok, err = validate_game_event(event)
    assert ok is True
    assert err is None


def test_validate_game_event_rejects_invalid_outcome():
    event = build_game_event("Normal", 42, "Unknown", 2, 5, 0.72)
    ok, err = validate_game_event(event)
    assert ok is False
    assert "Invalid game outcome" in err


def test_append_json_log_writes_one_jsonl_line(tmp_path: Path):
    log_file = tmp_path / "gameplay_log.jsonl"
    event = build_game_event("Hard", 77, "Too High", 1, 0, 0.34)
    append_json_log(str(log_file), event)

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["difficulty"] == "Hard"
    assert payload["guess"] == 77


def test_append_error_log_writes_structured_error_payload(tmp_path: Path):
    error_log_file = tmp_path / "error_log.jsonl"
    context = {"difficulty": "Normal", "guess": 999}
    append_error_log(
        str(error_log_file),
        stage="gameplay_log_write",
        error=RuntimeError("disk full"),
        context=context,
    )

    lines = error_log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1

    payload = json.loads(lines[0])
    assert payload["stage"] == "gameplay_log_write"
    assert payload["error_type"] == "RuntimeError"
    assert payload["message"] == "disk full"
    assert payload["context"]["guess"] == 999
