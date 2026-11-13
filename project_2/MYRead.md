Notes added to the project by file.

## [src/personaforge/orchestrator.py](./src/personaforge/orchestrator.py)
- Task 6: the bounded chat transcript and in-memory persona registry so the orchestrator remembers known personas without letting history grow without limit
- Task 5: the turn-count parsing for phrases like "for 3 turns" and "5 messages"
- Task 1: the tool schema used for persona creation, listing, and conversation routing
- Task 1: the JSON tool-call parsing that strips Markdown code fences before validation
- Task 1: the tool-dispatch flow that routes model-selected actions to the orchestrator methods
- Task 1: the fallback legacy regex routing path that remains as a safety net
- Task 2: the clarifying question for blank persona-creation requests
- Task 3: the ordered sequence handling for commands such as "list personas then have them talk"
- Task 4: the multi-persona disambiguation when more than two personas exist and the user has not named participants
- Task 6: the persona-memory refresh after saving a new persona and the bounded-history trim used before prompting the stage manager

## [src/personaforge/agent.py](./src/personaforge/agent.py)
- Task 1: the persistent persona memory kept with the agent so the same character can remember facts across conversations
- Task 2: the transcript summarization in `PersonaAgent.respond()`, which keeps only the recent turns plus a brief earlier-context summary so long conversations do not keep sending the full history on every turn
- Task 3: the decision logic that lets an agent choose to speak, remain silent, ask for a pause, or end the conversation based on the latest turn rather than always replying
- Task 3: the explicit `decide_response()` policy and the pre-model control-flow checks that handle pause/end/silent requests before generating new dialogue
- Task 4: the character-alignment guard in `_check_character_alignment()`, which rejects out-of-character meta replies like "I am an AI language model" before they are returned to the conversation
- Task 5: the private-memory hook in `_private_memory()`, which keeps facts hidden from other agents while still passing them to the correct persona during its turn

## [src/personaforge/persona.py](./src/personaforge/persona.py)
- Task 1: the loose `find_persona()` lookup logic, which matches on substrings and can confuse two personas with similar names or roles unless an exact match or disambiguation rule is enforced
- Task 2: the slug-based save path, which overwrites a prior `.md` file whenever two personas share a normalized name and therefore silently destroys earlier state
- Task 3: the frontmatter parser, which tolerates a missing closing fence but still assumes a tiny fixed key set and will mis-handle values containing punctuation or malformed metadata
- Task 4: the generation flow in `generate_persona()`, which never validates that the model emitted a real persona structure before accepting the output
- Task 5: the lack of inline editing support, so a persona can only be changed by directly opening the markdown file instead of an in-app mutation command
- Task 6: the absence of persona mutation during an active conversation, meaning the character cannot learn and update its own stored memory as the exchange evolves
- the agent memory stored with the persona markdown, so a character can retain facts across conversations by keeping them in the `.md` file rather than in a separate store
- the extra persona metadata used to persist remembered facts across runs

## [src/personaforge/llm.py](./src/personaforge/llm.py)
- Fixed the offline dialogue sequence so router, persona-author, and stage-manager calls do not consume canned character lines and scramble who appears to say them
- Added a regression test in `tests/test_llm.py` that makes setup calls before the first dialogue turn and verifies the scripted sequence starts correctly

## [src/personaforge/conversation.py](./src/personaforge/conversation.py)
- Task 1: the strict round-robin turn logic and the design question of whether the next speaker should be chosen by rules or by a model
- Task 2: the fixed-turn stopping rule, which ends after N turns even when the conversation may still be unresolved
- Task 3: the fake "Scene" speaker used to inject the topic, and the cleaner alternative of separating scene metadata from dialogue text
- Task 4: the missing observer/evaluator layer, which could summarize the exchange or judge whether the conversation actually resolved the topic
- Task 5: the transcript writer, which currently reuses one default filename and overwrites earlier run artifacts unless a custom name is given

## Validation
- Ran focused tests: `uv run pytest tests/test_llm.py tests/test_conversation.py -q`
- Result: 28 passed in 0.17s
- Ran syntax checks on `src/personaforge/llm.py` and `tests/test_llm.py`
- Result: no syntax errors
- Ran the focused tests: `cd "d:\cs676-Alexis-Rivera\project_2"; uv run pytest tests/test_agent.py tests/test_conversation.py -q`
- Result: 28 passed in 0.23s
