"""Explain panel — a grounded LLM drawer over computed results.

Opens as a right-side dialog. The first answer is auto-generated for the
clicked target; follow-ups go through a chat input. Conversation state
lives in ``st.session_state`` and is cleared whenever the grounding
context (dataset, filters, KPI) changes, so answers never reference
numbers that no longer apply.
"""

from html import escape

import streamlit as st

from dashboard.llm_client import ask
from dashboard.llm_context import context_fingerprint
from dashboard.llm_validate import unverified_numbers


DISCLAIMER = (
    "Reads only from your computed results — it explains the numbers, "
    "it never invents them."
)
SEED_FOCUS = (
    "Explain this in plain language: what does it show, how does it "
    "connect to the other findings, and what should I do next?"
)
SEED_PAGE = (
    "Summarize these results: what matters most, how do the findings "
    "connect, and what should I do first?"
)
UNVERIFIED_NOTE = (
    "Note: these figures are not in the computed results and should be "
    "treated as unverified: "
)


def _letter_avatar(letter: str, color: str, background: str) -> str:
    """Inline SVG letter avatar for chat messages."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        f'<rect width="32" height="32" rx="8" fill="{background}"/>'
        '<text x="16" y="21" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="15" font-weight="700" '
        f'fill="{color}">{letter}</text></svg>'
    )


AVATARS = {
    "assistant": _letter_avatar("D", "#5b8cff", "#1b2438"),
    "user": _letter_avatar("H", "#e7e9ee", "#22262e"),
}


def open_explain(
    *,
    target: str,
    context: dict,
    seed_question: str,
    title: str | None = None,
    chips: list[tuple[str, str, str | None]] | None = None,
) -> None:
    """Open the Explain drawer for one target component or page."""
    _explain_dialog(target, context, seed_question, title, chips or [])


@st.dialog("Explain", width="large")
def _explain_dialog(
    target: str,
    context: dict,
    seed_question: str,
    title: str | None,
    chips: list[tuple[str, str, str | None]],
) -> None:
    fingerprint = context_fingerprint(context)
    if (
        st.session_state.get("explain_target") != target
        or st.session_state.get("explain_fingerprint") != fingerprint
    ):
        st.session_state["explain_target"] = target
        st.session_state["explain_fingerprint"] = fingerprint
        st.session_state["explain_messages"] = []
    messages = st.session_state["explain_messages"]

    st.markdown(
        f'<div class="explain-disclaimer">{DISCLAIMER}</div>',
        unsafe_allow_html=True,
    )
    if title:
        st.markdown(
            f'<div class="explain-title">{escape(title)}</div>',
            unsafe_allow_html=True,
        )
    if chips:
        chip_html = "".join(
            f'<span class="explain-chip">{escape(label)}'
            f'<b style="color:{color or "var(--dac-text)"}">'
            f"{escape(value)}</b></span>"
            for label, value, color in chips
        )
        st.markdown(
            f'<div class="explain-chips">{chip_html}</div>',
            unsafe_allow_html=True,
        )

    # All turns render into this fixed-height scrollable container so
    # they always appear above the chat input and long conversations
    # scroll inside the drawer instead of overflowing it. The key lets
    # the CSS shrink it on short viewports.
    # The st.empty() slot wipes the previous run's conversation from the
    # screen as soon as the dialog paints — otherwise a target switch
    # would keep showing the old chat while the seed fetch blocks.
    conversation = st.empty().container(height=500, key="explain_conversation")
    with conversation:
        if not messages:
            seed_answer = _send(seed_question, context, messages, seed=True)
            if not messages:
                # Failed seed isn't persisted, so reopening retries it.
                with st.chat_message("assistant", avatar=AVATARS["assistant"]):
                    st.markdown(seed_answer["content"])

        for message in messages:
            if message.get("seed"):
                continue
            with st.chat_message(message["role"], avatar=AVATARS[message["role"]]):
                st.markdown(message["content"])
                if message.get("caveat"):
                    st.caption(message["caveat"])

    prompt = st.chat_input("Ask about a number on this page")
    if prompt:
        with conversation:
            with st.chat_message("user", avatar=AVATARS["user"]):
                st.markdown(prompt)
            answer = _send(prompt, context, messages)
            with st.chat_message("assistant", avatar=AVATARS["assistant"]):
                st.markdown(answer["content"])
                if answer.get("caveat"):
                    st.caption(answer["caveat"])


def _send(
    question: str,
    context: dict,
    messages: list[dict],
    seed: bool = False,
) -> dict:
    """Call the LLM with prior history, append both turns, return answer."""
    history = [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]
    user_message = {"role": "user", "content": question}
    if seed:
        user_message["seed"] = True
    messages.append(user_message)

    with st.spinner("Reading the computed results…"):
        response = ask(context, history, question)

    answer = {"role": "assistant", "content": response.text}
    if seed and not response.ok:
        messages.pop()
        return answer
    if response.ok:
        flagged = unverified_numbers(response.text, context)
        if flagged:
            answer["caveat"] = UNVERIFIED_NOTE + ", ".join(flagged)
    messages.append(answer)
    return answer
