> For a task-by-task outline of completed work, see [`src/personaforge/Outline.md`](src/personaforge/Outline.md).

# PersonaForge Project Report

**Course:** CS676 Algorithms for Data Science  
**Project:** Project 2 — PersonaForge  
**Date:** November 13, 2026

## 1. Project overview

PersonaForge is a Python command-line application for creating fictional personas
and having them converse. A persona is stored as a Markdown file, an agent combines
that persona with a language model, and the orchestrator routes user requests to
persona creation, listing, or conversation actions.

The project extends the supplied package with model-assisted request routing,
clarifying and ambiguity responses, persistent persona metadata, bounded context,
conversation control heuristics, and a scripted offline mode for tests and demos.
The scope is a small local simulation tool, not a clinical system or a general
autonomous-agent framework.

## 2. Architecture

The package uses a `src/personaforge/` layout. The root `main.py` is a thin entry
point; application logic remains in the package.

- **`cli.py` and `ui.py`:** Load environment settings, parse command-line options,
  run the interactive terminal loop, and render prompts, responses, and errors.
- **`llm.py`:** Defines the shared `LLM` protocol, the Anthropic-backed `ClaudeLLM`,
  the call-recording `ScriptedLLM` for tests, and `DemoLLM` for offline use.
- **`persona.py`:** Defines `PersonaSpec`, generates personas from model output,
  serializes persona metadata and body to Markdown, and loads, lists, finds, and
  saves persona files.
- **`agent.py`:** Builds an in-character prompt, prepares the conversation context,
  provides memory and response-control helpers, and applies a basic output guard.
- **`conversation.py`:** Runs a fixed round-robin exchange, emits turns to the UI,
  renders transcripts, and saves them.
- **`orchestrator.py`:** Routes user requests, dispatches supported actions, asks for
  missing details or participant choices, and retains bounded stage-manager history.

### Request and conversation flow

1. The CLI passes a user message to `Orchestrator.handle()`.
2. The orchestrator asks the model to return a JSON request matching one of three
   tool-like schemas: create a persona, list personas, or start a conversation.
   The application parses and dispatches that JSON itself; this is prompt-based
   routing, not Anthropic's native tool-use API.
3. If the response is not a recognized request, the orchestrator uses a
   regular-expression fallback for common commands or sends the text to the
   stage-manager chat path.
4. For a conversation, each agent receives the shared transcript rewritten from
   its point of view. Its own previous lines are assistant messages, while other
   speakers' lines are user messages.
5. The conversation is rendered in the terminal and written to
   `temp/conversation.md` by default.

## 3. Implemented behavior and design choices

- **Model abstraction:** Tests and offline use do not require a key or network
  access. Online mode uses `ClaudeLLM`; the selected model can be overridden with
  `--model`.
- **Persona files:** Persona metadata and body are stored in Markdown. The schema
  includes an optional memory field, and the parser tolerates a missing closing
  frontmatter fence and model output wrapped in a code fence.
- **Routing:** The model-selected JSON request supports persona creation, listing,
  and conversation startup. A legacy regex path remains as a fallback. Blank
  creation requests ask what kind of persona is wanted; chained commands are split
  and handled in order.
- **Participant and turn handling:** The user can specify the turn count. When more
  than two personas exist and participants are omitted, the application asks which
  personas should participate rather than silently selecting the first two.
- **Bounded context:** The agent keeps a recent-turn window and summarizes older
  lines. The stage-manager history is also capped, and known persona names are
  included separately from that chat history.
- **Agent controls and role guard:** Simple phrase checks can choose a speak,
  silence, pause, or end response. A lightweight output check rejects empty replies
  and certain meta-AI phrases.
- **Offline dialogue ordering:** `DemoLLM` now advances its canned dialogue only
  for character replies, not for routing, persona-authoring, or stage-manager calls.
  A regression test covers setup calls before the first dialogue turn.
- **Secret handling:** Online mode reads `ANTHROPIC_API_KEY` from the environment;
  the local `.env` file is intended for development and is ignored by Git. It must
  not be committed or included in this report.

