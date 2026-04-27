import json
from datetime import datetime, timezone


DIFFICULTY_CONFIG = {
    "Easy":   {"range": (1, 20),  "attempts": 6},
    "Normal": {"range": (1, 50),  "attempts": 8},
    "Hard":   {"range": (1, 100), "attempts": 5},
}


def guess_temperature(guess: int, secret: int, low: int, high: int) -> str:
    """Classify how close a guess is to the secret number.

    Returns:
        One of ``"Hot"``, ``"Warm"``, ``"Cold"``, or ``"Ice"``.
    """
    closeness = closeness_percent(guess, secret, low, high)
    if closeness >= 80:
        return "Hot"
    if closeness >= 55:
        return "Warm"
    if closeness >= 30:
        return "Cold"
    return "Ice"


def guess_distance(guess: int, secret: int) -> int:
    """Return the absolute difference between a guess and the secret number.

    Args:
        guess: The player's guessed number.
        secret: The hidden target number.

    Returns:
        The non-negative distance between the two values.
    """
    return abs(guess - secret)


def closeness_percent(guess: int, secret: int, low: int, high: int) -> int:
    """Convert a guess's distance from the secret into a 0-100 score.

    A higher value means the guess is closer to the secret. The result is
    clamped to the inclusive range 0 to 100 so it can be rendered safely in
    UI progress indicators.

    Args:
        guess: The player's guessed number.
        secret: The hidden target number.
        low: The minimum valid value for the selected difficulty.
        high: The maximum valid value for the selected difficulty.

    Returns:
        An integer percentage representing closeness to the secret.
    """
    span = max(1, high - low)
    distance = guess_distance(guess, secret)
    return max(0, min(100, round(100 - (distance / span) * 100)))


def history_summary(
    history: list[int], secret: int, low: int, high: int
) -> list[dict[str, int | str]]:
    """Build sidebar-ready rows describing each prior guess.

    Each row includes the attempt number, the guess itself, the distance to the
    secret, and a closeness score suitable for a progress bar.

    Args:
        history: Ordered list of guesses from the current game session.
        secret: The hidden target number.
        low: The minimum valid value for the selected difficulty.
        high: The maximum valid value for the selected difficulty.

    Returns:
        A list of dictionaries ready for display in the sidebar.
    """
    rows = []
    for attempt, guess in enumerate(history, start=1):
        rows.append(
            {
                "attempt": attempt,
                "guess": guess,
                "distance": guess_distance(guess, secret),
                "closeness": closeness_percent(guess, secret, low, high),
                "temperature": guess_temperature(guess, secret, low, high),
            }
        )
    return rows


def get_range_for_difficulty(difficulty: str) -> tuple[int, int]:
    """Return the inclusive number range associated with a difficulty level.

    Args:
        difficulty: The selected difficulty name.

    Returns:
        A tuple containing the inclusive lower and upper bounds.
    """
    return DIFFICULTY_CONFIG[difficulty]["range"]


def parse_guess(raw: str) -> tuple[bool, int | float | None, str | None]:
    """Parse raw user input into a numeric guess or an error.

    The parser accepts strings that can be interpreted as numbers, including
    decimal and scientific notation. Whole-number inputs are normalized to
    ``int`` values, while non-integral values are returned as ``float`` values
    so the caller can decide how to handle them.

    Args:
        raw: The unprocessed user input from the text field.

    Returns:
        A tuple of ``(ok, guess_value, error_message)`` where ``ok`` is ``True``
        when parsing succeeds, ``guess_value`` contains the parsed number, and
        ``error_message`` is ``None`` unless parsing failed.
    """
    if raw is None:
        return False, None, "Enter a guess."

    s = str(raw).strip()
    if s == "":
        return False, None, "Enter a guess."

    # Reject common non-numeric formatting such as commas
    if "," in s:
        return False, None, "That is not a number."

    try:
        # Use float() to accept decimal and scientific notation
        f = float(s)
    except Exception:
        return False, None, "That is not a number."

    # Reject NaN and infinities
    if f != f or f in (float("inf"), float("-inf")):
        return False, None, "That is not a number."

    # If the value is an integer (e.g. 3.0), return an int
    if float(int(f)) == f:
        return True, int(f), None

    return True, f, None


