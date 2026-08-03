from datetime import date, time

from pawpal_system import Task, Owner, Pet, PlanEntry, Priority, Scheduler

# Tasks must be defined before they're used in a Pet's task list.
rockyTask1 = Task(
    title="Walk",
    description="Take Rocky on a walk to the park",
    due_date=date(2026, 7, 2),
    duration=30,
    priority=Priority.HIGH,
)
rockyTask2 = Task(
    title="Feeding",
    description="Morning kibble and fresh water",
    due_date=date(2026, 7, 2),
    duration=10,
    priority=Priority.HIGH,
)
cookieTask1 = Task(
    title="Meds",
    description="Give Cookie her allergy medication",
    due_date=date(2026, 7, 2),
    duration=5,
    priority=Priority.MEDIUM,
)
cookieTask2 = Task(
    title="Grooming",
    description="Brush Cookie's coat",
    due_date=date(2026, 7, 3),
    duration=20,
    priority=Priority.LOW,
)

pet1 = Pet(name ="Rocky", 
           age = 2, 
           tasks = [rockyTask1, rockyTask2])
pet2 = Pet(
    name ="Cookie",
     age =  4, 
     tasks = [cookieTask1, cookieTask2])

owner1 = Owner(
    name = "Katie", 
    email = "katieemail@hotmail.com", 
    pets = [pet1, pet2])

scheduler = Scheduler(available_minutes= 60);

plan = scheduler.generate_plan(pet1.tasks)

print(scheduler.explain_plan(plan))


# ---------------------------------------------------------------------------
# Demo: exercise the sorting and filtering methods.
# Add a few tasks out of order (via add_task so pet_name gets set), mark one
# complete, then run each method and print the resulting order.
# ---------------------------------------------------------------------------

# Make sure the constructor-built tasks are tagged with their pet's name too,
# so sort_by_pet has something to group on.
for pet in owner1.pets:
    for task in pet.tasks:
        task.pet_name = pet.name

# Extra tasks added deliberately out of priority / duration / pet order.
pet2.add_task(Task(
    title="Play",
    description="Laser pointer session with Cookie",
    due_date=date(2026, 7, 1),
    duration=15,
    priority=Priority.HIGH,
))
pet1.add_task(Task(
    title="Nail trim",
    description="Clip Rocky's nails",
    due_date=date(2026, 7, 4),
    duration=25,
    priority=Priority.LOW,
))

pet1.add_task(Task(
    title="Bath",
    description="Give Rocky a bat",
    due_date=date(2026, 7, 4),
    duration=25,
    priority=Priority.MEDIUM,
))

# Mark one task complete so the completion filter has something to drop.
rockyTask2.mark_complete()  # "Feeding"


def show(label, tasks):
    """Print a task list compactly: title, pet, duration, priority, done?"""
    print(f"\n{label}")
    for t in tasks:
        done = "x" if t.completed else " "
        print(f"  [{done}] {t.title:<10} {t.pet_name:<7} "
              f"{t.duration:>3}m  {t.priority.name}")


all_tasks = owner1.all_tasks()

show("Original order (out of order):", all_tasks)
show("sort_by_priority (HIGH first):", scheduler.sort_by_priority(all_tasks))
show("sort_by_time (shortest first):", scheduler.sort_by_time(all_tasks))
show("sort_by_pet (grouped A-Z):", scheduler.sort_by_pet(all_tasks))
show("filter_by_completion() -> to-do:", scheduler.filter_by_completion(all_tasks))
show("filter_by_completion(True) -> done:",
     scheduler.filter_by_completion(all_tasks, completed=True))


# ---------------------------------------------------------------------------
# Demo: conflict detection. generate_plan packs tasks back-to-back, so it
# never self-conflicts. To test the warning we hand-build a plan that puts
# two of Rocky's tasks at the SAME start time, then explain it.
# ---------------------------------------------------------------------------

print("\nBuilding a plan with two of Rocky's tasks at 08:00 (a conflict):")
conflicting_plan = [
    PlanEntry(task=rockyTask1, start_time=time(8, 0)),  # Walk, 30m
    PlanEntry(task=cookieTask1, start_time=time(8, 0)),  # different pet: no conflict
    PlanEntry(task=rockyTask2, start_time=time(8, 0)),  # Feeding, same pet + time
]

