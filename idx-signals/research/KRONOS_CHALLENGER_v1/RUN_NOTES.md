# Run notes

- Protocol JSON and cohort were locked locally before the pilot price archives were downloaded. The protocol was
  committed and published as `3f8137b8bbc55941c758219524dd4de662138e19` before preparation parsed the archive frames
  and wrote outcomes. Downloads began before GitHub publication: this deviates from the stricter house template's
  requirement to push before *downloading* outcome data. It is recorded rather than described as full preregistration.
- Cohort is a deterministic 128-event sample of 4,413 already-exposed legacy ignition identifiers after June 2024.
  Only identifiers were inspected during selection. Existing source outcomes were not used for selection.
- An initial dependency install requested general packages from the PyTorch-only wheel index and failed before
  installing the model. Dependencies were then installed from their appropriate indexes. This did not produce a forecast.
- A real-sample parser test was added while downloads were running, extracting the same parse operations into a
  helper. The running preparation process used the original behavior-equivalent parser; the final parser is tested
  on the checksum-verified captured sample. No strategy threshold or model setting changed.
- The optional adapter is isolated in this new research folder. It invokes the MIT-licensed upstream Kronos code at
  its pinned commit; upstream code and pretrained weights are not vendored into KOD or its live collectors.
- Failures retain baseline exposure during scoring. Missing outcomes are counted and prohibit a promising verdict.
  All per-event predictions, including rejections, are retained. No model fitting or threshold search is performed.
