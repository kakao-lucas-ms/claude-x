---
name: cx-analyze
description: Comprehensive analysis of Claude Code usage patterns
---

# Comprehensive Claude Code Analysis

$ARGUMENTS

Perform a complete analysis using all available claude-x tools.

## Instructions

1. **Session Overview**
   Call `mcp__claude-x__analyze_sessions` to get overall statistics

2. **Prompt Quality Analysis**
   Call `mcp__claude-x__get_best_prompts` with strict=true for top performers
   Call `mcp__claude-x__get_worst_prompts` for areas needing improvement

3. **Pattern Discovery**
   Call `mcp__claude-x__get_prompt_patterns` to find successful patterns

4. **Generate Report**
   Combine all data into a comprehensive report with:
   - Executive summary
   - Key metrics
   - Strengths (from best prompts)
   - Areas for improvement (from worst prompts)
   - Actionable recommendations

## Example Output Format

```
📈 Claude Code Usage Analysis
============================

## Executive Summary
You've had 150 sessions with 2,450 messages. Your prompt quality
averages 6.2/10 with room for improvement in context provision.

## Key Metrics
- Sessions: 150 | Messages: 2,450 | Code: 890 blocks
- Avg Prompt Score: 6.2/10
- Top Language: TypeScript (45%)

## Strengths
✅ Clear goal statements in 78% of prompts
✅ Good use of file references
✅ Efficient session lengths (avg 16 messages)

## Areas for Improvement
⚠️ 23% of prompts lack technology context
⚠️ Short prompts (<20 chars) score 40% lower
⚠️ Context-dependent prompts need more detail

## Recommendations
1. Always include file paths when discussing specific files
2. Mention the technology stack (React, TypeScript, etc.)
3. Be specific about expected outcomes
```
