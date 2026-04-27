# I used AI as a coding partner to help me find and fix bugs in my guessing game.
# The AI read through my code, explained what was broken and why, then applied the
# fixes directly while I reviewed and approved each change. Together we also cleaned
# up the code structure, wrote automated tests to make sure everything works, and
# solved setup issues along the way.

import random
import streamlit as st
from logic_utils import (
    DIFFICULTY_CONFIG,
    append_json_log,
    append_error_log,
    build_game_event,
    parse_guess,
    check_guess,
    confidence_score,
    update_score,
    validate_game_event,
    history_summary,
    guess_temperature,
)


LOG_PATH = "assets/gameplay_log.jsonl"
ERROR_LOG_PATH = "assets/error_log.jsonl"


def reset_game(difficulty: str) -> None:
    low, high = DIFFICULTY_CONFIG[difficulty]["range"]
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.history = []
    st.session_state.status = "playing"
    st.session_state.difficulty = difficulty
    st.session_state.last_hint = None
    st.session_state.last_temperature = None
    st.session_state.last_outcome = None
    st.session_state.last_confidence = None
    st.session_state.game_count += 1


# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")
st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.header("Settings")
difficulty = st.sidebar.selectbox("Difficulty", list(DIFFICULTY_CONFIG), index=1)

low, high = DIFFICULTY_CONFIG[difficulty]["range"]
attempt_limit = DIFFICULTY_CONFIG[difficulty]["attempts"]

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

# ── Session state init ────────────────────────────────────────────────────────

if "game_count" not in st.session_state:
    st.session_state.game_count = 0

if "show_hint" not in st.session_state:
    st.session_state.show_hint = True

if "difficulty" not in st.session_state or st.session_state.difficulty != difficulty:
    reset_game(difficulty)

st.sidebar.divider()
st.sidebar.subheader("Guess History")
if st.session_state.history:
    history_rows = history_summary(
        st.session_state.history,
        st.session_state.secret,
        low,
        high,
    )
    for row in history_rows:
        st.sidebar.caption(
            f"Attempt {row['attempt']}: {row['guess']} • {row['distance']} away"
        )
        st.sidebar.progress(row["closeness"])
else:
    st.sidebar.caption("Your previous guesses will appear here.")

# ── UI ────────────────────────────────────────────────────────────────────────

st.subheader("Make a guess")
st.info(
    f"Guess a number between {low} and {high}. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

summary_rows = history_summary(st.session_state.history, st.session_state.secret, low, high)
if summary_rows:
    st.subheader("Session Summary")
    st.dataframe(
        summary_rows,
        hide_index=True,
        use_container_width=True,
    )
    best_row = max(summary_rows, key=lambda row: row["closeness"])
    st.caption(
        f"Best guess: attempt {best_row['attempt']} with {best_row['closeness']}% closeness "
        f"({best_row['temperature']})."
    )

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

if st.session_state.last_hint and st.session_state.show_hint:
    if st.session_state.last_outcome == "Win":
        st.success(f"🎉 {st.session_state.last_hint}")
    elif st.session_state.last_temperature == "Hot":
        st.success(f"🔥 Hot! {st.session_state.last_hint}")
    elif st.session_state.last_temperature == "Warm":
        st.info(f"🌤️ Warm. {st.session_state.last_hint}")
    elif st.session_state.last_temperature == "Cold":
        st.warning(f"🧊 Cold. {st.session_state.last_hint}")
    else:
        st.error(f"🥶 Ice cold. {st.session_state.last_hint}")

if st.session_state.last_confidence is not None:
    st.caption(f"Reliability confidence: {st.session_state.last_confidence:.2f}")

if st.session_state.status == "won":
    st.balloons()
    st.success(
        f"You won! The secret was {st.session_state.secret}. "
        f"Final score: {st.session_state.score}"
    )
    st.info("Start a new game to play again.")

if st.session_state.status == "lost":
    st.error(
        f"Out of attempts! The secret was {st.session_state.secret}. "
        f"Score: {st.session_state.score}"
    )
    st.info("Start a new game to play again.")

# ── Input & controls ─────────────────────────────────────────────────────────

with st.form(
    key=f"guess_form_{difficulty}_{st.session_state.game_count}",
    clear_on_submit=False,
):
    raw_guess = st.text_input("Enter your guess:")
    submit = st.form_submit_button("Submit Guess 🚀", use_container_width=True)

col1, col2 = st.columns(2)
with col1:
    new_game = st.button("New Game 🔁", use_container_width=True)
with col2:
    st.checkbox("Show hint", key="show_hint")

if new_game:
    reset_game(difficulty)
    st.rerun()

if submit and st.session_state.status == "playing":
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.error(err)
    elif not isinstance(guess_int, int):
        st.error("Please enter a whole number.")
    elif not (low <= guess_int <= high):
        st.error(f"Out of range! Please enter a number between {low} and {high}.")
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        outcome, message = check_guess(guess_int, st.session_state.secret)
        st.session_state.last_hint = message
        st.session_state.last_outcome = outcome
        st.session_state.last_temperature = guess_temperature(
            guess_int,
            st.session_state.secret,
            low,
            high,
        )
        st.session_state.last_confidence = confidence_score(
            guess_int,
            st.session_state.secret,
            low,
            high,
            outcome,
        )
        st.session_state.score = update_score(
            st.session_state.score, outcome, st.session_state.attempts
        )

        event = build_game_event(
            difficulty=st.session_state.difficulty,
            guess=guess_int,
            outcome=outcome,
            attempts=st.session_state.attempts,
            score=st.session_state.score,
            confidence=st.session_state.last_confidence,
        )
        is_valid, validation_error = validate_game_event(event)
        if not is_valid:
            st.error(f"System guardrail triggered: {validation_error}")
            try:
                append_error_log(
                    ERROR_LOG_PATH,
                    stage="event_validation",
                    error=ValueError(validation_error or "Unknown validation error"),
                    context=event,
                )
            except Exception:
                # Keep gameplay resilient even if error logging fails.
                pass
        else:
            try:
                append_json_log(LOG_PATH, event)
            except Exception as exc:
                st.warning("Log write failed. Gameplay will continue.")
                try:
                    append_error_log(
                        ERROR_LOG_PATH,
                        stage="gameplay_log_write",
                        error=exc,
                        context=event,
                    )
                except Exception:
                    # Keep gameplay resilient even if error logging fails.
                    pass

        if outcome == "Win":
            st.session_state.status = "won"
        elif st.session_state.attempts >= attempt_limit:
            st.session_state.status = "lost"

        st.rerun()

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
