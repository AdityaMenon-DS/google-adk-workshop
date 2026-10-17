# Understand what you are submitting

Start with Task 1. Once you understand how an agent calls a function, Task 2 is
mostly about controlling the order in which several agents work.

## 1. What an agent does

An LLM reads and generates language. A tool is code that does a specific job.
An agent connects the two: it reads your request, chooses a tool when needed,
gets the result, and uses that result in its reply.

For example, with “What is 18% GST on Rs 25,000?”, the flow is:

```text
Your request
    -> Gemini chooses calculate("25000 * 18 / 100")
    -> Python returns 4500
    -> Gemini explains that GST is Rs 4,500
```

The language model chooses the expression. Python performs the arithmetic.
That distinction matters: the tool can calculate correctly even if the model
misunderstands the question. You still need to check that it chose the right inputs.

## 2. Read the personal assistant definition

Open `agents/personal_assistant/agent.py`.

```python
root_agent = Agent(
    name="personal_assistant",
    model=...,
    instruction=...,
    tools=[GoogleSearchTool(...), calculate, analyze_text],
)
```

`root_agent` is the entry point ADK loads. `name` identifies the agent. `model`
chooses the LLM. `instruction` tells it when to use each tool and how to respond.
`tools` lists the actions available to it. These are Python objects, not just
names mentioned in a prompt.

The two functions have typed arguments and docstrings. ADK turns that information
into descriptions the model can use to call the functions with the right inputs.

Search is Google's built-in tool. The `bypass_multi_tools_limit=True` setting lets
ADK combine it with the two custom functions. ADK may internally wrap search in
a helper agent. Our application still defines one personal-assistant agent, with
three registered tools and no manually created search sub-agent.

Try the combined search-and-calculation request in the README. One request can
trigger more than one tool; choosing one does not finish the whole request.

## 3. How the calculator works

Open `tools.py`. `ast.parse` converts an expression into a tree of operations.
For `2 + 3 * 4`, that tree says: multiply 3 by 4, then add 2. `_evaluate` walks
the tree and allows only numbers and the arithmetic operators in `OPERATORS`.

We do not use `eval`, because it could execute arbitrary Python code supplied
as the “expression”. A function call such as `open(...)` is not arithmetic and
is rejected. Very long expressions and huge powers are rejected too.

Useful expressions:

| Request | Expression | Answer |
| --- | --- | --- |
| 18% of 25,000 | `25000 * 18 / 100` | 4,500 |
| Total including GST | `25000 * (1 + 18 / 100)` | 29,500 |
| 10,000 at 8%, compounded annually for 2 years | `10000 * (1 + 8/100)**2` | 11,664 |
| Interest earned in that example | `10000 * (1 + 8/100)**2 - 10000` | 1,664 |

`**` means power. `%` means remainder in Python, not percentage. Floating-point
results can have tiny rounding differences, so money should be displayed to a
sensible number of decimal places. This is an arithmetic demo, not accounting software.

## 4. How text analysis works

`len(text)` counts Unicode code points, including spaces and punctuation.
`text.split()` divides the input at whitespace. We count the resulting tokens
that contain a letter or number. A hyphenated word without spaces counts as one.

For sentences, we split on runs of `.`, `!` or `?` and count segments containing
a letter or number. An unfinished final sentence counts. An empty string counts
as zero characters, zero words and zero sentences.

The workshop sentence is:

```text
Google ADK helps developers build AI agents.
```

Its seven words are Google / ADK / helps / developers / build / AI / agents.
It has 37 letters, six spaces and one full stop: 44 characters.

The rule is intentionally simple. `Dr. Rao arrived.` would be counted as two
sentences. That limitation is documented rather than hidden. A more advanced
version could use a sentence tokenizer, but it would add dependencies and rules.

## 5. Why SmartStudy has several agents

The student supplies five kinds of information: subject, time until the exam,
current level, topics and daily availability. Different agents handle different
planning jobs:

| Role | Job | Saved result |
| --- | --- | --- |
| Coordinator | Extract the student's constraints | `requirements` |
| Planning | Prepare a shared brief | `planning_brief` |
| Topic | Rank topics and identify study focus | `topic_analysis` |
| Practice | Choose problem counts and practice types | `practice_plan` |
| Schedule | Allocate time across days | `schedule` |
| Writer | Combine the analyses into one plan | `draft_plan` |
| Reviewer | Find problems or approve the draft | `review` |

The brief says six agents once, but lists these seven roles. The implementation
follows the complete list.

## 6. The three workflow patterns

```text
Coordinator
    |
Input validation
    |
Planning
    |
    +------------+-------------+
    |            |             |
  Topic       Practice      Schedule      <- parallel
    |            |             |
    +------------+-------------+
                 |
               Writer
                 |
              Reviewer
                 |
          Python constraint checks
                 |
     approved? --+-- yes --> final display
                 |
                 no
                 |
        Writer again, if only one pass used
```

**SequentialAgent** runs its children in order. The planning brief must exist
before the analyses start. The writer must wait until those analyses finish.

**ParallelAgent** starts Topic, Practice and Schedule independently. Each reads
the same requirements and planning brief. Each writes to a different state key,
so one does not overwrite another's answer. There is no promised completion order.

