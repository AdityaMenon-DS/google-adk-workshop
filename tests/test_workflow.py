"""Real ADK execution with scripted model responses; no API calls or credentials."""

import asyncio
import json
import unittest

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr

from smart_study.agent import build_agent
from smart_study.checks import check_plan
from smart_study.schemas import Requirements, StudyPlan


REQUEST = dict(subject="Data Structures", days=10, level="Intermediate",
               topics=["Arrays", "Linked Lists", "Trees", "Graphs", "Dynamic Programming"],
               hours_per_day=3, missing_fields=[])


def example_plan():
    """A test fixture, not a claimed Gemini result."""
    days = []
    for index in range(10):
        topic = REQUEST["topics"][index % 5]
        blocks = [dict(kind="practice", topics=[topic], minutes=100,
                       activity=f"Solve and check {topic} problems.", problems=3),
                  dict(kind="revision", topics=[topic], minutes=40,
                       activity=f"Review {topic} mistakes.", problems=0)]
        if index == 8:
            blocks[0]["kind"] = "mock"
        days.append(dict(day=index + 1, blocks=blocks))
    return dict(title="Data Structures preparation", days=days, notes=[])


class ScriptedModel(BaseLlm):
    model: str = "offline-test-model"
    fail_first: bool = False
    always_fail: bool = False
    missing_input: bool = False
    _calls: list = PrivateAttr(default_factory=list)
    _reviews: int = PrivateAttr(default=0)
    _writers: int = PrivateAttr(default=0)
    _active: int = PrivateAttr(default=0)
    _peak: int = PrivateAttr(default=0)
    _writer_prompts: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        instruction = str(llm_request.config.system_instruction)
        schema = llm_request.config.response_schema
        if schema is Requirements:
            name = "coordinator"
            value = dict(REQUEST)
            if self.missing_input:
                value["hours_per_day"] = 0
                value["missing_fields"] = ["daily study hours"]
        elif schema is StudyPlan:
            name = "writer"
            self._writers += 1
            self._writer_prompts.append(instruction)
            value = example_plan()
            if self.always_fail or (self.fail_first and self._writers == 1):
                value["days"][0]["blocks"][0]["minutes"] = 500
        elif schema and getattr(schema, "__name__", "") == "Review":
            name = "reviewer"
            self._reviews += 1
            # Deliberately approve an invalid draft to test the Python guard.
            value = dict(approved=True, feedback=[])
        else:
            name = ("topic" if "For EVERY topic" in instruction else
                    "practice" if "Recommend a realistic number" in instruction else
                    "schedule" if "Draft a day-wise" in instruction else "planning")
            value = f"{name}_output"
        self._calls.append(name)
        if name in ("topic", "practice", "schedule"):
            self._active += 1
            self._peak = max(self._peak, self._active)
            await asyncio.sleep(0.02)
            self._active -= 1
        text = json.dumps(value) if isinstance(value, dict) else value
        yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


async def run_workflow(model, turns=1):
    sessions = InMemorySessionService()
    root = build_agent(model)
    runner = Runner(agent=root, app_name="smart_study", session_service=sessions)
    session = await sessions.create_session(app_name="smart_study", user_id="tester")
    output = []
    try:
        for _ in range(turns):
            output = []
            async for event in runner.run_async(
                user_id="tester", session_id=session.id,
                new_message=types.Content(role="user", parts=[types.Part(text="Create my plan.")]),
            ):
                if event.content:
                    output.extend(part.text for part in event.content.parts if part.text)
        saved = await sessions.get_session(app_name="smart_study", user_id="tester",
                                           session_id=session.id)
        return saved.state, output
    finally:
        await runner.close()


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_sequence_parallel_state_and_early_exit(self):
        model = ScriptedModel()
        state, output = await run_workflow(model)
        self.assertEqual(model._calls[:2], ["coordinator", "planning"])
        self.assertEqual(set(model._calls[2:5]), {"topic", "practice", "schedule"})
        self.assertEqual(model._calls[5:], ["writer", "reviewer"])
        self.assertEqual(model._peak, 3)
        self.assertEqual(state["review_passes"], 1)
        self.assertTrue(state["approved"])
        for key in ("topic_output", "practice_output", "schedule_output"):
            self.assertIn(key, model._writer_prompts[0])
        self.assertIn("Day 10", output[-1])

    async def test_second_pass_receives_feedback_and_repairs(self):
        model = ScriptedModel(fail_first=True)
        state, _ = await run_workflow(model)
        self.assertEqual(model._reviews, 2)
        self.assertTrue(state["approved"])
        self.assertIn("Day 1 must fit the daily time budget", model._writer_prompts[1])

    async def test_hard_limit_does_not_mislabel_a_bad_plan(self):
        model = ScriptedModel(always_fail=True)
        state, output = await run_workflow(model)
        self.assertEqual(model._reviews, 2)
        self.assertFalse(state["approved"])
        self.assertIn("Draft", output[-1])
        self.assertIn("issues remain", output[-1])

    async def test_missing_input_skips_planning(self):
        model = ScriptedModel(missing_input=True)
        state, output = await run_workflow(model)
        self.assertEqual(model._calls, ["coordinator"])
        self.assertEqual(state["review_passes"], 0)
        self.assertIn("daily study hours", output[-1])

    async def test_new_turn_resets_review_state(self):
        model = ScriptedModel()
        state, _ = await run_workflow(model, turns=2)
        self.assertEqual(model._reviews, 2)
        self.assertEqual(state["review_passes"], 1)
        self.assertIn("First draft: no reviewer feedback yet", model._writer_prompts[1])


class PlanChecks(unittest.TestCase):
    def test_missing_day_topic_practice_revision_and_mock_are_reported(self):
        raw = example_plan()
        raw["days"] = raw["days"][:1]
        raw["days"][0]["blocks"] = [dict(kind="concept", topics=["Arrays"], minutes=181,
                                          activity="Read arrays", problems=0)]
        issues = " ".join(check_plan(StudyPlan.model_validate(raw), Requirements(**REQUEST)))
        for phrase in ("days 1 through 10", "daily time budget", "Cover these topics",
                       "Add practice", "revision", "mock", "new concepts"):
            self.assertIn(phrase, issues)


if __name__ == "__main__":
    unittest.main()
