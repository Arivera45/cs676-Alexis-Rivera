"""
orchestrator.py — the agent you talk to.

You type "I want to create a persona patient" and something has to decide that
you meant `create_persona("patient")`. That decision is intent routing, and it
happens here.

The baseline router is regular expressions. It works, it is free, it is
deterministic, and it is obviously not what a modern agent does — a real one
would hand Claude a set of tools and let the model choose. Replacing this router
with genuine tool use is the headline task of this project, and the tool schemas
you would need are sketched at the bottom of this file.

Anything the router does *not* recognize is passed to the model as ordinary
conversation, so the orchestrator still feels like something you are talking to
rather than a command prompt.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .agent import agent_from_spec
from .conversation import Conversation, Turn, run_conversation, save_transcript
from .llm import LLM
from .persona import (
    DEFAULT_PERSONA_DIR,
    PersonaSpec,
    find_persona,
    generate_persona,
    list_personas,
    save_persona,
)

_STAGE_MANAGER_SYSTEM = """You are the stage manager of a persona simulation workshop.

The user builds fictional characters and has them talk to each other. You help them
decide who to create and what those characters should discuss.

Be brief — two or three sentences. When the user seems ready to act, remind them they
can say things like "create a persona doctor", "list personas", or "have them talk
about the test results"."""


@dataclass
class Result:
    """What the orchestrator did, in a form the UI can render."""

    reply: str
    events: List[str] = field(default_factory=list)
    conversation: Optional[Conversation] = None


