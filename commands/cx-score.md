---
name: cx-score
description: Score a prompt for quality
---

# Prompt Quality Scorer

$ARGUMENTS

Score a prompt and get improvement suggestions.

## Instructions

1. Take the provided prompt text from $ARGUMENTS

2. Call `mcp__claude-x__score_prompt` with the prompt text

3. Display the results:
   - Structure score (0-10)
   - Context score (0-10)
   - Combined score
   - Specific improvement suggestions

## Example Usage

```
/cx:score "버그 수정해줘"
```

## Example Output

```
📊 Prompt Quality Score

Prompt: "버그 수정해줘"

┌─────────────┬───────┐
│ Structure   │ 3.0   │
│ Context     │ 1.0   │
│ Combined    │ 4.0   │
└─────────────┴───────┘

💡 Improvement Suggestions:
1. Add file paths (e.g., "src/components/Login.tsx에서")
2. Describe the bug specifically
3. Mention expected vs actual behavior

✨ Improved Version:
"src/components/Login.tsx에서 로그인 버튼 클릭시
TypeError 발생하는 버그 수정해줘.
user 객체가 undefined인 경우를 처리해야 할 것 같아."
```
