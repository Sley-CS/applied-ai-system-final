# I used AI as a coding partner to help me find and fix bugs in my guessing game.
# The AI read through my code, explained what was broken and why, then applied the
# fixes directly while I reviewed and approved each change. Together we also cleaned
# up the code structure, wrote automated tests to make sure everything works, and
# solved setup issues along the way.

import random
import streamlit as st
from logic_utils import DIFFICULTY_CONFIG, parse_guess, check_guess, update_score


def reset_game(difficulty: str) -> None:
    low, high = DIFFICULTY_CONFIG[difficulty]["range"]
    st.session_state.secret = random.randint(low, high)
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.history = []
    st.session_state.status = "playing"
    st.session_state.difficulty = difficulty
    st.session_state.last_hint = None
    st.session_state.game_count += 1


def on_enter() -> None:
    st.session_state.pending_submit = True


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

if "last_hint" not in st.session_state:
    st.session_state.last_hint = None

if "difficulty" not in st.session_state or st.session_state.difficulty != difficulty:
    reset_game(difficulty)

# ── UI ────────────────────────────────────────────────────────────────────────

st.subheader("Make a guess")
st.info(
    f"Guess a number between {low} and {high}. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)

if st.session_state.last_hint and st.session_state.show_hint:
    st.warning(st.session_state.last_hint)

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

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}_{st.session_state.game_count}",
    on_change=on_enter,
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀", use_container_width=True)
with col2:
    new_game = st.button("New Game 🔁", use_container_width=True)
with col3:
    st.checkbox("Show hint", key="show_hint")

if new_game:
    reset_game(difficulty)
    st.rerun()

if (submit or st.session_state.get("pending_submit")) and st.session_state.status == "playing":
    st.session_state.pending_submit = False
    ok, guess_int, err = parse_guess(raw_guess)

    if not ok:
        st.error(err)
    elif not (low <= guess_int <= high):
        st.error(f"Out of range! Please enter a number between {low} and {high}.")
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        outcome, message = check_guess(guess_int, st.session_state.secret)
        st.session_state.last_hint = message
        st.session_state.score = update_score(
            st.session_state.score, outcome, st.session_state.attempts
        )

        if outcome == "Win":
            st.session_state.status = "won"
        elif st.session_state.attempts >= attempt_limit:
            st.session_state.status = "lost"

        st.rerun()
elif st.session_state.get("pending_submit"):
    st.session_state.pending_submit = False

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
