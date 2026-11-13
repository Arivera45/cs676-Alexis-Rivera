"""
agent.py — markdown file + model = an agent with its own mind.

This is the smallest interesting idea in the package. A `PersonaAgent` holds a
`PersonaSpec` (which came from a `.md` file) and an `LLM`. When you ask it to
speak, it builds a system prompt out of that markdown and sends the transcript
so far. The persona file *is* the agent's brain — nothing else distinguishes
the doctor from the patient.

Because the transcript is passed in rather than stored, agents are stateless
between turns. That is a design decision with consequences; see YOUR TASK.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from .llm import LLM
from .persona import PersonaSpec

# Wrapped around the persona markdown to put the model in character and keep it
# from narrating. Without the last two rules models tend to write stage
# directions and answer for everyone in the room.
_IN_CHARACTER_TEMPLATE = """You are role-playing a character in a simulated conversation.

Everything between the markers below defines who you are. Inhabit it completely:
speak in this person's voice, hold their opinions, want what they want.

=== BEGIN CHARACTER ===
{persona}
=== END CHARACTER ===

Rules:
- Speak only as {name}. Never speak for anyone else.
- Reply with dialogue only. No stage directions, no asterisks, no narration.
- Stay in character even if the conversation goes somewhere unexpected.
- Keep replies to a few sentences unless the moment genuinely calls for more.
- You are {name}. Do not mention that you are an AI or a simulation."""


@dataclass
class PersonaAgent:
    """One character in a conversation."""

    spec: PersonaSpec
    llm: LLM
    max_context_turns: int = 12

    @property
    def name(self) -> str:
        return self.spec.name

    def system_prompt(self) -> str:
        """The persona markdown, wrapped in the in-character instructions."""
        # Task 1: keep the persona's persistent memory with the markdown itself so
        # the same file survives runs and carries forward facts the character has
        # learned across conversations.
        persona = self.spec.body
        if self.spec.memory.strip():
            persona = f"{persona}\n\n## Persistent memory\n{self.spec.memory.strip()}"
        return _IN_CHARACTER_TEMPLATE.format(persona=persona, name=self.spec.name)

    def remember(self, fact: str) -> None:
        """Append a fact to the persona's persistent memory."""
        fact = fact.strip()
        if not fact:
            return
        memory = self.spec.memory.strip()
        if memory:
            self.spec.memory = f"{memory} | {fact}"
        else:
            self.spec.memory = fact

    def _context_summary(self, transcript: List["Turn"]) -> str:
        """Condense old turns into a short note so long conversations stay cheap."""
        # Task 2: summarize older turns instead of sending the whole transcript
        # back to the model on every message.
        if len(transcript) <= self.max_context_turns:
            return ""

        prior = transcript[:-self.max_context_turns]
        fragments = []
        for turn in prior:
            short = re.sub(r"\s+", " ", turn.text).strip()
            if len(short) > 80:
                short = short[:77] + "..."
            fragments.append(f"{turn.speaker}: {short}")

        summary = "Earlier in the conversation: " + " | ".join(fragments[:6])
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary

    def decide_response(self, transcript: List["Turn"]) -> str:
        """Return one of: speak, silent, pause, end."""
        # Task 3: the agent needs a lightweight policy for conversational control.
        # Instead of always speaking, it reacts to the last utterance with clear
        # decisions for silence, pause, or ending the exchange.
        if not transcript:
            return "speak"

        last = transcript[-1].text.lower()
        pause_markers = ("pause", "take a break", "hold on", "let's pause", "wait a moment")
        end_markers = ("end the conversation", "wrap up", "that's all", "we're done", "stop here")
        silence_markers = ("be quiet", "stay quiet", "no response", "silence")

        if any(marker in last for marker in pause_markers):
            return "pause"
        if any(marker in last for marker in end_markers):
            return "end"
        if any(marker in last for marker in silence_markers):
            return "silent"
        return "speak"

    def _check_character_alignment(self, response: str) -> bool:
        """Reject replies that drift outside the persona's voice and role."""
        # Task 4: this is the guard against the model drifting out of character.
        # It catches meta replies like "I am an AI" before the text reaches the
        # shared conversation.
        text = response.strip().lower()
        if not text:
            return False
        if self.name.lower() in text:
            return True
        if any(marker in text for marker in ("i am an ai", "as an ai", "i am a language model", "i cannot")):
            return False
        return True

    def _private_memory(self) -> str:
        """Return facts known only to this agent, not shared with other personas."""
        # Task 5: keep agent-specific knowledge separate from what other personas
        # hear in the public conversation.
        return self.spec.memory.strip()

    def respond(self, transcript: List["Turn"], max_tokens: int = 1024) -> str:  # noqa: F821
        """
        Produce this character's next line.

        The transcript is rewritten from this agent's point of view: its own past
        lines become `assistant` turns and everyone else's become `user` turns.
        That is what makes the model feel like a participant rather than an
        observer reading a script.
        """
        # Task 3 continuation: handle the control actions before the model is
        # asked to generate a response. Silent, pause, and end requests are not
        # just dialogue turns; they change the flow of the conversation itself.
        decision = self.decide_response(transcript)
        if decision == "silent":
            return ""
        if decision == "pause":
            return "Let's pause here and come back when we need to."
        if decision == "end":
            return "I agree. Let's end the conversation here."

        recent = transcript[-self.max_context_turns:] if transcript else []
        messages: List[dict] = []

        summary = self._context_summary(transcript)
        if summary:
            messages.append({"role": "user", "content": summary})

        for turn in recent:
            if turn.speaker == self.name:
                messages.append({"role": "assistant", "content": turn.text})
            else:
                messages.append({"role": "user", "content": f"{turn.speaker}: {turn.text}"})

        # The API requires the first message to be from the user, and consecutive
        # same-role turns get merged, so an empty or assistant-first transcript
        # needs an opener.
        if not messages or messages[0]["role"] != "user":
            messages.insert(0, {"role": "user", "content": "(begin the conversation)"})

        private = self._private_memory()
        if private:
            messages.insert(0, {"role": "user", "content": f"Private context for {self.name}: {private}"})

        response = self.llm.complete(self.system_prompt(), messages, max_tokens=max_tokens)
        if not self._check_character_alignment(response):
            return "I need to stay in character."
        return response


def agent_from_spec(spec: PersonaSpec, llm: LLM) -> PersonaAgent:
    """Convenience constructor, so callers don't import the dataclass directly."""
    return PersonaAgent(spec=spec, llm=llm)


# =============================================================================
# YOUR TASK
# =============================================================================
#
#  1. Agents have no memory between conversations. Run the same doctor twice and
#     they will not remember the first patient. Where should that memory live —
#     back in the .md file, or somewhere new?
#
#  2. Every turn re-sends the entire transcript. A long conversation gets
#     expensive and eventually hits the context window.
#
#  3. `respond()` cannot decide to stay quiet, ask for a pause, or end the
#     conversation. Every agent speaks every time it is asked.
#
#  4. Nothing stops an agent breaking character, and nothing detects it when it
#     happens. What would a check look like?
#
#  5. There is no notion of what an agent knows privately versus what has been
#     said out loud. A doctor and a patient should not share a memory.
