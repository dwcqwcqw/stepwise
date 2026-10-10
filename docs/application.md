# Application design and interactions

The Stepwise four-screen design uses a consistent white/lilac palette, clear typography and source-linked feedback.

1. **Your draft:** one wide editor for the question and typed/pasted essay, sample draft, live word count and Review button. No target-band sidebar, decorative `04` panel, image upload or OCR.
2. **Feedback:** actual overall Task 2 estimate and four criterion scores. Selecting a criterion reveals its score explanation, exact essay evidence, an actionable next step and a revision of the learner's words. The right panel contains the official subcriteria with model judgments and evidence; expandable source cards show the awarded/next-band descriptors.
3. **Your goals:** enter target band, position and ideas to preserve. Submit the question and these requirements to generation.
4. **Model essay:** full generated prose, coverage notes for the requested ideas, and a separate target-blind assessment with four scores, detailed subcriteria, revisions and official citations. Target and assessed band are shown separately, including when the target is not met. Download the essay and explained scores as text.

```text
Question + typed/pasted essay
           ↓ /api/feedback
Complete Task 2 rubric retrieved from Qdrant
           ↓ live Gemini assessment + evidence validation
Four scores + 20 qualitative checks + revisions
           ↓ user enters target / position / ideas
/api/model-essay → target rubric → Gemini generation
           ↓ essay text only + original question
New target-blind Gemini assessment → validated scores / citations
```

The frontend escapes all dynamic text. User input is bounded and validated. Model calls have timeouts and bounded retries; source IDs and exact essay quotations are checked before returning results. Errors remain errors rather than fabricated feedback. Generated assessment does not receive the target, generator's title, notes or self-rating claims. The source library is server-owned; user writing is never inserted into its vector collection.

These are real model outputs, but contract tests and successful API calls do not establish scoring accuracy. Criterion agreement, repeatability, cost and latency benchmarking remain subsequent evaluation work.
