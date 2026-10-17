"""Check measurable constraints before calling a study plan finished."""

from .schemas import Requirements, StudyPlan


def check_requirements(req: Requirements) -> list[str]:
    issues = list(req.missing_fields)
    if not req.subject.strip():
        issues.append("subject")
    if not req.level.strip():
        issues.append("current level")
    if not req.topics or any(not topic.strip() for topic in req.topics):
        issues.append("topics")
    if not 1 <= req.days <= 60:
        issues.append("days remaining (1 to 60)")
    if not 0 < req.hours_per_day <= 16:
        issues.append("daily study hours (more than 0, at most 16)")
    return list(dict.fromkeys(issues))


def check_plan(plan: StudyPlan, req: Requirements) -> list[str]:
    issues = []
    if [day.day for day in plan.days] != list(range(1, req.days + 1)):
        issues.append(f"Include days 1 through {req.days}, once each and in order.")
    requested = {topic.strip().casefold() for topic in req.topics}
    covered, practiced = set(), set()
    revision = mock = False
    for day in plan.days:
        total = sum(block.minutes for block in day.blocks)
        if not day.blocks or total <= 0 or total > req.hours_per_day * 60 + 1e-6:
            issues.append(f"Day {day.day} must fit the daily time budget.")
        for block in day.blocks:
            if block.minutes <= 0 or block.problems < 0 or not block.activity.strip():
                issues.append(f"Day {day.day} has an invalid or empty study block.")
            topics = {topic.strip().casefold() for topic in block.topics}
            if block.kind != "break":
                covered.update(topics)
            if block.kind == "practice" and block.problems > 0:
                practiced.update(topics)
            revision |= block.kind == "revision"
            mock |= block.kind == "mock"
    if requested - covered:
        issues.append("Cover these topics: " + ", ".join(sorted(requested - covered)))
    if requested - practiced:
        issues.append("Add practice for: " + ", ".join(sorted(requested - practiced)))
    if not revision:
        issues.append("Include revision.")
    if not mock:
        issues.append("Include a timed mock test.")
    if not plan.days or not any(b.kind == "revision" for b in plan.days[-1].blocks):
        issues.append("Include revision on the final day.")
    if plan.days and any(b.kind == "concept" for b in plan.days[-1].blocks):
        issues.append("Keep new concepts off the final day; focus on exam preparation.")
    return list(dict.fromkeys(issues))


def render_plan(plan: StudyPlan, req: Requirements, approved: bool,
                feedback: list[str], passes: int) -> str:
    lines = [f"# {plan.title}", "",
             f"{req.level} | {req.days} days | {req.hours_per_day:g} hours per day", ""]
    if not approved:
        lines += ["**Draft - the two review passes finished, but issues remain:**"]
        lines += [f"- {item}" for item in feedback]
        lines.append("")
    for day in plan.days:
        total = sum(block.minutes for block in day.blocks)
        lines += [f"## Day {day.day} ({total} minutes)", ""]
        for block in day.blocks:
            count = f"; {block.problems} problems" if block.problems else ""
            lines.append(f"- **{block.minutes} min - {block.kind.title()}**: "
                         f"{block.activity}{count}")
        lines.append("")
    if plan.notes:
        lines += ["Notes:", ""] + [f"- {note}" for note in plan.notes] + [""]
    status = "passed" if approved else "needs changes"
    lines.append(f"Review: {status} after {passes} pass(es).")
    return "\n".join(lines)
