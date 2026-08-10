# Example MCP prompts

## Bounded first run

```text
Use fetch-actor-details for
nomad-agent/linkedin-enrich-translate-normalize-scraper first. Confirm its
deployed input schema and current pricing, then use only its configured Actor
tool. Search for at most 5 remote or hybrid TypeScript developer jobs in Spain
posted in the last 7 days. Disable translation, AI enrichment, analytics, raw
descriptions, and cross-run deduplication.

If the Actor is still running, follow nextStep with get-actor-run until it is
terminal. Only after SUCCEEDED, read RUN-SUMMARY from the run's default
key-value store. If the exact nomad-agent-linkedin-run-summary-v1 record says
blocked=true and reschedule.recommended=true, wait until its notBefore time and
repeat the exact input once. Never automatically retry more than once. Fetch
up to 5 rows from the latest successful run's default dataset with
get-dataset-items. Validate that every row is nomad-agent-job-v1 with exactly
schemaVersion, identity, data, custom, llm, and raw at the top level. If the
successful dataset is empty without a retry recommendation, report "no
matching jobs" without making up a row or silently broadening the search.
```

## Compare two explicit search partitions

```text
Use fetch-actor-details first and confirm the deployed input schema and current
pricing. Then use the configured LinkedIn normalized Actor once with
linkedinSearch v1. Search these partitions in deterministic newest-first order:
1. frontend engineer in Spain
2. TypeScript developer in European Union

Return at most 10 total jobs, not 10 per partition. Include remote and hybrid
work arrangements, use the last 7 days, and disable translation, AI
enrichment, analytics, raw descriptions, and cross-run deduplication. Poll the
run to SUCCEEDED, honor at most one valid structured RUN-SUMMARY blocked retry,
and retrieve the latest successful run's default dataset with
get-dataset-items.
Keep the canonical records and give me a compact comparison by partition only
when the source data supports it; do not guess which partition produced a row.
```

## Diagnose an empty or failed run

```text
Use fetch-actor-details first to compare the deployed contract with the input
that was used. Then inspect the most recent result from the configured LinkedIn
Actor. Distinguish:
- a non-terminal run that still needs get-actor-run polling;
- SUCCEEDED with an empty dataset;
- SUCCEEDED with a valid structured blocked-run reschedule recommendation;
- FAILED, TIMED-OUT, or ABORTED.

For an empty successful dataset, report the exact search constraints and
whether cross-run dedupe was enabled. Do not broaden or rerun the search unless
the exact v1 RUN-SUMMARY recommends one same-input retry or I approve a changed
input. For an error, report runId, status, statusMessage, and exitCode and tell
me to inspect the Apify run log; never present partial dataset rows as a
successful search.
```