def check_guess(guess: int, secret: int) -> tuple[str, str]:
    """Compare a guess to the secret number and return game feedback.

    Args:
        guess: The player's guessed number.
        secret: The hidden target number.

    Returns:
        A tuple of ``(outcome, message)`` where ``outcome`` is one of
        ``"Win"``, ``"Too High"``, or ``"Too Low"``.
    """
    if guess == secret:
        return "Win", "🎉 Correct!"
    elif guess > secret:
        return "Too High", "📉 Go LOWER!"
    else:
        return "Too Low", "📈 Go HIGHER!"


def update_score(current_score: int, outcome: str, attempt_number: int) -> int:
    """Update the running score after a guess outcome.

    Wins award more points when they happen earlier in the game. Non-winning
    guesses deduct a small fixed amount, and the score never drops below zero.

    Args:
        current_score: The score before the current guess is processed.
        outcome: The result returned by :func:`check_guess`.
        attempt_number: The 1-based attempt count for the current guess.

    Returns:
        The updated score.
    """
    if outcome == "Win":
        return current_score + max(10, 100 - 10 * attempt_number)
    if outcome in ("Too High", "Too Low"):
        return max(0, current_score - 5)
    return current_score


def confidence_score(
    guess: int | float,
    secret: int,
    low: int,
    high: int,
    outcome: str,
) -> float:
    """Estimate answer confidence in the inclusive range 0.0 to 1.0.

    The score is based on game outcome and numerical closeness so the UI can
    expose reliability information to the player.
    """
    if outcome == "Win":
        return 1.0

    try:
        closeness = closeness_percent(int(guess), secret, low, high)
    except Exception:
        return 0.0

    # Scale to 0-1 and keep a minimum floor for valid in-range guesses.
    return round(max(0.1, min(0.95, closeness / 100)), 2)


def build_game_event(
    difficulty: str,
    guess: int,
    outcome: str,
    attempts: int,
    score: int,
    confidence: float,
) -> dict[str, str | int | float]:
    """Build a structured game event for logs and downstream validation."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "difficulty": difficulty,
        "guess": guess,
        "outcome": outcome,
        "attempts": attempts,
        "score": score,
        "confidence": confidence,
    }


def validate_game_event(event: dict[str, str | int | float]) -> tuple[bool, str | None]:
    """Apply guardrails to a game event before it is accepted or logged."""
    required_fields = {
        "timestamp",
        "difficulty",
        "guess",
        "outcome",
        "attempts",
        "score",
        "confidence",
    }
    if not required_fields.issubset(set(event.keys())):
        return False, "Missing required logging fields."

    if event["outcome"] not in {"Win", "Too High", "Too Low"}:
        return False, "Invalid game outcome detected."

    confidence = event["confidence"]
    if not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
        return False, "Confidence score must be between 0.0 and 1.0."

    attempts = event["attempts"]
    if not isinstance(attempts, int) or attempts < 1:
        return False, "Attempts must be a positive integer."

    score = event["score"]
    if not isinstance(score, int) or score < 0:
        return False, "Score must be a non-negative integer."

    return True, None


def append_json_log(log_path: str, event: dict[str, str | int | float]) -> None:
    """Append one validated event to a JSONL log file."""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def append_error_log(
    log_path: str,
    stage: str,
    error: Exception,
    context: dict[str, str | int | float] | None = None,
) -> None:
    """Append one structured runtime error entry to a JSONL log file."""
    payload: dict[str, str | int | float | dict[str, str | int | float]] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "error_type": type(error).__name__,
        "message": str(error),
        "context": context or {},
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + "\n")
