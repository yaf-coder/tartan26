# Strategic Model Handoff Architecture

## Overview
Our research pipeline uses model orchestration across 3 different models, with the purpose of balancing cost, speed, and quality for the research system.

---

## Model Selection Strategy

### Design Principle: **Right Model, Right Task**

Each stage uses the **cheapest model that can deliver acceptable quality** for that specific task. More expensive models are reserved for tasks where quality directly impacts user value.

```

---

## 🔧 Implementation Details

### Paper Ranking
**File:** [`app.py:101-108`](file:///Users/aditya/tartan26/app.py#L101-L108)

```python
# MODEL HANDOFF: Using gpt-4o (not gpt-4o-mini) for paper ranking
# Rationale: This is a CRITICAL task requiring strong judgment
resp = await client.chat.completions.create(
    model="openai/gpt-4o",  #  Handoff #1
    ...
)
```

### Idea Synthesis
**File:** [`synthesize_ideas.py:16-19`](file:///Users/aditya/tartan26/tartan_backend/synthesize_ideas.py#L16-L22)

```python
# MODEL HANDOFF: Using gpt-4o for idea synthesis
# Rationale: Academic writing quality matters for literature review
DEFAULT_MODEL = "openai/gpt-4o"  #  Handoff #2
```

### Final Summary
**File:** [`summarize_review.py:68-77`](file:///Users/aditya/tartan26/tartan_backend/summarize_review.py#L68-L80)

```python
# MODEL HANDOFF: Using claude-3-5-sonnet for final literature review
# Rationale: Best-in-class synthesis, user-facing output
resp = await client.chat.completions.create(
    model="anthropic/claude-3-5-sonnet",  #  Handoff #3
    ...
)
```