These choices favor a small, testable package and a quick demonstration over a more
complex conversation manager or persistence service.

## 4. Validation and observed demonstrations

### Automated tests

The full test suite was run with:

```powershell
uv run pytest
```

The observed result was **52 passed in 0.33 seconds**. The suite covers the agent,
conversation loop and orchestrator, language-model adapters, and persona parsing and
storage. Tests use scripted responses so they do not call the paid API.

### Manual behavior checks

- In offline mode, a blank persona request returned a clarifying question.
- When several personas existed and none were named for a conversation, the
  orchestrator asked which participants to use.
- A request naming an unknown persona returned a not-found message.
- An online run successfully created **Dr. Elena Park** and **Ava Thompson**, then
  produced a conversation saved to `temp/conversation.md`.
- The current online transcript is two turns. Dr. Park opens by asking about the
  listener's concerns; Ava responds at length with stage directions and speaks as
  though a patient is present, even though the listed participants are Dr. Park and
  Ava. This confirms that generation and saving work, while also showing that the
  output does not consistently stay within the intended interaction or role.

The `0 turns` edge case was not isolated: the test command encountered the
multiple-persona selection prompt first, so that run does not establish how zero is
handled in an otherwise valid conversation.

## 5. Failure analysis and remaining limitations

The project is functional, but several behaviors remain heuristic or incomplete:

- **Role and content drift:** The output guard looks for a short list of meta-AI
  phrases; it does not judge whether the response fits the persona's role, whether
  it speaks for another participant, or whether stage directions appear. The
  online transcript demonstrates this limitation.
- **Routing limitations:** Routing depends on the model returning parseable JSON.
  The regex fallback only recognizes common phrasings. It is not a general natural
  language command parser, and the router does not use native provider tool calls.
- **Persona lookup and file collisions:** `find_persona()` accepts substring
  matches, which can select the wrong persona. Saving two personas with the same
  slug overwrites the existing file.
- **Persona validation and editing:** Generated Markdown is parsed with a small
  custom parser and receives only a minimal fallback when the name is missing.
  There is no strict validation of required sections and no in-app persona editor.
- **Memory persistence:** The persona schema can serialize memory, and an agent can
  add a fact to its in-memory spec. A conversation does not automatically extract
  memories or save them back to the persona file.
- **Conversation policy:** Speakers take fixed round-robin turns and the loop ends
  after a fixed count. The response-control heuristics return pause/end text but do
  not make the conversation loop stop early. There is no observer or evaluator to
  decide whether the topic was resolved.
- **Transcript retention:** The default filename is always `conversation.md`, so a
  later conversation can replace the earlier transcript.
- **API and runtime failures:** The missing-key error gives setup guidance, and the
  CLI displays exceptions rather than closing the interactive session. There are
  no automatic retries or recovery of an interrupted conversation's partial turns.
- **Cost:** Online routing, persona generation, and each generated conversation
  turn may each require a paid model call. Shorter conversations and the offline
  mode reduce cost during development.

The remaining numbered task comments in the source files should be read as design
notes or known limitations where applicable, not as evidence that every listed
issue has been implemented.

## 6. Running the application

From the project directory:

```powershell
uv sync
uv run main.py --offline
```

Offline mode requires no key and uses scripted persona and dialogue responses. For
online use, put `ANTHROPIC_API_KEY=...` in a private `.env` file in the project
directory, then run:

```powershell
uv run main.py --model claude-haiku-4-5
```

Do not commit `.env`; keep `.env.example` as a placeholder template. Model calls
may incur charges.

## 7. Summary

PersonaForge demonstrates a coherent Python package with a terminal interface,
file-backed persona definitions, model-backed persona and dialogue generation,
offline testing, and saved transcripts. The full automated suite passes, and an
online end-to-end run was completed. Its strongest current limitations are
semantic role adherence, ambiguous persona lookup, overwritten persona/transcript
files, and the lack of conversation-level evaluation or failure recovery. These
limitations define the next improvements and are important qualifications when
presenting the system's results.
