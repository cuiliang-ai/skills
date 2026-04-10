---
name: blog-review
description: Review and score blog articles for cuiliang.ai using a structured 8-dimension rubric. Use this skill whenever the user asks to review, score, rate, evaluate, or critique a blog article, or mentions 打分, 评分, 评审, review, score, rate an article. Also trigger when user asks to check article quality before publishing, or says "review 文章", "给文章打分", "评价这篇文章". Works for both draft articles and published posts.
---

# Blog Article Review Skill

Review articles for **cuiliang.ai** — an AI Agent engineering blog targeting architects, developers, and technical managers.

## Gate Check (Must Pass Before Scoring)

From the blog's publishing standard:

> **读者花 10-15 分钟读完这一篇后，能说出一个他之前不知道的、能改变他下一步行动的东西吗？**

If the answer is no, report "**未通过发表门槛**" with explanation. Do not proceed to scoring.

If yes, state what the actionable takeaways are (list 2-4 specific ones), then proceed.

## Eight Scoring Dimensions

Score each dimension on a 10-point scale. For each dimension, provide:
1. The numeric score
2. A 2-4 sentence justification citing specific parts of the article
3. Specific deduction reasons if below 9.5

### 1. 命题价值 (Thesis Value)

Does the article address a real, current knowledge gap or pain point? Is the thesis sharp enough — does it challenge a common assumption or fill a blank that existing discussions haven't covered?

- 9.5+: Identifies a blind spot most practitioners haven't articulated yet
- 9.0: Clear value proposition with meaningful increment over existing discussions
- 8.5: Valid topic but partially covered elsewhere
- <8.0: Retreads well-known ground without new angle

### 2. 结构设计 (Structure Design)

Is the logical progression clear? Is reader cognitive load well-managed (e.g., establish framework before diving in, general-to-specific flow)? Are section proportions balanced relative to their importance?

- 9.5+: Each section builds on the previous; reader never feels lost
- 9.0: Clear flow with minor proportion imbalances
- 8.5: Logical but has "flat list" tendencies or some sections too thin/thick
- <8.0: Reader has to backtrack to understand connections

### 3. 论证质量 (Argumentation Quality)

Are core claims backed by evidence (cases, code, data, comparisons)? Are sources authoritative and verifiable? Are there unsupported assertions? Is the balance between positive and negative examples adequate?

- 9.5+: Every major claim has concrete, verifiable support
- 9.0: Strong overall with 1-2 claims needing more backing
- 8.5: Some "assertion without evidence" paragraphs
- <8.0: Multiple core claims lack support

### 4. 信息密度 (Information Density)

How much useful information per unit of reading time? Are there deletable filler paragraphs (common-knowledge padding, repetition)? Do code blocks, quotes, and diagrams effectively increase density?

- 9.5+: Every paragraph delivers new information; multi-modal elements amplify
- 9.0: High density with minor common-knowledge padding
- 8.5: Some sections could be compressed without loss
- <8.0: Significant filler or repetition

### 5. 可操作性 (Actionability)

After reading, does the reader know what to do next? Are action items prioritized? Are there reusable templates, examples, or checklists?

- 9.5+: Clear priority-ordered actions with copy-paste-ready templates
- 9.0: Clear actions with some templates/examples
- 8.5: Actions implied but not explicitly prioritized or templated
- <8.0: Reader finishes thinking "interesting, but now what?"

### 6. 引用与可信度 (Citations & Credibility)

Are factual claims backed by verifiable sources? Are citations formatted consistently (footnotes preferred)? Have numbers, timelines, and attributions been fact-checked? Are there any false quotes or misattributions?

- 9.5+: All key claims have footnotes with verifiable URLs; numbers fact-checked
- 9.0: Most claims sourced; minor gaps in less critical areas
- 8.5: Inline links but no systematic footnotes; some unverified claims
- <8.0: Multiple unsourced factual claims or verified errors

**Hard rule**: If a factual error is found (wrong number, misattribution, fabricated quote), this dimension is capped at 8.0 regardless of other qualities. Flag the specific error.

### 7. 原创洞察 (Original Insight)

Does the article offer the author's own analytical framework, concept coinage, or cognitive reframing? What percentage is "things you can't read elsewhere"? Or is it primarily an information synthesis?

- 9.5+: Introduces a new framework or concept that reframes how readers think
- 9.0: Has clear original analysis layered on top of existing knowledge
- 8.5: Mostly synthesis with some original commentary
- <8.0: Pure information aggregation

### 8. 文字质量 (Writing Quality)

Are sentences crisp and punchy? Are metaphors/analogies accurate (not pretentious)? Is Chinese-English mixing natural? Is terminology used correctly? Is there good rhythm (long/short sentence alternation, paragraph breathing)?

- 9.5+: Memorable phrases; rhythm pulls reader forward; analogies land perfectly
- 9.0: Clean prose with good flow; minor rough spots
- 8.5: Competent but occasional awkward phrasing or terminology misuse
- <8.0: Noticeably rough or jargon-heavy in ways that slow reading

## Scoring Rules

**Composite score** = arithmetic mean of all 8 dimensions, with two modifiers:

1. **Floor drag**: If any dimension scores below 8.0, the composite is capped at 8.5 — one serious weakness drags overall reading experience
2. **Citation veto**: Verified factual errors cap dimension 6 at 8.0 and must be flagged explicitly

## Output Format

Structure the review as follows:

```
## 《[Article Title]》Review

### 发表门槛检验
[Pass/Fail + actionable takeaways if pass]

### 分维度评分

| 维度 | 分数 | 评价 |
|------|------|------|
| 命题价值 | X.X/10 | [justification] |
| 结构设计 | X.X/10 | [justification] |
| 论证质量 | X.X/10 | [justification] |
| 信息密度 | X.X/10 | [justification] |
| 可操作性 | X.X/10 | [justification] |
| 引用与可信度 | X.X/10 | [justification] |
| 原创洞察 | X.X/10 | [justification] |
| 文字质量 | X.X/10 | [justification] |

### 综合评分：X.X / 10

### 主要优势
[3-4 bullet points citing specific strengths]

### 可提升方向
[2-4 bullet points with concrete, actionable improvement suggestions]
```

## Calibration Reference

These scores from previous reviews anchor the scale:

- **9.27/10**: LLM series article 1 "一句话是怎么变成 AI 回复的" — 27 footnotes, strong original framework, excellent code experiments
- **8.94/10**: LLM series article 3 "Agent 时代的推理框架" — high data density, practical decision tables, slightly weaker on original insight

## Important Notes

- Target audience is **AI Agent engineering practitioners**, not general public. Evaluate information density and thesis value through this lens — what's "common knowledge" for this audience is different from general tech readers.
- The blog publishes in **Chinese** with English technical terms mixed in. Evaluate Chinese-English mixing naturalness as part of writing quality.
- When reviewing, actually verify key factual claims if possible (search the web, check URLs). Don't just assess whether claims "seem right" — spot-check them. This is especially important for numbers, dates, and attributed quotes.
- If the article is a draft (not yet published), note any issues that should be fixed before publishing.
