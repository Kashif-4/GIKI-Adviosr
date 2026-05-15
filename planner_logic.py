import json
import os

class DegreePlanner:
    """
    Constraint-based Degree Planner.

    Core rules:
    - Courses stay in their ORIGINALLY PLANNED semester or LATER (never earlier).
    - A course is only deferred if:
        a) Its prerequisite has not been completed yet (e.g. because the prereq was failed), OR
        b) The semester is over the credit-hour cap.
    - Summer slots only contain RETAKE courses (failed courses being repeated).
    - CGPA < 2.0 triggers Academic Probation: max 12 CH per regular semester.

    Academic Calendar:
        Sem 1  = Fall  Year 1  (odd sems  = Fall)
        Sem 2  = Spring Year 1 (even sems = Spring)
        Sem 3  = Fall  Year 2
        ...
        Summer comes AFTER each Spring, BEFORE the next Fall.
    """

    MAX_CREDITS_NORMAL    = 18
    MAX_CREDITS_PROBATION = 12
    MAX_CREDITS_SUMMER    =  6

    def __init__(self, data_path="data/prerequisites.json", degree="BSCS"):
        self.data_path = data_path
        self.degree    = degree
        self.graph     = self._load_data()

    def _load_data(self):
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Could not find {self.data_path}")
        with open(self.data_path, "r") as f:
            data = json.load(f)
        if self.degree not in data:
            raise ValueError(f"Degree '{self.degree}' not found in {self.data_path}")
        return data[self.degree]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def prereqs_met(self, course: str, taken: set) -> bool:
        return all(p in taken for p in self.graph.get(course, {}).get("prereqs", []))

    def original_semester(self, course: str) -> int:
        return self.graph.get(course, {}).get("semester", 99)

    def get_credits(self, course: str) -> int:
        return self.graph.get(course, {}).get("credits", 3)

    @staticmethod
    def sem_to_label(sem: int) -> str:
        """Return a human-readable label given the 1-based semester number."""
        year      = ((sem - 1) // 2) + 1
        season    = "Fall" if sem % 2 == 1 else "Spring"
        return f"Semester {sem} ({season} Year {year})"

    @staticmethod
    def summer_label(after_sem: int) -> str:
        """Label for the summer that comes after the given semester number."""
        year = ((after_sem - 1) // 2) + 1
        return f"Summer Year {year}"

    # ------------------------------------------------------------------
    # Core planning engine
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        passed_courses:        list,
        failed_courses:        list,
        current_completed_sem: int,
        use_summer:            bool  = True,
        cgpa:                  float = 3.0
    ) -> list:
        """
        Generate a semester-by-semester plan from (current_completed_sem + 1) onwards.

        Rules:
        1. Courses appear in their originally planned semester or later — NEVER earlier.
        2. If a course's prereq was failed and has not been retaken yet, the course is
           deferred to the next semester automatically.
        3. Summer slots only contain RETAKE courses.
        4. The plan continues until every remaining course is scheduled.
        """
        max_regular = self.MAX_CREDITS_PROBATION if cgpa < 2.0 else self.MAX_CREDITS_NORMAL

        taken      = set(passed_courses)
        failed_set = set(failed_courses)
        start_sem  = current_completed_sem + 1

        # Courses that still need to be retaken
        pending_retakes = set(failed_courses) - taken  # Should be all of failed_courses

        # Courses deferred because their prereqs weren't met this semester
        deferred: set = set()

        # Find the last planned semester in the degree
        max_sem = max((d.get("semester", 0) for d in self.graph.values()), default=8)

        plan: list = []

        sem = start_sem
        while sem <= max_sem + 4:  # +4 safety for deferred/retake overflow
            # ── 1. Regular Semester ──────────────────────────────────────────
            # Candidates = courses originally planned for THIS semester + any deferred
            originally_this_sem = {
                c for c, d in self.graph.items()
                if d.get("semester") == sem
            }
            candidates = (originally_this_sem | deferred) - taken

            selected       = []
            used_credits   = 0
            still_deferred = set()

            # Sort: failed courses first, then by original sem, then by code
            for c in sorted(
                candidates,
                key=lambda c: (
                    0 if c in failed_set else 1,
                    self.original_semester(c),
                    c
                )
            ):
                if not self.prereqs_met(c, taken):
                    still_deferred.add(c)   # Prereq still not done — defer
                    continue
                ch = self.get_credits(c)
                if used_credits + ch <= max_regular:
                    selected.append(c)
                    used_credits += ch
                else:
                    still_deferred.add(c)   # Credit cap hit — defer

            taken.update(selected)
            deferred = still_deferred
            pending_retakes -= set(selected)

            if selected:
                warning = (
                    f"⚠️ Academic Probation: max {self.MAX_CREDITS_PROBATION} CH per semester (CGPA < 2.0)."
                    if cgpa < 2.0 else ""
                )
                plan.append(self._make_term(self.sem_to_label(sem), selected, used_credits, failed_set, warning))

            # ── 2. Summer (after every Spring, i.e. after even-numbered sems) ──
            if sem % 2 == 0 and use_summer:
                summer_retakes = [
                    c for c in pending_retakes
                    if c not in taken and self.prereqs_met(c, taken)
                ]
                if summer_retakes:
                    summer_selected = []
                    summer_credits  = 0
                    for c in sorted(summer_retakes, key=lambda c: self.original_semester(c)):
                        ch = self.get_credits(c)
                        if summer_credits + ch <= self.MAX_CREDITS_SUMMER:
                            summer_selected.append(c)
                            summer_credits += ch

                    if summer_selected:
                        taken.update(summer_selected)
                        pending_retakes -= set(summer_selected)
                        plan.append(self._make_term(
                            self.summer_label(sem),
                            summer_selected, summer_credits, failed_set,
                            "☀️ Summer — retake slot only."
                        ))

            # ── 3. Stop when everything is done ─────────────────────────────
            all_remaining = set(self.graph.keys()) - taken
            if not all_remaining and not deferred and not pending_retakes:
                break

            sem += 1

        return plan

    # ------------------------------------------------------------------
    # Internal HTML builder
    # ------------------------------------------------------------------

    def _make_term(self, term_name, courses, total_credits, failed_set, warning=""):
        rows = []
        for c in courses:
            prereqs     = self.graph.get(c, {}).get("prereqs", [])
            prereqs_str = ", ".join(prereqs) if prereqs else "None"
            is_retake   = c in failed_set
            rows.append({
                "code":      c,
                "name":      self.graph[c].get("name", c),
                "credits":   self.graph[c].get("credits", 3),
                "prereqs":   prereqs_str,
                "is_retake": is_retake
            })
        return {
            "term_name":     term_name,
            "courses":       rows,
            "total_credits": total_credits,
            "warning":       warning
        }