class Orchestrator:
    """Routes what the user typed to the right part of the package."""

    def __init__(self, llm: LLM, persona_dir: Path = DEFAULT_PERSONA_DIR) -> None:
        self.llm = llm
        self.persona_dir = Path(persona_dir)
        # Task 6: keep a bounded chat transcript so the stage manager stays
        # responsive, and track persona names already known to the session so the
        # router can remember what it has created without depending on a full log.
        self.history: List[dict] = []
        self.persona_memory: List[str] = []
        self._refresh_persona_memory()

    def _refresh_persona_memory(self) -> None:
        """Rebuild the in-memory persona list from the files on disk."""
        self.persona_memory = [f"{spec.name} ({spec.role})" for spec in list_personas(self.persona_dir)]

    def _trim_history(self) -> None:
        """Limit the chat transcript so stale turns do not accumulate forever."""
        if len(self.history) > 20:
            self.history = self.history[-20:]

    @staticmethod
    def _extract_turn_count(text: str) -> int:
        """Allow the user to choose how many turns to generate in a conversation."""
        # Task 5: accept phrases like "for 3 turns" or "5 messages" so the user
        # can control conversation length without changing the router itself.
        for pattern in (
            r"\bfor\s+(\d+)\s+turns?\b",
            r"\b(\d+)\s+turns?\b",
            r"\bfor\s+(\d+)\s+messages?\b",
            r"\b(\d+)\s+messages?\b",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                turns = int(match.group(1))
                return max(1, turns)
        return 6

    # -- intents ------------------------------------------------------------

    def _create_persona(self, description: str) -> Result:
        """Author a persona, write it to disk, and report where it landed."""
        if not description.strip():
            # Task 2: ask for the missing detail instead of silently treating a
            # blank request as a generic fallback message.
            return Result(reply="What kind of person should I create?")

        spec = generate_persona(description, self.llm)
        path = save_persona(spec, self.persona_dir)
        self._refresh_persona_memory()
        return Result(
            reply=f"Created **{spec.name}** ({spec.role}) — {spec.summary}",
            events=[f"wrote {path}"],
        )

    def _list_personas(self) -> Result:
        """Show what is currently in the persona folder."""
        specs = list_personas(self.persona_dir)
        if not specs:
            return Result(reply="No personas yet. Try: create a persona patient")

        lines = [f"- **{s.name}** ({s.role}) — {s.summary}" for s in specs]
        return Result(reply=f"{len(specs)} persona(s) in `{self.persona_dir}`:\n" + "\n".join(lines))

    def _converse(
        self,
        topic: str,
        who: Optional[List[str]] = None,
        turns: int = 6,
        on_turn: Optional[Callable[[Turn], None]] = None,
        on_start: Optional[Callable[[str], None]] = None,
    ) -> Result:
        """Wake up two personas and let them talk."""
        specs: List[PersonaSpec] = []

        if who:
            for name in who:
                found = find_persona(name, self.persona_dir)
                if found is None:
                    return Result(reply=f"I couldn't find a persona matching '{name}'.")
                specs.append(found)
        else:
            # Task 4: don't silently choose the first two when the user has created
            # more than one possible pair; ask which personas should participate.
            available = list_personas(self.persona_dir)
            if len(available) < 2:
                return Result(reply="I need at least two personas before they can talk. Create another one first.")
            if len(available) > 2:
                names = ", ".join(s.name for s in available)
                return Result(
                    reply=(
                        "I found more than two personas. Which two should take part? "
                        f"Available: {names}"
                    )
                )
            specs = available

        agents = [agent_from_spec(s, self.llm) for s in specs]
        if on_start is not None:
            on_start(topic)
        conversation = run_conversation(agents, topic=topic, turns=turns, on_turn=on_turn)
        path = save_transcript(conversation, self.persona_dir, filename="conversation.md")

        return Result(
            reply=f"{len(conversation.turns)} turns between {' and '.join(s.name for s in specs)}.",
            events=[f"wrote {path}"],
            conversation=conversation,
        )

    def _chat(self, text: str) -> Result:
        """Nothing matched, so just talk to the user."""
        # Task 6: keep a compact working memory for the stage manager and surface
        # the personas already known to the session so the router can refer to them
        # even when the conversation log is trimmed.
        self.history.append({"role": "user", "content": text})
        self._trim_history()
        system = _STAGE_MANAGER_SYSTEM
        if self.persona_memory:
            system = f"{system}\nKnown personas: {', '.join(self.persona_memory)}"
        reply = self.llm.complete(system, self.history, max_tokens=512)
        self.history.append({"role": "assistant", "content": reply})
        self._trim_history()
        return Result(reply=reply)

    @staticmethod
    def _tool_schema() -> List[Dict[str, Any]]:
        """Tool definitions the model can choose from when routing a request."""
        # Task 1: this small tool contract lets the model decide between creating
        # personas, listing them, or starting a dialogue without depending on
        # fragile regex ordering in the user message.
        return [
            {
                "name": "create_persona",
                "description": "Create and save a new persona character.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What kind of person to create, such as 'patient with back pain'",
                        }
                    },
                    "required": ["description"],
                },
            },
            {
                "name": "list_personas",
                "description": "List the personas currently saved on disk.",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "start_conversation",
                "description": "Start a conversation between personas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "What the conversation is about"},
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Names of the personas to include",
                        },
                        "turns": {"type": "integer", "description": "How many turns to run"},
                    },
                    "required": ["topic"],
                },
            },
        ]

    @staticmethod
    def _parse_tool_call(text: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON tool call from a model reply."""
        # Task 1 continuation: models often wrap structured results in Markdown
        # fences, so peel off the wrapper before validating the JSON payload.
        candidate = text.strip()
        if not candidate:
            return None

        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1)

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        tool_name = payload.get("tool") or payload.get("name")
        if not isinstance(tool_name, str):
            return None

        arguments = payload.get("arguments") or payload.get("parameters") or {}
        if not isinstance(arguments, dict):
            arguments = {}
        return {"tool": tool_name, "arguments": arguments}

    def _route_with_tools(
        self,
        text: str,
        on_turn: Optional[Callable[[Turn], None]] = None,
        on_start: Optional[Callable[[str], None]] = None,
    ) -> Optional[Result]:
        """Ask the model to choose a tool, then execute it."""
        # Task 1 continuation: prompt the model for a single structured tool call
        # and then dispatch that call to the corresponding orchestrator method.
        schema = json.dumps(self._tool_schema(), indent=2)
        prompt = (
            "Choose exactly one tool and return JSON only with the form "
            "{\"tool\": \"<tool_name>\", \"arguments\": {...}}.\n"
            f"Available tools:\n{schema}\n\n"
            f"User request: {text}"
        )
        response = self.llm.complete(
            system="You are a router for a persona simulation app. Return valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )

        call = self._parse_tool_call(response)
        if call is None:
            return None

        tool_name = call["tool"]
        arguments = call["arguments"]

        if tool_name == "create_persona":
            description = str(arguments.get("description", "")).strip()
            return self._create_persona(description)

        if tool_name == "list_personas":
            return self._list_personas()

        if tool_name == "start_conversation":
            topic = str(arguments.get("topic") or "an initial consultation").strip()
            participants = arguments.get("participants") or []
            if isinstance(participants, str):
                participants = [p.strip() for p in re.split(r"\s+and\s+|,", participants) if p.strip()]
            turns = max(1, int(arguments.get("turns") or 6))
            return self._converse(topic=topic, who=participants or None, turns=turns, on_turn=on_turn, on_start=on_start)

        return self._chat(text)

    # -- routing ------------------------------------------------------------

    def _handle_sequence(
        self,
        text: str,
        on_turn: Optional[Callable[[Turn], None]] = None,
        on_start: Optional[Callable[[str], None]] = None,
    ) -> Result:
        """Run multiple ordered steps in a single request, such as "list personas then talk"."""
        # Task 3: split a chained command on the sequencing word so each action is
        # handled in order instead of letting the first regex match short-circuit
        # the whole input.
        parts = re.split(r"\b(?:then|and then)\b", text, flags=re.IGNORECASE)
        if len(parts) <= 1:
            return self.handle(text, on_turn=on_turn, on_start=on_start)

        results: List[Result] = []
        last_conversation: Optional[Conversation] = None
        for part in parts:
            piece = part.strip()
            if not piece:
                continue
            # Recurse into the normal entry point so the same validation and routing
            # logic applies to each sub-command independently.
            result = self.handle(piece, on_turn=on_turn, on_start=on_start)
            results.append(result)
            if result.conversation is not None:
                last_conversation = result.conversation

        combined = "\n\n".join(result.reply for result in results if result.reply)
        return Result(reply=combined, conversation=last_conversation)

    def handle(
        self,
        text: str,
        on_turn: Optional[Callable[[Turn], None]] = None,
        on_start: Optional[Callable[[str], None]] = None,
    ) -> Result:
        """Use tool selection when the model returns a tool call; otherwise fall back to the legacy route."""
        # Task 1 plus Task 3: prefer the tool-driven router first; if the model
        # fails to emit a valid call, fall back to the older regex route so common
        # natural-language requests still work.
        stripped = text.strip()
        if not stripped:
            return Result(reply="Tell me what you want to do.")

        # Sequence phrases such as "list personas then have them talk" must be
        # resolved before the regex fallback; otherwise the first match wins and
        # the later action is silently ignored.
        if re.search(r"\b(?:then|and then)\b", stripped, flags=re.IGNORECASE):
            return self._handle_sequence(stripped, on_turn=on_turn, on_start=on_start)

        tool_result = self._route_with_tools(stripped, on_turn=on_turn, on_start=on_start)
        if tool_result is not None:
            return tool_result

        lowered = stripped.lower()

        # "create a persona doctor" / "make a persona who is a nurse"
        create = re.search(
            r"(?:create|make|add|build|generate)\s+(?:a\s+|an\s+|new\s+)*persona\s*(?:for|of|who is|that is|:)?\s*(.*)",
            lowered,
        )
        if create:
            return self._create_persona(create.group(1).strip())

        # "list personas" / "who do I have"
        if re.search(r"\b(list|show|what|who)\b.*\bpersona", lowered) or lowered in {"list", "ls"}:
            return self._list_personas()

        # "have them talk about X" / "start a conversation between A and B"
        converse = re.search(
            r"\b(?:talk|conversation|converse|chat|discuss|speak)\b",
            lowered,
        )
        if converse:
            turns = self._extract_turn_count(stripped)
            topic_match = re.search(r"\babout\s+(.*)$", lowered)
            topic = topic_match.group(1).strip() if topic_match else "an initial consultation"
            topic = re.sub(r"\s+(?:for|in)\s+\d+\s+(?:turns?|messages?)\s*$", "", topic, flags=re.IGNORECASE)

            who_match = re.search(r"\bbetween\s+(.*?)(?:\s+about\b|$)", lowered)
            who = None
            if who_match:
                who = [w.strip() for w in re.split(r"\s+and\s+|,", who_match.group(1)) if w.strip()]

            return self._converse(topic=topic, who=who, turns=turns, on_turn=on_turn, on_start=on_start)

        return self._chat(stripped)


# =============================================================================
# YOUR TASK
# =============================================================================
#
#  1. REPLACE THE REGEX ROUTER WITH REAL TOOL USE. This is the main event.
#     Claude supports tool calling: you describe the tools, the model picks one
#     and fills in the arguments. Roughly:
#
#         tools = [
#             {
#                 "name": "create_persona",
#                 "description": "Create and save a new persona character.",
#                 "input_schema": {
#                     "type": "object",
#                     "properties": {
#                         "description": {"type": "string",
#                                         "description": "What kind of person to create"},
#                     },
#                     "required": ["description"],
#                 },
#             },
#             {"name": "list_personas", ...},
#             {"name": "start_conversation", ...},   # participants, topic, turns
#         ]
#
#     Then loop: send the message with `tools=`, and while
#     `response.stop_reason == "tool_use"`, run the requested tool, append a
#     `tool_result` block, and send it back. The model handles "actually, make
#     it two doctors and a nurse, and have them argue about the diagnosis" —
#     which the regexes below will never manage.
#
#  2. The router cannot ask a clarifying question. "Create a persona" with no
#     description gets a canned string instead of "what kind of person?".
#
#  3. Pattern order decides meaning. "list the personas then have them talk"
#     only ever lists.
#
#  4. `_converse` silently picks the first two personas when you do not name
#     anyone, even if you have six.
#
#  5. `turns` is hardcoded to 6 and cannot be set from the conversation.
#
#  6. `self.history` grows without limit and is only used by `_chat`, so the
#     orchestrator has no memory of the personas it created.
