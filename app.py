from datetime import date, time

import streamlit as st

from pawpal_system import PlanEntry, Priority, RiskLevel, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
**PawPal+** is a pet care planning assistant. Add care tasks for your pets, then let
the scheduler sort, filter, and pack them into a time-ordered daily plan under your
available time budget — and flag any scheduling conflicts along the way.
"""
)

st.divider()

# --- Owner / pet setup -------------------------------------------------------
st.subheader("Who are we planning for?")
col_owner, col_pet = st.columns(2)
with col_owner:
    owner_name = st.text_input("Owner name", value="Jordan")
with col_pet:
    pet_names_raw = st.text_input("Pet name(s), comma-separated", value="Mochi, Kiwi")
pet_names = [p.strip() for p in pet_names_raw.split(",") if p.strip()] or ["Pet"]

st.divider()

# --- Task entry --------------------------------------------------------------
st.subheader("Tasks")
st.caption("Add a few care tasks. These feed directly into the scheduler below.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
    task_pet = st.selectbox("Pet", pet_names)
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col3:
    due = st.date_input("Due date", value=date.today())
    start = st.time_input("Start time", value=time(8, 0))

# --- Risk-prediction inputs: history + recurrence feed the risk estimate. ----
col4, col5 = st.columns(2)
with col4:
    times_late = st.number_input(
        "Times late previously",
        min_value=0,
        max_value=99,
        value=0,
        help="How many past occurrences of this task were missed or done late.",
    )
with col5:
    is_recurring = st.checkbox(
        "Recurring task",
        value=False,
        help="Repeats on a schedule — routine chores are easy to forget.",
    )
    recurrence_days = None
    if is_recurring:
        recurrence_days = st.number_input(
            "Repeats every N days", min_value=1, max_value=365, value=1
        )

if st.button("Add task"):
    new_task = Task(
        title=task_title,
        duration=int(duration),
        priority=PRIORITY_MAP[priority],
        pet_name=task_pet,
        due_date=due,
        start_time=start,
        times_late=int(times_late),
        recurrence_days=int(recurrence_days) if recurrence_days else None,
    )
    # Predict up front so the task carries its risk level and explanation.
    new_task.assess_risk()
    st.session_state.tasks.append(new_task)

st.divider()

# --- Current tasks -----------------------------------------------------------
st.subheader("Current tasks")

PRIORITY_BADGE = {"HIGH": "🔴 High", "MEDIUM": "🟡 Medium", "LOW": "🟢 Low"}
RISK_BADGE = {"HIGH": "🔴 High", "MEDIUM": "🟠 Medium", "LOW": "🟢 Low"}

if not st.session_state.tasks:
    st.info("No tasks yet. Add one above.")
else:
    scheduler_view = Scheduler()

    # Re-run the prediction so risk reflects today's date (a task can slip to
    # "overdue" just by time passing since it was added).
    for t in st.session_state.tasks:
        t.assess_risk()

    # At-a-glance summary of the whole task set.
    all_tasks = st.session_state.tasks
    done_tasks = scheduler_view.filter_by_completion(all_tasks, completed=True)
    todo_tasks = scheduler_view.filter_by_completion(all_tasks, completed=False)
    at_risk = [
        t for t in todo_tasks if t.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)
    ]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total tasks", len(all_tasks))
    m2.metric("To-do", len(todo_tasks))
    m3.metric("Completed", len(done_tasks))
    m4.metric("At risk", len(at_risk), help="To-do tasks with medium or high risk.")

    # Scheduler.sort_* methods let the owner reorder the same task set by
    # different criteria without mutating the underlying list.
    SORTERS = {
        "Priority (highest first)": scheduler_view.sort_by_priority,
        "Time (shortest first)": scheduler_view.sort_by_time,
        "Pet (grouped A–Z)": scheduler_view.sort_by_pet,
    }
    sort_choice = st.radio("Sort by", list(SORTERS.keys()), horizontal=True)

    show_completed = st.checkbox("Show completed tasks", value=False)
    tasks_to_show = SORTERS[sort_choice](st.session_state.tasks)
    if not show_completed:
        # filter_by_completion(completed=False) → still-to-do tasks only.
        tasks_to_show = scheduler_view.filter_by_completion(tasks_to_show, completed=False)

    # Describe the active view so the sort/filter state is obvious.
    scope = "all tasks" if show_completed else "to-do tasks only"
    st.success(f"Showing **{len(tasks_to_show)}** {scope}, sorted by **{sort_choice}**.")

    st.dataframe(
        [
            {
                "Task": t.title,
                "Pet": t.pet_name,
                "Start": t.start_time.strftime("%H:%M") if t.start_time else "—",
                "Due": t.due_date.isoformat() if t.due_date else "—",
                "Duration": t.duration,
                "Priority": PRIORITY_BADGE.get(t.priority.name, t.priority.name),
                "Recurring": "🔁 Yes" if t.is_recurring else "—",
                "Late before": t.times_late,
                "Risk": RISK_BADGE.get(
                    t.risk_level.name if t.risk_level else "", "—"
                ),
                "Why": t.risk_explanation,
                "Status": "✅ Done" if t.completed else "⏳ To-do",
            }
            for t in tasks_to_show
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Duration": st.column_config.NumberColumn("Duration", format="%d min"),
            "Late before": st.column_config.NumberColumn("Late before", format="%d×"),
            "Why": st.column_config.TextColumn("Why", width="large"),
        },
    )

    # Spotlight the tasks the risk model thinks are most likely to slip.
    high_risk = [t for t in todo_tasks if t.risk_level is RiskLevel.HIGH]
    if high_risk:
        st.error(
            "⚠️ **Likely to be missed or late:** "
            + ", ".join(f"{t.title} ({t.pet_name})" for t in high_risk)
        )
        for t in high_risk:
            st.caption(f"• **{t.title}** — {t.risk_explanation}")

    # Let the owner mark tasks complete so filter_by_completion is visible.
    open_tasks = todo_tasks
    if open_tasks:
        done_title = st.selectbox(
            "Mark a task complete",
            [t.title for t in open_tasks],
            key="complete_select",
        )
        if st.button("Mark complete"):
            for t in open_tasks:
                if t.title == done_title:
                    t.mark_complete()
                    break
            st.rerun()

st.divider()

# --- Build schedule ----------------------------------------------------------
st.subheader("Build schedule")
st.caption("The scheduler prioritizes, trims to your time budget, and lays out start times.")

available_minutes = st.number_input(
    "Available time today (minutes)", min_value=1, max_value=1440, value=240
)

if st.button("Generate schedule"):
    if not st.session_state.tasks:
        st.info("Add some tasks first, then generate a schedule.")
    else:
        scheduler = Scheduler(available_minutes=int(available_minutes))
        plan = scheduler.generate_plan(st.session_state.tasks)

        if not plan:
            st.warning("Nothing fit the available time. Try adding more minutes.")
        else:
            used = sum(e.task.duration for e in plan)
            free = int(available_minutes) - used
            s1, s2, s3 = st.columns(3)
            s1.metric("Tasks scheduled", len(plan))
            s2.metric("Minutes used", used)
            s3.metric("Minutes free", free)

            st.code(scheduler.explain_plan(plan))
            st.caption(
                "This auto-plan packs tasks back-to-back, so it never overlaps. "
                "Use the conflict check below to test your own start times."
            )

st.divider()

# --- Conflict check (owner's own start times) --------------------------------
st.subheader("Conflict check")
st.caption(
    "Builds a timeline from the start times you entered and flags any point where "
    "the same pet is booked in two overlapping slots."
)

if st.button("Check for conflicts"):
    scheduler = Scheduler()
    todo = scheduler.filter_by_completion(st.session_state.tasks, completed=False)
    timed = [t for t in todo if t.start_time is not None]

    if not timed:
        st.info("Add some to-do tasks with start times first.")
    else:
        # Build a plan from the owner's chosen times, ordered by start time.
        timeline = [
            PlanEntry(task=t, start_time=t.start_time)
            for t in sorted(timed, key=lambda t: t.start_time)
        ]

        st.dataframe(
            [
                {
                    "Start": e.start_time.strftime("%H:%M"),
                    "Task": e.task.title,
                    "Pet": e.task.pet_name,
                    "Duration": e.task.duration,
                }
                for e in timeline
            ],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Duration": st.column_config.NumberColumn("Duration", format="%d min"),
            },
        )

        # find_conflicts / conflict_warnings surface same-pet overlaps.
        if scheduler.has_conflicts(timeline):
            conflicts = scheduler.conflict_warnings(timeline)
            st.warning(f"⚠️ Found {len(conflicts)} scheduling conflict(s):")
            for line in conflicts:
                st.warning(line.strip())
        else:
            st.success("No time conflicts — every pet's slots are clear. ✅")