**LoopAgent** runs Writer then Reviewer. If the first draft fails, the writer
gets the feedback and tries once more. `max_iterations=2` is a hard limit on
writer/reviewer passes. Approval sets `actions.escalate = True`, which tells
the loop to stop early. It is a control signal here, not a request for a person.

## 7. How the agents share information

Session state is a dictionary belonging to the conversation. Setting
`output_key="topic_analysis"` saves that agent's answer in state. A later
instruction containing `{topic_analysis}` receives the saved answer.

This is why merely naming several agents would not be enough: you also need to
connect their inputs and outputs. The writer explicitly reads all three analysis
results and the review feedback. The independent analyses use
`include_contents="none"`; they receive their explicit instructions and state
instead of relying on each other's conversation messages.

The coordinator, writer and reviewer use Pydantic schemas. A schema describes
the shape of a record: for example, each study block needs minutes, an activity,
topic names, a block type and a problem count. Structured output makes those
fields easier for Python to validate than a free-form paragraph.

Session state is not permanent memory. The README's web command stores sessions
in memory; stopping the server loses them. At the start of each new planning
request, the callbacks also clear prior draft and review state so old feedback
does not leak into the next plan.

## 8. What the checks add

The reviewer judges realism and usefulness: can somebody actually do those tasks
in the time allowed? Python checks the measurable rules as well:

- The requested days appear exactly once and in order.
- Each day stays within the daily minute budget, including breaks.
- Every topic is covered and has a practice block with a positive problem count.
- Revision and a mock test exist.
- The last day has revision and no new-concept block.

For the example, `3 * 60 = 180` minutes per day and `10 * 180 = 1800` minutes
overall. A 200-minute day fails even if another day is only 160 minutes: the
student said three hours **per day**, not just thirty hours in total.

Python cannot prove that a task is educationally useful just because its label
says “Graphs”. The reviewer checks whether activities match labels, whether
problem counts are sensible and whether practice targets are met. These semantic
judgments still need a live model run and your own inspection.

Callbacks are ordinary functions ADK calls at specific points. Here they reset
state, reject incomplete input, check reviews and format the final plan. The final
formatting callback does not make another model call.

## 9. What the offline tests do and do not prove

The tests call the actual calculator and text tool. They also run the real ADK
workflow using a scripted replacement for Gemini. That replacement supplies
known records, letting us deliberately test good drafts and bad drafts.

For example, one test supplies a 500-minute block while the scripted reviewer
approves it. Python must still reject it, send feedback to the writer, and request
another pass. Another test keeps the plan invalid and checks that the loop stops
after two passes with an honest draft warning.

The parallel test checks that all three analysis calls overlap, not just that
three agents appear in the source. Other tests check fresh state on a second
request, missing-input handling, agent discovery and the web page response.

These tests do not prove live tool selection, Google Search grounding, model
availability or the quality of a real generated study plan. That is what the
README's live checks and the required screenshots are for.

## 10. Practice explaining it aloud

Try answering these before reading the answer column. They are revision questions,
not the unseen questions from the certification form.

| Question | Short answer |
| --- | --- |
| 1. What is an LLM? | A model that processes and generates language. |
| 2. What does an API do? | Lets one program request a service from another. |
| 3. What does ADK provide? | Agent definitions, tools, execution, sessions and workflows. |
| 4. What makes this assistant an agent? | It can choose tools, use their results and continue the task. |
| 5. Why use a calculator tool? | Python executes the arithmetic instead of relying on generated numbers. |
| 6. Why avoid eval? | It can execute arbitrary code, not just arithmetic. |
| 7. Does % mean percentage in Python? | No; it means remainder. Divide a percentage by 100. |
| 8. Why give a tool a docstring? | ADK exposes its purpose and arguments to the model. |
| 9. What is root_agent? | The agent object ADK loads as the app's entry point. |
| 10. What is a session? | One conversation and its associated events and state. |
| 11. What does output_key do? | Saves an agent's output under a named state key. |
| 12. Why use sequential execution? | Later steps depend on earlier outputs. |
| 13. Why run the three analyses in parallel? | They share inputs but do not depend on each other. |
| 14. Why use different state keys? | To prevent parallel results from overwriting each other. |
| 15. What does the loop repeat? | The writer and reviewer, at most twice. |
| 16. What stops it early? | Approval sets the escalation flag for the LoopAgent. |
| 17. What if the second draft still fails? | Show it as a draft with unresolved issues. |
| 18. What is a callback? | A function ADK invokes at an execution lifecycle point. |
| 19. What is RAG? | Retrieving relevant material and supplying it to a model before it answers. |
| 20. Why omit .env from the ZIP? | It can contain your private API key. |

## 11. Make one small change yourself

Run `calculate("12500 * 18 / 100")` and predict the answer first: 2250.
Then analyze `One. Two! Three?` and check why the sentence count is three.
For SmartStudy, change the test request to two hours a day and inspect whether
every generated day stays within 120 minutes. These small experiments help you
explain the code from understanding rather than memorizing a script.

Read the code in this order: personal assistant `agent.py`, `tools.py`, SmartStudy
`agent.py`, `schemas.py`, then `callbacks.py` and `checks.py`.

References: [ADK tool limitations](https://adk.dev/tools/limitations/),
[Google ADK Python source](https://github.com/google/adk-python), and
[Gemini models](https://ai.google.dev/gemini-api/docs/models).
