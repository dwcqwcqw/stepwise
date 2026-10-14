# Application design and interactions

The Stepwise four-screen design uses a consistent white/lilac palette, clear typography and source-linked feedback.

1. **Your draft:** one wide editor for the question and typed/pasted essay, sample draft, live word count and Review button. No target-band sidebar, decorative `04` panel, image upload or OCR.
2. **Feedback:** actual overall Task 2 estimate and four criterion scores. Selecting a criterion reveals its score explanation, exact essay evidence, an actionable next step and a revision of the learner's words. The right panel prioritizes current/next-band paragraph matches with exact official wording and page citations. The 20 supplementary skill checks are expandable; the interface shows the assessed band and the next band only. Four independently assessed criteria cover all 119 Task 2 standards.
3. **Your goals:** enter target band, position and ideas to preserve. Submit the question and these requirements to generation.
4. **Model essay:** complete prose and idea coverage notes, the user's preset **Target band**, and four qualitative criterion comments with 20 expandable skill details. Each criterion includes an exact essay excerpt, an actionable next step, a before/after refinement and official target-band guidance. No generated-essay scoring, average, candidate reassessment or score-calibration loop. Download the essay and commentary as text.

```text
Question + typed/pasted essay
  → /api/feedback/stream → complete Task 2 rubric → live assessment
  → four actual scores + 119 descriptor matches + 20 skill checks + revisions

Question + target + position + ideas
  → /api/model-essay/stream → official target-band guidance → essay generation
  → one qualitative commentary call → preset target + four comments and examples
```

Original quotes are selected by evidence ID and copied by the server; official sources are attached from the retrieved index. Dynamic text is escaped. Writing never enters the rubric index or persistent browser storage. The preset target is a writing goal, not a newly assessed score. Submitted drafts continue to be assessed independently of any target.

## Processing progress

Generation shows only **Write your essay → Prepare your feedback**. One streamed request covers the two operations. Progress follows real backend events and an elapsed timer. The generator may repair invalid length/content once; the feedback call may repair malformed references once. Neither repair scores or recalibrates the essay. Failed connections preserve form inputs. Submitted-draft review retains its separate grading and validation progress.

Historical calibration designs and measured receipts are preserved in earlier release documents; [model-essay-commentary.md](model-essay-commentary.md) describes the current behavior.
