"""PawPal+ domain model.

Implements the classes from diagrams/uml.mmd: Owner, Pet, Task, and Scheduler.
The Scheduler turns a set of tasks into a time-ordered daily plan under a
time budget, and can explain the plan it produced.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from uuid import uuid4


class Priority(Enum):
    """Task importance, used by the Scheduler to order tasks."""

    HIGH = 3
    MEDIUM = 2
    LOW = 1


class RiskLevel(Enum):
    """How likely a task is to be missed or finished late."""

    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class Task:
    """A single pet care task (walk, feeding, meds, etc.)."""

    title: str
    description: str = ""
    due_date: date | None = None
    start_time: time | None = None  # when the owner plans to start this task
    duration: int = 0  # minutes
    priority: Priority = Priority.MEDIUM
    pet_name: str = ""  # which pet this task belongs to (for display)
    recurrence_days: int | None = None  # repeat every N days; None = one-off
    times_late: int = 0  # how many past occurrences were missed or done late
    id: str = field(default_factory=lambda: uuid4().hex)
    completed: bool = False
    # Filled in by assess_risk(); None until a prediction has been made.
    risk_level: RiskLevel | None = None
    risk_explanation: str = ""
    # How much to trust the risk_level, in [0.0, 1.0]. None until assessed.
    risk_confidence: float | None = None

    @property
    def is_recurring(self) -> bool:
        """True if this task repeats on a schedule (has a recurrence interval)."""
        return self.recurrence_days is not None

    def mark_complete(self) -> None:
        """Mark this task as done."""
        self.completed = True

    def mark_late(self) -> int:
        """Record that this occurrence was missed or finished late.

        Bumps the lateness counter and returns the new total. A history of
        lateness is the strongest signal assess_risk() has, so each call here
        makes future predictions lean riskier (and more confident).
        """
        self.times_late += 1
        return self.times_late

    def assess_risk(self, today: date | None = None) -> RiskLevel:
        """Predict how likely this task is to be missed or finished late.

        Combines a few simple signals into a risk score, then buckets that
        score into LOW / MEDIUM / HIGH. The result is stored on the task
        (risk_level and a human-readable risk_explanation) and also returned.

        Signals used:
          * times_late   — a history of lateness is the strongest predictor.
          * due_date      — overdue or due-today tasks are riskier than ones
                            with runway left.
          * duration      — long tasks are easier to put off.
          * priority      — low-priority tasks tend to get bumped.
          * is_recurring  — routine tasks are easy to forget on any given day.
        """
        if today is None:
            today = date.today()

        score = 0
        reasons: list[str] = []

        # History of lateness: each past slip adds weight (capped so one very
        # unreliable task doesn't drown out every other signal).
        if self.times_late > 0:
            score += min(self.times_late, 3) * 2
            times = "time" if self.times_late == 1 else "times"
            reasons.append(f"late {self.times_late} {times} before")

        # Deadline pressure.
        if self.due_date is not None:
            if self.due_date < today:
                score += 3
                reasons.append("already overdue")
            elif self.due_date == today:
                score += 1
                reasons.append("due today")

        # Longer tasks are easier to procrastinate on.
        if self.duration > 60:
            score += 2
            reasons.append("long task (over 60 min)")
        elif self.duration > 30:
            score += 1
            reasons.append("moderately long task (over 30 min)")

        # Low-priority work is the first to get dropped when time is tight.
        if self.priority is Priority.LOW:
            score += 2
            reasons.append("low priority, easy to deprioritize")
        elif self.priority is Priority.MEDIUM:
            score += 1

        # Recurring chores are easy to forget on any given day.
        if self.is_recurring:
            score += 1
            reasons.append("recurring routine, easy to forget")

        if score >= 5:
            self.risk_level = RiskLevel.HIGH
        elif score >= 2:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW

        # --- How confident are we in that label? ---------------------------
        # Confidence answers "how much should you trust this prediction?" and
        # is driven by two things:
        #   1. Evidence — real signals (a track record, a concrete deadline)
        #      beat guessing from defaults. History is the strongest evidence,
        #      so more past-lateness observations raise confidence.
        #   2. Margin — a score sitting right on a bucket edge (2 or 5) is a
        #      near coin-flip; one deep inside a bucket is a safe call.
        confidence = 0.35  # floor: priority, duration and recurrence are known
        if self.times_late > 0:
            confidence += min(self.times_late, 3) * 0.15  # +0.15 .. +0.45
        if self.due_date is not None:
            confidence += 0.20  # a real deadline anchors the pressure signal
        margin = min(abs(score - 2), abs(score - 5))
        confidence += min(margin, 2) * 0.05  # +0.00 .. +0.10 for a clear-cut score
        self.risk_confidence = round(max(0.0, min(1.0, confidence)), 2)

        if reasons:
            self.risk_explanation = (
                f"{self.risk_level.name} risk — " + "; ".join(reasons) + "."
            )
        else:
            self.risk_explanation = (
                f"{self.risk_level.name} risk — no warning signs; "
                "on track to finish on time."
            )
        self.risk_explanation += (
            f" (confidence: {self.confidence_label()}, "
            f"{self.risk_confidence:.0%})"
        )
        return self.risk_level

    def confidence_label(self) -> str:
        """Bucket risk_confidence into a plain-English word for display.

        Returns "unknown" if assess_risk() hasn't run yet, otherwise
        "high" (>= 0.75), "moderate" (>= 0.5), or "low".
        """
        if self.risk_confidence is None:
            return "unknown"
        if self.risk_confidence >= 0.75:
            return "high"
        if self.risk_confidence >= 0.5:
            return "moderate"
        return "low"

    def next_occurrence(self) -> Task | None:
        """Build the next instance of a recurring task, or None if one-off.

        Returns a fresh, not-completed copy with a new id and the due_date
        advanced by recurrence_days. If there's no due_date, the copy keeps
        due_date=None. Does not touch this task or any task list.
        """
        if self.recurrence_days is None:
            return None
        next_due = (
            self.due_date + timedelta(days=self.recurrence_days)
            if self.due_date is not None
            else None
        )
        return replace(
            self,
            due_date=next_due,
            completed=False,
            id=uuid4().hex,
        )


@dataclass
class PlanEntry:
    """A task placed at a specific start time in the daily plan."""

    task: Task
    start_time: time


@dataclass
class Pet:
    """A pet and its list of care tasks."""

    name: str
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's list, tagging it with the pet's name."""
        task.pet_name = self.name
        self.tasks.append(task)

    def complete_task(self, task: Task) -> Task | None:
        """Mark a task complete and, if it recurs, queue its next occurrence.

        Appends the new instance to this pet's list (tagged with the pet's
        name) and returns it, or None for a one-off task.
        """
        task.mark_complete()
        upcoming = task.next_occurrence()
        if upcoming is not None:
            self.add_task(upcoming)
        return upcoming

    def edit_task(self, task: Task) -> None:
        """Replace an existing task (matched by id) with an updated version.

        Raises ValueError if no task with that id belongs to this pet.
        """
        for index, existing in enumerate(self.tasks):
            if existing.id == task.id:
                task.pet_name = self.name
                self.tasks[index] = task
                return
        raise ValueError(f"No task with id {task.id!r} on pet {self.name!r}")


