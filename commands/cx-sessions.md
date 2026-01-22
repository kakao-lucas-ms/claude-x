---
name: cx-sessions
description: Analyze Claude Code session statistics
---

# Session Statistics Analysis

$ARGUMENTS

Use the `mcp__claude-x__analyze_sessions` tool to get session statistics.

## Instructions

1. Call `mcp__claude-x__analyze_sessions` with:
   - project: "front" (or as specified in arguments)

2. Present statistics clearly:
   - Total sessions count
   - Total messages count
   - Total code blocks
   - Language distribution
   - Average messages per session

3. Provide insights:
   - Which languages are most used
   - Productivity patterns
   - Recommendations based on data

## Example Output Format

```
📊 Session Statistics for "front"

📁 Total Sessions: 150
💬 Total Messages: 2,450
💻 Total Code Blocks: 890
📝 Avg Messages/Session: 16.3

🌐 Language Distribution:
   TypeScript: 45% ████████████████
   JavaScript: 25% █████████
   Python: 15% █████
   CSS: 10% ███
   Other: 5% ██

💡 Insights:
   - Most productive sessions have 10-20 messages
   - TypeScript is your primary language
```
