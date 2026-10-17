"""Task 2: sequential preparation, parallel analysis, then two review passes."""

import os

from google.adk.agents import Agent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

from .callbacks import check_input, finish_review, show_final_plan, start_request
from .schemas import Requirements, Review, StudyPlan


def build_agent(model=None):
    """A factory also lets the offline tests substitute a scripted model."""
    if model is None:
        model = Gemini(
            model=os.getenv("SMART_STUDY_MODEL") or os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            retry_options=types.HttpRetryOptions(
                attempts=4, initial_delay=15, max_delay=60, exp_base=2,
                http_status_codes=[429, 500, 502, 503, 504],
            ),
        )

    coordinator = Agent(
        name="coordinator", model=model, output_key="requirements",
        output_schema=Requirements,
        instruction="""Extract the student's subject, days remaining, current level,
        topics and hours per day from the conversation, prioritizing the newest
        request. Today in India is {today}; convert an exam date to days remaining
        if needed. Preserve topic names consistently. Do not invent missing values:
        use empty strings/lists or zero and list their names in missing_fields.
        If everything is supplied, missing_fields is empty. Output only the schema.
        """,
    )
    planning = Agent(
        name="planning", model=model, output_key="planning_brief",
        instruction="""Prepare a short planning brief from {requirements}.
        State total available minutes, the daily limit, the student's level,
        topic dependencies and the goals for the topic, practice and schedule
        analyses. Reserve time for daily revision, a mock test and final review.
        Do not change the student's constraints. The framework starts the three
        independent analyses after your brief is saved.
        """,
    )
    topic = Agent(
        name="topic", model=model, output_key="topic_analysis", include_contents="none",
        instruction="""Requirements: {requirements}. Brief: {planning_brief}.
        For EVERY topic, give High/Medium/Low priority, difficulty and specific
        study focus appropriate for the level. Explain the priority briefly.
        Use the exact topic names supplied. These are suggested priorities,
        not claims about an official exam's marks or syllabus weightage.
        """,
    )
    practice = Agent(
        name="practice", model=model, output_key="practice_plan", include_contents="none",
        instruction="""Requirements: {requirements}. Brief: {planning_brief}.
        Recommend a realistic number and type of practice questions for EVERY
        topic: concept questions, coding, mixed practice. Include a timed mock.
        For the workshop's 10-day intermediate Data Structures example, use
        Arrays 5, Linked Lists 5, Trees 8, Graphs 8, Dynamic Programming 10 as
        starting targets; adjust if the student's actual budget requires it.
        Give representative tasks and allow time to review incorrect answers.
        """,
    )
    schedule = Agent(
        name="schedule", model=model, output_key="schedule", include_contents="none",
        instruction="""Requirements: {requirements}. Brief: {planning_brief}.
        Draft a day-wise time allocation within the daily minute limit. Include
        concept work, practice and revision. Put a timed mock before the final
        day where possible. The final day is for revision and exam preparation,
        not new material. You run independently of the topic and practice agents;
        the writer will reconcile all three outputs.
        """,
    )
    writer = Agent(
        name="study_plan_writer", model=model, output_key="draft_plan",
        output_schema=StudyPlan, include_contents="none",
        instruction="""Write a practical study plan using:
        Requirements: {requirements}
        Planning brief: {planning_brief}
        Topic analysis: {topic_analysis}
        Practice targets: {practice_plan}
        Schedule: {schedule}
        Previous draft: {draft_plan}
        Reviewer feedback: {review_feedback}

        Output the StudyPlan schema. Give exactly the requested number of days,
        numbered from 1. Each block has positive integer minutes, an activity,
        exact relevant topic names, and a nonnegative integer problem count.
        Use zero problems for blocks without questions. Keep each day's total
        at or below hours_per_day * 60, including any breaks. Cover and practice
        every topic; include revision and a timed mock. The final day includes
        revision and no new concept block. Distribute the practice targets
        across days without double-counting them. Make tasks specific enough
        to follow, such as implementing BFS and tracing its queue.
        If feedback exists, fix every listed issue. Write naturally and avoid
        motivational filler. Mention sensible adjustments in notes.
        """,
    )
    reviewer = Agent(
        name="reviewer", model=model, output_key="review", output_schema=Review,
        include_contents="none", after_agent_callback=finish_review,
        instruction="""Review this draft: {draft_plan}
        Requirements: {requirements}. Practice targets: {practice_plan}.
        Topic guidance: {topic_analysis}.
        Check all topics, each day's total minutes, sufficient practice for
        each topic, revision, a timed mock and appropriate final-day preparation.
        Check whether the actual activities match the topic labels and level,
        and whether the assigned problem counts fit the minutes available.
        Return approved=true and empty feedback only when all checks pass.
        Otherwise give specific corrections. Do not rewrite the plan yourself.
        """,
    )
    analyses = ParallelAgent(name="parallel_analysis", sub_agents=[topic, practice, schedule])
    review_loop = LoopAgent(
        name="write_and_review", sub_agents=[writer, reviewer], max_iterations=2,
    )
    workflow = SequentialAgent(
        name="planning_workflow", before_agent_callback=check_input,
        sub_agents=[planning, analyses, review_loop],
    )
    return SequentialAgent(
        name="smart_study", sub_agents=[coordinator, workflow],
        before_agent_callback=start_request, after_agent_callback=show_final_plan,
    )


root_agent = build_agent()
