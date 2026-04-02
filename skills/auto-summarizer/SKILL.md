---
name: auto-summarizer
description: >
  Summarize long content, extract key insights, and produce concise summaries. 
  Use when: (1) User shares a long article/doc/URL, (2) User asks for "tl;dr" or 
  "summarize", (3) Need to extract action items from conversation history.
---

# Goal
Transform long content into digestible, actionable summaries.

# Instructions

## 1. Summarize Content
When given long content (article, doc, web fetch):
- Extract the main thesis/point (1 sentence)
- Key findings (3-5 bullet points)
- Any actionable takeaways

## 2. TL;DR Format
Structure output as:
```
## TL;DR
[One sentence summary]

## Key Points
- Point 1
- Point 2
- Point 3

## Action Items (if any)
- [ ] Action 1
```

## 3. Extract Action Items
From conversation or documents:
- Identify explicit tasks or to-dos
- Note who "owns" each item
- Flag deadlines if mentioned

## 4. History Summarization
When summarizing conversation history:
- Group by topic/theme
- Highlight decisions made
- Note pending items

# Constraints
- Summaries max 300 words unless user asks for longer
- Always preserve key numbers/dates/metrics
- Don't lose nuance — summarize, don't distort

# Success Criteria
- User can understand content without reading full text
- Action items are clear and trackable
- Key context preserved