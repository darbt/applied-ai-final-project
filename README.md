Pawpal + 
- A scheduler to help pet owners organize tasks for their pets. The scheduler, can asssign pets, track tasks duration, generate a daily schedule, and other small features that assist in prioritizing to-dos. 

Pawapl 2.0 
- A smart pet care-planning program that pet owners can organize and manage daily responsibilites tied to their pets. Pawpal 2.0 has the same capabilities as its predecessor as well as an explainable risk-assesment system which evaluates each unfinished task and assigns a risk score of how likely a task would be missed or late. 
This program matters because it helps reduce the probklems for forgetting both important and minor task regarding the pet. It helps the user determine what tasks have the highest priority and helps the user avoid feeling overwhelmed with all the different tasks

System Design
Three Main components: 

1. Streamlit User Interface
The UI that allows the user to utilize the program's features and stores an active task list in the session state while the application is running
2. Domain and Risk Model
The risk model takes the classes of the pawpal_system class and examines several task signals like due date, task duration, priority, etc and combines them to determine a risk score. The risk scoere then assigns result of either low, medium, or high. 
3. Scheduling and Reliablity Checks
There is a conflict checker to make sure that there are no conflicts in scheduling with overlapping tasks. The diagram also includes automated tests to checkthat the program behaves consistently and efficently. 

Instructions

Before starting, make sure the following are installed:

Python 3.10 or newer
A code editor such as Visual Studio Code
A terminal, PowerShell, or Command Prompt

Run:

python -m streamlit run app.py

Streamlit should open PawPal+ in a web browser.

After the app opens:

1. Enter the owner’s name.
2. Enter one or more pet names separated by commas.
3. Add a task title.
4. Select the pet connected to the task.
5. Enter the task duration.
6. Choose its priority.
7. Select its due date and start time.
8. Enter how many times the task was previously late.
9. Select whether it is recurring.
10. Click Add task.

The task will appear in the current-task section with:

Priority
Completion status
Recurrence status
Previous late count
Predicted risk level
Explanation and confidence

Use the available controls to edit, delete, complete, sort, or filter tasks.

To build a schedule:

1. Enter the number of minutes available that day.
2. Click Generate schedule.
3. Review the scheduled tasks, used time, and remaining time.

To check for conflicts:

1. Give tasks their intended start times.
2. Click Check for conflicts.
3. Review any overlap warnings.

Sample Inputs and Outputs

INPUT: show_risk("Luna (expect HIGH, then LOW):", pet3.tasks)

OUTPUT:
=== Risk scoring demo (today = 2026-08-03) ===

Luna (expect HIGH, then LOW):
  Luna   Vet visit    -> HIGH  
         HIGH risk — late 2 times before; already overdue; moderately long task (over 30 min). (confidence: high, 95%)
  Luna   Water        -> LOW   
         LOW risk — no warning signs; on track to finish on time. (confidence: moderate, 65%)

=== Sam's plan, annotated with risk ===
  08:00  Luna   Water        [LOW]
  08:05  Luna   Vet visit    [HIGH]
  08:50  Milo   Litter box   [MEDIUM]
  09:05  Milo   Dental treat [MEDIUM]

INPUT: show_risk("Milo (expect MEDIUM, MEDIUM):", pet4.tasks)
show_risk("Bella (expect HIGH):", pet5.tasks)

OUTPUT:
=== Risk scoring demo (today = 2026-08-03) ===

Milo (expect MEDIUM, MEDIUM):
  Milo   Litter box   -> MEDIUM
         MEDIUM risk — due today; recurring routine, easy to forget. (confidence: moderate, 60%)
  Milo   Dental treat -> MEDIUM
         MEDIUM risk — due today; low priority, easy to deprioritize; recurring routine, easy to forget. (confidence: moderate, 60%)

Bella (expect HIGH):
  Bella  Cage clean   -> HIGH  
         HIGH risk — already overdue; long task (over 60 min); low priority, easy to deprioritize. (confidence: moderate, 65%)

=== Sam's plan, annotated with risk ===
  08:00  Luna   Water        [LOW]
  08:05  Luna   Vet visit    [HIGH]
  08:50  Milo   Litter box   [MEDIUM]
  09:05  Milo   Dental treat [MEDIUM]

Design Decisions

I built the program the way that I did because I wanted the predictions to be able to be explained clearly and easily. I also prioritized simplicity so that it is manageable and consistent. I also had to make sure that it was clear that results are a prediction and not certain. These design choices do come with trade offs. For example, as a result of the simplicty, the program is non-adaptive, it does not learn as it is transparent. So two users with different habits may recieve the same risk score for the same inputs which is not very accurate. 

Testing Summary

The risk explainations worked as well as calculating the risk score. What didn't work was automatically creating a risk "scale", that would change based on the user. Meaning that a missed task should receive a different score because the users are different and do things differently. This proved to be to complicated and the outputs would constantly change even with the same information. 