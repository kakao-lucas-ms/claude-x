---
name: cx-best
description: Quick view of your best prompts
---

# Best Prompts Quick View

$ARGUMENTS

Quickly show the top 3 best prompts.

## Instructions

1. Call `mcp__claude-x__get_best_prompts` with:
   - limit: 3
   - strict: true

2. Display results concisely:
   - Show prompt preview
   - Show composite score
   - Show category

## Example Output

```
🏆 Your Top 3 Prompts

1. [7.8] 기능 구현
   "LoginForm.tsx에 validation 추가해줘. React 프로젝트야."

2. [7.5] 디버깅
   "[Image] svg 아이콘이 flex 정렬을 안먹는 이유와 수정방안..."

3. [7.2] 아키텍처
   "tailwind에서 모바일→PC 전환시 레이아웃 틀어지는 개선법..."
```