# explain_plan emits a warnings.warn(...) AND appends the conflict lines,
# without stopping the program.
print(scheduler.explain_plan(conflicting_plan))
print("\n=== program finished normally despite the conflict ===")


# ---------------------------------------------------------------------------
# Demo: risk scoring and risk explanations.
# A few more pets, each with tasks crafted to land on a different risk level,
# so we can eyeball how assess_risk() turns signals (lateness, deadlines,
# duration, priority, recurrence) into a LOW / MEDIUM / HIGH label plus a
# plain-English explanation and a confidence.
#
# "today" is pinned so the deadline-pressure signal (overdue / due-today) is
# reproducible regardless of when this file is actually run.
# ---------------------------------------------------------------------------

TODAY = date(2026, 8, 3)

# Luna: one clearly-HIGH task (a repeat offender that's now overdue) and one
# clearly-LOW task (short, high priority, with days of runway left).
lunaVet = Task(
    title="Vet visit",
    description="Overdue annual checkup Luna keeps missing",
    due_date=date(2026, 7, 30),          # overdue relative to TODAY  (+3)
    duration=45,                          # moderately long (>30 min)  (+1)
    priority=Priority.MEDIUM,             # medium priority            (+1)
    times_late=2,                         # slipped twice before       (+4)
)
lunaWater = Task(
    title="Water",
    description="Top up Luna's water bowl",
    due_date=date(2026, 8, 12),          # days of runway left        (+0)
    duration=5,                           # quick                      (+0)
    priority=Priority.HIGH,               # high priority              (+0)
)
pet3 = Pet(name="Luna", age=6, tasks=[lunaVet, lunaWater])

# Milo: two MEDIUM tasks that get there different ways — one via a
# due-today recurring chore, one via a low-priority recurring chore.
miloLitter = Task(
    title="Litter box",
    description="Scoop Milo's litter box",
    due_date=TODAY,                       # due today                  (+1)
    duration=15,
    priority=Priority.MEDIUM,             # medium priority            (+1)
    recurrence_days=1,                    # daily routine              (+1)
)
miloTeeth = Task(
    title="Dental treat",
    description="Weekly dental chew for Milo",
    due_date=TODAY,                       # due today                  (+1)
    duration=10,
    priority=Priority.LOW,                # low priority               (+2)
    recurrence_days=7,                    # weekly routine             (+1)
)
pet4 = Pet(name="Milo", age=3, tasks=[miloLitter, miloTeeth])

# Bella: a single very-HIGH task — long, low priority, and already overdue.
bellaClean = Task(
    title="Cage clean",
    description="Deep-clean Bella's hutch",
    due_date=date(2026, 8, 1),           # overdue                    (+3)
    duration=90,                          # long task (>60 min)        (+2)
    priority=Priority.LOW,                # low priority               (+2)
)
pet5 = Pet(name="Bella", age=1, tasks=[bellaClean])

owner2 = Owner(
    name="Sam",
    email="sam@example.com",
    pets=[pet3, pet4, pet5],
)

# Tag every task with its pet's name so the display lines read nicely.
for pet in owner2.pets:
    for task in pet.tasks:
        task.pet_name = pet.name


def show_risk(label, tasks):
    """Assess each task's risk against TODAY and print the explanation."""
    print(f"\n{label}")
    for t in tasks:
        t.assess_risk(today=TODAY)
        print(f"  {t.pet_name:<6} {t.title:<12} -> {t.risk_level.name:<6}")
        print(f"         {t.risk_explanation}")


print("\n=== Risk scoring demo (today = 2026-08-03) ===")

show_risk("Milo (expect MEDIUM, MEDIUM):", pet4.tasks)
show_risk("Bella (expect HIGH):", pet5.tasks)

# Schedule Sam's whole day, then list each planned task with its risk so the
# owner can see which slots are the shaky ones.
print("\n=== Sam's plan, annotated with risk ===")
sam_scheduler = Scheduler(available_minutes=120)
sam_plan = sam_scheduler.generate_plan(owner2.all_tasks())
for entry in sam_plan:
    entry.task.assess_risk(today=TODAY)
    print(f"  {entry.start_time.strftime('%H:%M')}  "
          f"{entry.task.pet_name:<6} {entry.task.title:<12} "
          f"[{entry.task.risk_level.name}]")