@dataclass
class Owner:
    """A pet owner who manages one or more pets."""

    name: str
    email: str = ""
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def all_tasks(self) -> list[Task]:
        """Return every task across all of this owner's pets, as a flat list."""
        return [task for pet in self.pets for task in pet.tasks]

    def edit_task(self, pet: Pet, task: Task) -> None:
        """Edit a task on one of this owner's pets. Delegates to Pet.edit_task."""
        pet.edit_task(task)


@dataclass
class Scheduler:
    """Builds a daily plan from a set of tasks under a time budget."""

    available_minutes: int = 240  # total time the owner has today
    day_start: time = time(8, 0)  # when the plan begins

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return a new list sorted highest-priority first.

        Ties break by earlier due_date, then shorter duration, so the order
        is deterministic (important for stable tests).
        """
        return sorted(
            tasks,
            key=lambda t: (
                -t.priority.value,        # HIGH(3) first
                t.due_date or date.max,   # earlier deadlines first; None sinks to the end
                t.duration,               # shorter tasks first
            ),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return a new list sorted shortest-duration first.

        Ties break by earlier due_date, then higher priority, so the order
        is deterministic (important for stable tests).
        """
        return sorted(
            tasks,
            key=lambda t: (
                t.duration,               # shorter tasks first
                t.due_date or date.max,   # earlier deadlines first; None sinks to the end
                -t.priority.value,        # HIGH(3) first
            ),
        )

    def sort_by_pet(self, tasks: list[Task]) -> list[Task]:
        """Return a new list grouped alphabetically by pet name.

        Ties (same pet) break by higher priority, then earlier due_date, so
        the order is deterministic (important for stable tests).
        """
        return sorted(
            tasks,
            key=lambda t: (
                t.pet_name,               # group by pet, A-Z
                -t.priority.value,        # HIGH(3) first within a pet
                t.due_date or date.max,   # earlier deadlines first; None sinks to the end
            ),
        )

    def filter_by_completion(
        self, tasks: list[Task], completed: bool = False
    ) -> list[Task]:
        """Return tasks matching the given completion status, preserving order.

        Defaults to completed=False so callers get the still-to-do tasks, which
        is what the planner wants.
        """
        return [t for t in tasks if t.completed == completed]

    def filter_by_time(self, tasks: list[Task]) -> list[Task]:
        """Keep tasks (in the given order) that fit the time budget.

        Greedy: walk the list and include each task whose duration fits in the
        remaining minutes; skip the ones that don't. A later, shorter task can
        still fit after an earlier, longer one was skipped.
        """
        remaining = self.available_minutes
        kept: list[Task] = []
        for task in tasks:
            if task.duration <= remaining:
                kept.append(task)
                remaining -= task.duration
        return kept

    def generate_plan(self, tasks: list[Task]) -> list[PlanEntry]:
        """Return a time-ordered daily plan.

        Completed tasks are dropped, then the rest are prioritized, trimmed to
        the time budget, and assigned back-to-back start times from day_start.
        """
        todo = self.filter_by_completion(tasks)  # skip already-done tasks
        prioritized = self.sort_by_priority(todo)
        packed = self.filter_by_time(prioritized)

        plan: list[PlanEntry] = []
        clock = datetime.combine(date.min, self.day_start)
        for task in packed:
            plan.append(PlanEntry(task=task, start_time=clock.time()))
            clock += timedelta(minutes=task.duration)
        return plan

    def find_conflicts(
        self, plan: list[PlanEntry]
    ) -> list[tuple[PlanEntry, PlanEntry]]:
        """Return pairs of entries for the same pet whose times overlap.

        Two entries conflict when they share a pet_name and their
        [start, start + duration) intervals overlap — so a pet can't be in
        two places at once. Back-to-back tasks (one ends exactly when the
        next starts) do NOT count as a conflict. Order within each returned
        pair follows the plan's order.
        """
        def bounds(entry: PlanEntry) -> tuple[datetime, datetime]:
            start = datetime.combine(date.min, entry.start_time)
            return start, start + timedelta(minutes=entry.task.duration)

        conflicts: list[tuple[PlanEntry, PlanEntry]] = []
        for i, a in enumerate(plan):
            a_start, a_end = bounds(a)
            for b in plan[i + 1:]:
                if a.task.pet_name != b.task.pet_name:
                    continue
                b_start, b_end = bounds(b)
                if a_start < b_end and b_start < a_end:  # strict: touching is OK
                    conflicts.append((a, b))
        return conflicts

    def has_conflicts(self, plan: list[PlanEntry]) -> bool:
        """True if any two same-pet entries in the plan overlap in time."""
        return bool(self.find_conflicts(plan))

    def conflict_warnings(self, plan: list[PlanEntry]) -> list[str]:
        """Return one human-readable warning line per detected conflict.

        Empty list if the plan is clean. This never raises — it's meant to
        report problems without stopping the program.
        """
        lines = []
        for a, b in self.find_conflicts(plan):
            lines.append(
                f"  [!] {a.task.pet_name} double-booked: "
                f"{a.task.title} ({a.start_time:%H:%M}) overlaps "
                f"{b.task.title} ({b.start_time:%H:%M})"
            )
        return lines

    def explain_plan(self, plan: list[PlanEntry]) -> str:
        """Render the plan as an aligned, terminal-friendly table."""
        if not plan:
            return "No tasks scheduled — nothing fit the available time."

        # Column widths sized to the longest value in each column.
        title_w = max(len(e.task.title) for e in plan)
        pet_w = max(len(e.task.pet_name) for e in plan)
        used = sum(e.task.duration for e in plan)
        free = self.available_minutes - used

        rows = []
        for entry in plan:
            task = entry.task
            end = (datetime.combine(date.min, entry.start_time)
                   + timedelta(minutes=task.duration)).time()
            rows.append(
                f"  {entry.start_time:%H:%M}-{end:%H:%M}   "
                f"{task.title:<{title_w}}   "
                f"{task.pet_name:<{pet_w}}   "
                f"{task.duration:>3}m  {task.priority.name}"
            )

        width = max(len(r) for r in rows)
        divider = "  " + "-" * (width - 2)
        footer = (
            f"  {len(plan)} task(s) · {used}/{self.available_minutes} min used "
            f"· {free} min free"
        )

        lines = ["  Daily Plan", divider, *rows, divider, footer]

        # Conflicts are reported, never fatal: emit a runtime warning and
        # append the details to the rendered plan so the program keeps going.
        warning_lines = self.conflict_warnings(plan)
        if warning_lines:
            warnings.warn(
                f"{len(warning_lines)} scheduling conflict(s) detected",
                stacklevel=2,
            )
            lines.extend([divider, *warning_lines])

        return "\n".join(lines)
