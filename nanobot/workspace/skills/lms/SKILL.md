---
name: lms
description: Use LMS MCP tools for live course data
always: true
---

# LMS Skill

Use LMS MCP tools to fetch live course data from the LMS backend. This skill provides read access to labs, learners, and performance metrics.

## Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `lms_health` | none | Check if the LMS backend is healthy and report the item count |
| `lms_labs` | none | List all labs available in the LMS |
| `lms_learners` | none | List all learners registered in the LMS |
| `lms_pass_rates` | `lab` (string) | Get pass rates (avg score and attempt count per task) for a lab |
| `lms_timeline` | `lab` (string) | Get submission timeline (date + submission count) for a lab |
| `lms_groups` | `lab` (string) | Get group performance (avg score + student count per group) for a lab |
| `lms_top_learners` | `lab` (string), `limit` (int, default 5) | Get top learners by average score for a lab |
| `lms_completion_rate` | `lab` (string) | Get completion rate (passed / total) for a lab |
| `lms_sync_pipeline` | none | Trigger the LMS sync pipeline. May take a moment |

## Strategy

### When a lab parameter is needed but not provided

If the user asks for scores, pass rates, completion, groups, timeline, or top learners **without naming a lab**:

1. Call `lms_labs` first to fetch available labs
2. If multiple labs are available, use the `structured-ui` skill to present a choice
3. Use each lab's `title` field as the user-facing label
4. Pass the lab's `id` or `name` value to the subsequent tool call

Example flow:
```
User: "Show me the pass rates"
→ Call lms_labs
→ Present choice UI with lab titles as labels
→ User picks one
→ Call lms_pass_rates with the chosen lab
```

### Cooperating with structured-ui

When you need user input for a choice (like selecting a lab):

1. **Delegate to structured-ui**: Call the `structured_ui_choice` tool with:
   - `options`: Array of `{label: "Lab Title", value: "lab-id"}`
   - `question`: Clear question like "Which lab would you like to see?"
   - `multiple`: `false` for single selection

2. **Wait for the response**: The channel will render the appropriate UI (buttons, dropdown, etc.)

3. **Use the returned value**: The `value` field contains the lab ID to pass to LMS tools

This pattern ensures:
- Consistent UI across webchat, Flutter, and other channels
- Proper structured payloads instead of parsing text responses
- Better UX with clickable options instead of "type the number"

### When to use structured-ui

Use structured-ui for:
- Lab selection (from `lms_labs`)
- Learner selection (from `lms_learners`)
- Any multi-option choice where the user should pick one

Do NOT use structured-ui for:
- Yes/no questions (use channel-native confirmations)
- Free-text input
- When there's only one option (just proceed)

### Formatting numeric results

- **Percentages**: Format as `XX%` (e.g., `0.85` → `85%`)
- **Counts**: Use plain integers with optional thousands separator
- **Averages**: Round to 1-2 decimal places unless precision matters
- **Scores**: Show as percentage or fraction depending on context

Keep responses concise. Present data in a scannable format (tables, bullet points) rather than dense paragraphs.

### When asked "what can you do?"

Explain capabilities clearly:

> I can access live data from your LMS backend:
> - List available labs and learners
> - Show pass rates, completion rates, and group performance for any lab
> - Display submission timelines and top learners
> - Trigger a sync pipeline if data seems stale
>
> I cannot modify grades, enrollments, or course content — read-only access.

## Integration with structured-ui

When presenting lab choices or other multi-option selections:

- Let the `structured-ui` skill decide how to present the choice on supported channels
- Pass lab titles as `label` and lab IDs/names as `value` to the choice UI
- On unsupported channels, fall back to a plain text numbered list

## Limits

- Read-only: cannot create, update, or delete any LMS data
- No direct database access: works through the LMS API only
- Sync pipeline may take time: warn the user before calling `lms_sync_pipeline`
