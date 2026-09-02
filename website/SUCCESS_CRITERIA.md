# Website success criteria

The website is complete only when every gate below has current evidence. A visual resemblance alone is not sufficient.

## 1. Reference-style fidelity

- Desktop uses the reference page's white documentation-directory composition: 68 px header, 1280 px container, 832/384 px content split, 32 px gutter, bordered Markdown panel, and sticky related-content sidebar.
- Typography, compact controls, neutral borders, card radii, shadows, and spacing remain visibly consistent with the reference.
- At 390 px wide, the layout becomes one column, the menu remains usable, and the page has no horizontal overflow.

## 2. Actor promotion and conversion clarity

- LinkedIn and EURAXESS each receive an outcome-led value proposition, intended use case, and direct Apify CTA.
- At least one direct Actor CTA is visible before the long documentation panel.
- The primary path never sends a visitor to a generic organization page when an Actor-specific destination is available.
- Claims are grounded in the repository and current official Actor pages; no invented accuracy, adoption, pricing, or performance metrics appear.

## 3. Conversion attribution

- Every Apify CTA includes deterministic `data-event`, `data-actor`, and `data-placement` metadata.
- Every direct Actor URL includes campaign, medium, source, and placement attribution parameters.
- Clicks emit a local `nomad-agent:analytics` browser event and can forward to an installed Plausible hook without requiring analytics or credentials to render the site.

## 4. Functional paths

- Header navigation, mobile navigation, anchors, external links, Actor selector, install-command switching, and copy action all work with pointer and keyboard input.
- Copy feedback is announced accessibly and does not leave controls in a stale state.
- Local HTML, CSS, JavaScript, and image assets return HTTP 200 from the documented preview command.

## 5. Trust and contract accuracy

- The six-root `nomad-agent-job-v1` contract and the `null` versus `[]` distinction are presented correctly.
- Exact-build, `RUN-SUMMARY`, dataset reconciliation, and named-destination boundaries are not overstated.
- Benchmark status, responsible-use guidance, and the project's unofficial/non-affiliation status are visible.

## 6. Discoverability, accessibility, and efficiency

- The document has unique metadata, semantic landmarks, useful accessible names, keyboard-visible focus states, and valid JSON-LD describing the two Actors without fabricated review data.
- Controls expose correct state with ARIA; motion respects `prefers-reduced-motion`.
- The site remains dependency-free at runtime and the first-party HTML, CSS, JavaScript, and SVG payload stays below 100 KiB uncompressed.
- Every indexable HTML document has one unique canonical URL; `sitemap.xml` and `robots.txt` publish exactly those URLs.
- Production search notification runs only after Firebase deployment and live URL verification succeed.
- A clean browser load produces no console errors.

## 7. Verification gate

- Automated website contract tests pass.
- The full repository test suite passes.
- Desktop and mobile browser QA confirms geometry, interactions, sticky behavior, overflow, and console state.
- Current LinkedIn and EURAXESS Apify destinations resolve before completion is claimed.

## Evidence ledger

| Gate | Status | Current evidence |
| --- | --- | --- |
| Reference fidelity | Passed 2026-08-24 | Browser measurements: 1440 px header 69; grid 1248; content/sidebar 832/384 with 32 px gutter; sticky top 16 after scroll. At 390 px: header 65, content 358, no overflow. Desktop/mobile captures inspected. |
| Actor promotion | Passed 2026-08-24 | Both direct Actor CTAs are visible above the docs panel; outcome and best-fit copy is Actor-specific; both official Apify destinations returned HTTP 200. |
| Attribution | Passed 2026-08-24 | Website tests validate all 12 Apify CTAs, unique placements, Actor metadata, and four UTM fields; runtime emits the documented local event and optional Plausible forwarding has no default network call. |
| Functional paths | Passed 2026-08-24 | Browser QA verified source selection, the exact copied EURAXESS command, accessible copy feedback, mobile open/Escape/close state, body lock release, and anchor/link targets. All local runtime assets returned HTTP 200. |
| Trust | Passed 2026-08-24 | Automated visible-copy checks cover contract roots, null/empty semantics, run/destination boundaries, benchmark status, and non-affiliation. Numeric accuracy and price claims are absent. |
| Discoverability/efficiency | Passed 2026-08-24 | Valid two-Actor JSON-LD, unique IDs, local asset integrity, focus/reduced-motion guards, zero browser warnings/errors, and 52,013-byte first-party runtime payload. |
| Verification | Passed 2026-08-24 | 10 website contract tests and the full 115-test repository suite passed; desktop/mobile browser QA and local/live HTTP probes passed. |
