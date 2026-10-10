# Application design and MS1 refinement

| Screen | User action | Live MS2 backend | MS3 extension |
|---|---|---|---|
| Draft | Type/paste question and essay; select band | Validation and word count | Adapted-model assessment |
| Feedback | Switch TR/CC/LR/GRA and inspect sources | Criterion/band retrieval, exact quotes, practice examples | Calibrated scores and personalized advice |
| Goals | Submit target, position and ideas | Preserve requirements and retrieve rubric context | Constrained generation |
| Model essay | Inspect/download writing brief | Backend outline and sources | Full essay + separate explained scores |

```text
        Draft -> Feedback -> Your goals -> Model essay
DRAFT                              FEEDBACK
Question + essay editor            Four criterion tabs
Target band                        Draft quote | Official band details
Review my writing                  Next step + before/after technique
GOALS                              MODEL ESSAY
Target + position + ideas          Preserved requirements + outline
Prepare writing brief              Download brief | Source context
```

Feedback shows actual criterion detail in the side panel rather than repeating top-level score cards. Source links include PDF pages; half-band targets show adjacent integer descriptors. Labels, focus states, validation/loading states and a responsive layout support the workflow.

Dynamic essay content is escaped before rendering. A same-origin gateway keeps database access on the private Docker network. Ports bind to localhost. The app neither logs private writing nor saves it as training data. The demo essay is authored sample content. Production authentication/history/privacy controls follow later. There is no photo or OCR input.
