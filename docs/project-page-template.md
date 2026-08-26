# Project Page Template

Two formats. Use the applied-project format by default; use the research
format only for a deeper, longer-running project.

Every page starts with the YAML block, then a one-sentence takeaway in bold
before the first header.

## YAML front matter

```yaml
---
title: "<Specific, concrete title>"
subtitle: "<The question, phrased as a question>"
description: "<One sentence: what was found. Shown on the project card.>"
image: images/thumbnail.svg
image-alt: "<Describe the figure for screen readers>"
categories:
  - <Method, e.g. Time Series / Causal Inference>
  - <Language, e.g. R / Python>
  - <Domain or skill, e.g. Visualization / Policy Analysis>
order: <integer; controls position in the listing>
---
```

`description` and `image-alt` are not optional — the first is the only text a
reader sees on the Projects page, the second is required for accessibility.

## Applied project

1. **Takeaway** — one sentence, bolded, before any header. What did you find?
2. **Question and motivation** — why this question, why it is worth asking
3. **Data** — source, coverage, known quality problems
4. **Cleaning** — what was dropped or corrected, and what that cost
5. **Method** — what you did and why it suits the question
6. **Results** — the main visualizations, each with a caption that states its point
7. **Interpretation** — what the results mean, in plain language
8. **Uncertainty and robustness** — how confident, and what was checked
9. **Limitations** — what this cannot show
10. **Code** — link to the GitHub repository
11. **Next steps** — optional

## Research project

1. **Abstract** — executive summary
2. **Research question**
3. **Motivation and related work**
4. **Data and measurement**
5. **Methods**
6. **Validation**
7. **Main results**
8. **Error analysis**
9. **Sensitivity analysis**
10. **Limitations**
11. **Discussion**
12. **Technical appendix** — may be a separate `appendix.qmd`
13. **Reproducibility materials**

## Notes

- Sections are `##` headers. The page `title` is the only `#`.
- Prefer a static figure. Reach for Plotly only when hover, zoom, or filtering
  adds analytical value; reach for a separate app only when the interaction
  requires live execution.
- Limitations are a feature of the page, not an admission. Write them plainly.
