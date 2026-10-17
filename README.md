# Google ADK Workshop

Two Python projects built with Google's Agent Development Kit: a personal
assistant with tools and a multi-agent study planner.

## Projects

### Personal assistant

One agent selects between three tools:

- Google Search for external information.
- A custom arithmetic calculator with an AST-based parser.
- A text analyzer that counts characters, words and sentences.

The calculator rejects function calls and other non-arithmetic input. Text
counting uses simple, documented rules; abbreviations can affect sentence counts.

### SmartStudy

Creates a study plan from a subject, exam timeline, current level, topic list and
daily time budget. Seven specialized agents work through three ADK patterns:

```text
Coordinator -> Planning -> [Topic | Practice | Schedule] -> Writer -> Reviewer
                                parallel                    ^          |
                                                            +----------+
                                                         maximum 2 passes
```

The agents share results through session state. Pydantic schemas structure the
requirements, plan and review. Python checks day numbering, daily minutes, topic
coverage, practice, revision and a mock test. If unresolved issues remain after
two passes, the final result is labelled as a draft.

## Setup

Use Python 3.11 or newer. From this repository's root, on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item agents/personal_assistant/.env.example agents/personal_assistant/.env
Copy-Item agents/smart_study/.env.example agents/smart_study/.env
```

Edit each `.env` file and replace the key placeholder with your own Gemini API
key from [Google AI Studio](https://aistudio.google.com/apikey). Do not commit the
actual `.env` files. Both agents need access to a key.

Start the local development UI:

```powershell
.\.venv\Scripts\adk.exe web agents --port 8000 --no_use_local_storage
```

Open `http://localhost:8000`, select an agent and start a conversation. Keep the
terminal running. Sessions are temporary and disappear when the server stops.

On macOS/Linux, create the environment with `python3 -m venv .venv`, use `cp`
instead of `Copy-Item`, and replace `.\.venv\Scripts\python.exe` and
`.\.venv\Scripts\adk.exe` with `.venv/bin/python` and `.venv/bin/adk`.

## Examples

Personal assistant:

```text
Calculate 18% of 50,000, then count the characters, words and sentences in:
Google ADK helps developers build AI agents.
```

Expected calculation: 9,000. Expected counts: 44 characters, 7 words, 1 sentence.

```text
Search for information about Google ADK and include source links.
```

SmartStudy:

```text
I have a Data Structures exam in 10 days.
My current level is Intermediate.
Topics: Arrays, Linked Lists, Trees, Graphs, Dynamic Programming.
I can study for 3 hours per day.
Create a preparation plan for me.
```

## Models and service limits

The personal assistant defaults to `gemini-3.8-flash`. The SmartStudy settings
template selects `gemini-3.5-flash-lite`, which completed the live study-plan demo.
`SMART_STUDY_MODEL` overrides SmartStudy's model without changing the assistant.

Google Search access depends on the model and API billing tier. In the local
demo, calculation and text analysis succeeded, but Search on the free-tier
Gemini 3.8 Flash project returned a quota error. Search remains implemented but
has not been verified successfully in that account. Check Google's current
[pricing and feature availability](https://ai.google.dev/gemini-api/docs/pricing)
before running it.

SmartStudy retries transient HTTP errors with increasing delays, up to four
total attempts. This cannot fix a missing key, inaccessible model or exhausted
daily quota. A multi-agent run uses multiple model requests.

ADK is pinned to 2.11.0. Its SequentialAgent, ParallelAgent and LoopAgent classes
are retained for the workshop, although that version marks them deprecated.

## Tests

```powershell
.\.venv\Scripts\python.exe run_tests.py
```

The 13 offline tests cover arithmetic, invalid inputs, text counting, tool
configuration, ADK Web discovery, sequential and parallel execution, state
passing, review feedback, early exit, the two-pass limit and missing input.
Workflow tests use scripted model responses and require no API key. They do not
replace live checks of model quality or Google Search.

## Code map

| Path | Purpose |
| --- | --- |
| `agents/personal_assistant/agent.py` | Assistant instructions and three tools |
| `agents/personal_assistant/tools.py` | Calculator and text analyzer |
| `agents/smart_study/agent.py` | Seven agent roles and workflow containers |
| `agents/smart_study/schemas.py` | Structured inputs and outputs |
| `agents/smart_study/checks.py` | Plan validation and formatting |
| `agents/smart_study/callbacks.py` | State initialization and review control |
| `tests/` | Offline tests |

See [LEARN.md](LEARN.md) for a walkthrough and exercises, and
[OPTIONAL_CLOUD_RUN.md](OPTIONAL_CLOUD_RUN.md) for deployment preparation.
Cloud Run deployment has not been performed or verified.
