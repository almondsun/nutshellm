# Submission checklist

## Required before release

- [ ] Rotate the PariTok key previously stored in local project notes.
- [x] Run the complete test/lint/type-check/build suite.
- [x] Deploy one Docker replica with a persistent volume and production safeguards.
- [x] Run all three curated scenarios against the live deployment.
- [x] Record measured median input saving and deterministic quality pass rate.
- [ ] Capture the PariTok hosted dashboard showing matching API activity.
- [x] Export one redacted sample run into `examples/`.
- [x] Verify the public repository shows the Apache 2.0 license and PariTok credit.
- [x] Confirm no secrets appear in Git history, images, logs, or browser bundles.

## Devpost material

- [x] Elevator pitch under 200 characters.
- [x] Project story: inspiration, what it does, implementation, challenges,
      accomplishments, lessons, and next steps.
- [ ] Tags: PariTok, FastAPI, React, context-compression, LLM, developer-tools.
- [x] Public app and source links.
- [ ] PariTok account email entered privately in Devpost.
- [x] Three 3:2 screenshots: landing/workbench, result evidence, context decisions.
- [x] Thumbnail in 3:2 format.
- [ ] Public YouTube/Vimeo demo under three minutes.
- [ ] Actionable PariTok feedback submitted without exposing private data.
- [ ] Optional social post tagged `#BuiltWithParitok`.
