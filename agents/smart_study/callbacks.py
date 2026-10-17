"""Callbacks handle validation and loop control; the agents do the planning."""

import json
from datetime import datetime, timedelta, timezone

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .checks import check_plan, check_requirements, render_plan
from .schemas import Requirements, Review, StudyPlan


def read_record(schema, value):
    return schema.model_validate_json(value) if isinstance(value, str) else schema.model_validate(value)


def message(text):
    return types.Content(role="model", parts=[types.Part(text=text)])


def start_request(callback_context: CallbackContext):
    state = callback_context.state
    # Reset this run's intermediate results, including feedback from a prior turn.
    for key in ("requirements", "planning_brief", "topic_analysis", "practice_plan",
                "schedule", "draft_plan", "review"):
        state[key] = ""
    state["review_feedback"] = "First draft: no reviewer feedback yet."
    state["review_passes"] = 0
    state["approved"] = False
    state["input_error"] = ""
    state["today"] = datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat()


def check_input(callback_context: CallbackContext):
    state = callback_context.state
    try:
        req = read_record(Requirements, state["requirements"])
        issues = check_requirements(req)
    except (ValueError, TypeError):
        issues = ["subject, days remaining, level, topics and daily study hours"]
    if issues:
        text = "Before I make the plan, please provide or correct: " + "; ".join(issues) + "."
        state["input_error"] = text
        return message(text)  # Skip the whole planning workflow on incomplete input.


def finish_review(callback_context: CallbackContext):
    state = callback_context.state
    state["review_passes"] = state.get("review_passes", 0) + 1
    try:
        review = read_record(Review, state["review"])
        plan = read_record(StudyPlan, state["draft_plan"])
        req = read_record(Requirements, state["requirements"])
        issues = check_plan(plan, req)
        if not review.approved:
            issues.extend(review.feedback or ["Reviewer requested another revision."])
        issues = list(dict.fromkeys(issues))
    except (ValueError, TypeError):
        issues = ["Return valid structured plan and review records."]
    state["approved"] = not issues
    state["review_feedback"] = json.dumps(issues)
    if not issues:
        callback_context.actions.escalate = True  # Exit the nearest LoopAgent.


def show_final_plan(callback_context: CallbackContext):
    state = callback_context.state
    if state.get("input_error"):
        return message(state["input_error"])
    try:
        plan = read_record(StudyPlan, state["draft_plan"])
        req = read_record(Requirements, state["requirements"])
        feedback = json.loads(state["review_feedback"])
        text = render_plan(plan, req, state["approved"], feedback, state["review_passes"])
    except (ValueError, TypeError):
        text = "I could not produce a valid study plan. Please try the request again."
    return message(text)
