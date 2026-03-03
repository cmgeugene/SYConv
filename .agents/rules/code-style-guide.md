---
trigger: always_on
---

# code-style-guide

This rule enforces synchronization between source code and documentation to ensure clarity of intent and progress. The agent must strictly follow these instructions for all code modification tasks.

## 1. File Management Principles
- **Naming Consistency:** Every source file (e.g., `PlayerController.cpp`) must have a corresponding Markdown file with the exact same name (e.g., `PlayerController.md`).
- **Timing of Updates:** 1. **Pre-modification:** Update the `.md` file first to reflect the current structure and planned changes.
    2. **Post-modification:** Immediately update the `.md` file after code changes to record the final state.

## 2. Mandatory Markdown Structure (`[filename].md`)
Every `.md` file must include the following two sections:

### 1) Code Overview
- **Method Roles:** Describe the individual responsibilities of key methods/functions within the file.
- **Relationships & Flow:** Describe the logical structure, such as call sequences between methods or how data flows through the logic.

### 2) TODOs in this Code
- **Pending Tasks:** List features not yet implemented or areas requiring improvement.
- **Status Tracking:** Mark completed tasks as `[x]` or remove them, and add new challenges discovered during coding.

## 3. Agent Workflow (Internal Instructions)
1. Upon receiving a code modification request, the agent must check for the existence of the corresponding `.md` file.
2. If it doesn't exist, create it. If it does, read it and update the 'Overview' and 'TODO' sections to match the current context before touching the code.
3. Proceed with the source code modification (C++, Headers, etc.) only after the documentation is updated.
4. After code changes are complete, refresh the `.md` file once more to align with the new logic and report the completion of the task.