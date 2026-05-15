# Advanced Degree Planner: Implementation Roadmap

This document outlines the advanced features required to transform the current UniNavigator into a fully interactive, multi-option, "smart" advisory system.

## 1. Interactive UI: The "Degree Planner" Tab
*   **Objective:** Move away from purely text-based extraction and provide a dedicated interface for complex inputs.
*   **Implementation:** 
    *   Activate the "Courses" or add a new "Degree Planner" tab on the left sidebar (`index.html`).
    *   Create an interactive dashboard with form controls:
        *   **Current Semester Dropdown** (e.g., "2nd Semester")
        *   **Current CGPA Input** (e.g., "1.8")
        *   **Failed Courses Selector** (Multi-select dropdown with all available courses)
        *   **Preferences Toggle** ("Willing to take Summer classes?")
    *   **Frontend-Backend Link:** These inputs will be sent directly to the LangGraph backend as structured JSON rather than a raw chat string.

## 2. Conversational Memory & Clarification Node
*   **Objective:** Prevent the agent from making assumptions if the user asks for help via the chat interface without providing all details.
*   **Implementation:**
    *   Update `AgentState` in `graph.py` to include `missing_information` flags.
    *   Create a `clarification_node`: If a user types *"Fix my plan"* but doesn't mention *which* course they failed, the agent will pause the calculation and ask: *"I can help with that. Which exact courses did you fail, and are you open to taking summer classes to catch up?"*
    *   The graph will loop back to the user until all necessary state variables are collected.

## 3. Multi-Option Generation (Plan A vs. Plan B)
*   **Objective:** Give the student choices based on their personal preferences and financial/time constraints.
*   **Implementation:**
    *   Upgrade the Python Constraint Solver (`planner_logic.py`) to run multiple parallel simulations.
    *   It will output 2 to 3 distinct options:
        *   **Option 1 (The Catch-up Plan):** Uses summer semesters heavily to ensure the student graduates exactly on time.
        *   **Option 2 (The Relaxed Plan):** Excludes summer semesters entirely, pushing graduation back by one semester but keeping the workload standard.
        *   **Option 3 (The Workload-Reduced Plan):** If GPA is low, intentionally drops non-prerequisite electives to later semesters to lighten the immediate load.

## 4. The "Why" Engine (Prerequisite Reasoning)
*   **Objective:** The system must explain its mathematical decisions so the student understands the impact of their failed courses.
*   **Implementation:**
    *   Add a new step where the LLM analyzes the output of `planner_logic.py`.
    *   It will generate a summary paragraph explaining the topological sort decisions.
    *   *Example Output:* "I placed CS112 in Summer Year 1 because it is a strict prerequisite for CS221 (Data Structures). If you delay it to Fall, it will cascade and delay your graduation. However, HM102 has no future dependencies, so I pushed it to your final year."

## 5. Strict University Rules Integration
*   **Objective:** Integrate real-world academic probation constraints.
*   **Implementation:**
    *   Consult the university rulebook (via RAG or hardcoding core logic).
    *   If the student inputs a CGPA < 2.0 (Academic Probation), the Planner Algorithm will strictly cap the max credit hours to 12 per semester.
    *   The planner will prioritize retaking failed courses over enrolling in new ones until the GPA constraint is lifted.

---
*Feel free to edit this file, add your comments, or rearrange priorities! Let me know which phase we should tackle first.*
