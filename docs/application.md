# Application design and interactions

The Stepwise four-screen design uses a consistent white/lilac palette, clear typography and source-linked feedback.

1. **Your draft:** one wide editor for the question and typed/pasted essay, sample draft, live word count and Review button. No target-band sidebar, decorative `04` panel, image upload or OCR.
2. **Feedback:** actual overall Task 2 estimate and four criterion scores. Selecting a criterion reveals its score explanation, exact essay evidence, an actionable next step and a revision of the learner's words. The right panel prioritizes current/next-band paragraph matches with exact official wording and page citations. The 20 supplementary skill checks are expandable; the interface shows the assessed band and the next band only. Four independently assessed criteria cover all 119 Task 2 standards.
3. **Your goals:** enter target band, position and ideas to preserve. Submit the question and these requirements to generation.
4. **Model essay:** full generated prose, coverage notes for the requested ideas, and a separate target-blind assessment with four scores, detailed subcriteria, revisions and official citations. Target and independently assessed band are shown together. A candidate that misses the exact selected band is rewritten and reassessed; persistent mismatches produce a retry message rather than an incorrectly targeted result. Download the essay and explained scores as text.

```text
Question + typed/pasted essay
           ↓ /api/feedback/stream
Complete Task 2 rubric retrieved from Qdrant
           ↓ live Gemini assessment + evidence validation
Four scores + 20 qualitative checks + revisions
           ↓ user enters target / position / ideas
/api/model-essay/stream → target rubric → Gemini generation
           ↓ essay text only + original question
New target-blind Gemini assessment → validated scores / citations
```

The frontend escapes all dynamic text. User input is bounded and validated. Model calls have timeouts and bounded retries; source IDs and exact essay quotations are checked before returning results. Errors remain errors rather than fabricated feedback. Generated assessment does not receive the target, generator's title, notes or self-rating claims. The source library is server-owned; user writing is never inserted into its vector collection.

These are real model outputs, but contract tests and successful API calls do not establish scoring accuracy. Criterion agreement, repeatability, cost and latency benchmarking remain subsequent evaluation work.

## Real processing progress

Both submit buttons immediately open a loading view and prevent duplicate submission. The same POST connection streams NDJSON events through Cloud Run and the Vercel/Compose gateway. Review shows rubric retrieval, four parallel criterion checks and final evidence/arithmetic validation. Generation first shows target-rubric retrieval and writing, then a separate target-blind assessment and exact target confirmation. If a rewrite is needed, the real attempt and fresh criterion progress are shown. Each criterion changes state only when the backend reports it; the timer shows elapsed time without estimating a percentage. Heartbeats keep the connection active without claiming progress.

Failures restore the form with its text intact. Only identical, already validated feedback can be reused from a three-entry in-memory cache in the current browser tab. Changed inputs trigger new inference; generation always runs again. Reloading/closing the tab discards the cache. No learner text is stored in localStorage, a task database or the source index.

See [performance and reproduction](performance.md) for the compact inference protocol, measurements and test commands.

See [selected-band generation](target-bands.md) for proficiency profiles, the bounded rewrite loop and regression verification.
