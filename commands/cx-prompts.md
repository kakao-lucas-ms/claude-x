---
name: cx-prompts
description: Analyze prompt quality from Claude Code sessions
---

# Prompt Quality Analysis

$ARGUMENTS

Use the `mcp__claude-x__get_best_prompts` and `mcp__claude-x__get_worst_prompts` tools to analyze prompt quality.

## Instructions

1. Call `mcp__claude-x__get_best_prompts` with the following parameters:
   - project: "front" (or as specified)
   - limit: 10 (or as specified)
   - strict: true if --strict flag is provided

2. Present results in a clear, organized format:
   - Show rank, category, and score for each prompt
   - Display prompt preview (first 100 characters)
   - Include structure and context scores

3. Provide actionable insights:
   - Common patterns in successful prompts
   - Recommendations for improvement

## Example Output Format

```
🏆 Best Prompts (Top 10)

1. [기능 구현] Score: 7.5/10
   "LoginForm.tsx 컴포넌트에 validation 추가해줘..."
   📊 Structure: 6.0 | Context: 4.0 | Efficiency: 8.0

2. [디버깅] Score: 7.2/10
   ...
```

If `--worst` is specified, also show the worst prompts using `mcp__claude-x__get_worst_prompts`.
