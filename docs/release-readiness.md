# v0.1 release-readiness review — 2026-10-21

**Suitable for a local fictional portfolio demonstration and PR review.** This is
not certification of real scouting decisions. No GitHub release or merge is part
of Milestone 5c. Scoring formulas, eligibility rules, dependencies and the default
four-player review list are unchanged.

## Checklist

| Item | Status | Evidence / remaining boundary |
| --- | --- | --- |
| README quick start | Completed | Fresh Python 3.12 virtual environment; `pip install -e ".[ui]"`; Streamlit startup, HTTP 200 and actual browser demo loading |
| Three scouting sections | Completed | Synthetic AppTest workflows and real Chromium interactions: exploration/search, roles/weights/priorities, shortlist explanations and hypothetical midfield changes |
| Local files and external reviews | Completed with synthetic sources | Browser exercised local JSON, evidence-bearing reviews, empty cohorts, missing files and source switching; automated tests cover malformed input, revised reviews and transfers |
| Isolation, caching and integrity | Completed with synthetic sources | Existing cache tests cover one calculation across controls/reviews, file invalidation, explicit reload and independent cached copies; unknown fictional markers fail explicitly |
| Historical-pair correction | Completed | Match-sheet affiliation survives missing global player metadata; missing metadata is labeled, unknown pairs still fail, and no-sample bench players remain ineligible |
| Browser source-reset correction | Completed | Explicit widget updates reset browser-visible values as well as Python state; regression tests inspect the frontend reset flags |
| Desktop visual review | Completed | Actual Chromium 154.0.8037.57 at 1440 px width; genuine fictional screenshots linked below; tables, explanations, labels and warnings inspected |
| Automated checks | Completed locally | Both Python versions below pass lint, format and all tests; GitHub CI repeats its 3.12/3.13 matrix on the PR |
| Football validity and cohort | Partially verified | Four default positional-proxy reviews are a demonstration. External evidence is supplied by the analyst, not verified by the application; role templates/thresholds are not calibrated football ground truth |
| Source provenance and licensing | Partially verified | Earlier original-item metadata confirmed CC BY 4.0; metadata checksums matched. Raw event findings are mirror-derived; original whole-event-archive identity remains unverified. See [data sources](data-sources.md) |
| New real-data simulator + external-review smoke | Blocked | No legitimate local Wyscout source files available. No data downloaded or real results fabricated |

## Automated verification

| Local Python | Ruff | pytest | Streamlit | Result |
| --- | --- | --- | --- | --- |
| 3.12.14 | 0.17.0 | 9.1.1 | 1.66.0 | **476 passed; 0 failed, 0 skipped** |
| 3.13.5 | 0.17.1 | 9.1.1 | 1.66.0 | **476 passed; 0 failed, 0 skipped** |

Commands from the repository root, with the selected environment activated:

```sh
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -rA
```

The clean 3.12 setup followed the README, using a temporary environment path. The
system 3.13 interpreter lacked `ensurepip`; pip's supported `--python` option
installed the same existing `dev,ui` extras into that temporary environment.
This was an environment setup issue, not a skipped test or project dependency
change. Dependency ranges remain unpinned; these results cover the versions above.

## Browser and visual review

The app ran on loopback from the clean quick-start environment. Installed
Playwright 1.62.0 drove actual headless Chromium; captured screenshots were
visually inspected. This is browser rendering, not an AppTest screenshot or
fabricated UI. No browser/tool dependency was added to the project.

The browser tour loaded the fictional demo, searched Casey, changed role/style
priority and metric weights, inspected component explanations, changed simulator
settings, triggered insufficient-minutes warnings and recovered. It also loaded
the existing **explicitly synthetic** local-format fixture with external reviews,
switched to an empty review set, rejected a missing directory, and returned to the
separate fictional source. No JavaScript page errors were recorded.
The browser exposed a stale search value after a source reset despite correct
server-side state. Explicit widget writes now reset the native controls too;
the regression checks the frontend `set_value` protocol flags, not just Python
values. Repaired reference and simulator selections use the same explicit updates.

Genuine default-demo captures:

- [Replacement finder](screenshots/fictional-replacements.png)
- [Hypothetical midfield comparison](screenshots/fictional-midfield.png)

All names, clubs, events, statistics and scores in these captures are fictional.
The shortlist now places minutes and coverage beside scores before audit IDs and
weighted points, avoiding the previously clipped coverage column at this width.
Wide audit/feature tables still scroll horizontally. This desktop review does not
claim mobile, cross-browser or formal accessibility certification.

## Real-data and modeling limits

Searches of accessible `/workspace` and `/tmp` paths found only checked-in or
locally generated synthetic records, excluding test/cache directories; one system
directory was unreadable. Therefore no new real Bundesliga simulator or external
review smoke ran. Earlier dated audits in [metrics](metrics.md) and
[data sources](data-sources.md) remain historical evidence, not 5c results.

The historical audit retained usable durations for 267/306 matches; uneven missing
coverage can bias comparisons. Last-event time is approximate, not a final whistle.
Scores are cohort-relative, not probabilities or independently validated quality
rankings. Midfield coverage describes a hypothetical trio's feature representation,
not chemistry, tactical synergy or predicted performance. Check provenance,
attribution and applicable terms before publishing data or derived real outputs.
