# Zapier editor recipe

Zapier has no portable workflow-import format for this template. Build the Zap
from [`template-spec.json`](template-spec.json) and preserve these controls.

1. Trigger: **Schedule by Zapier → Every Day**. Keep the Zap off during setup.
2. Action: **Apify → Run Actor**.
   - Actor: `nomad-agent/ai-job-fit-scorer`
   - build: keep the template pinned to verified build `0.1.22` (never `latest`)
   - input: the bounded five-item search starter after reviewing the explicit
     search terms and candidate profile; keep `resultMode: "shortlist"` and
     `minDeliveryScore: 2` for the first run
   - maximum total charge: USD 0.10
3. Confirm the action returns one terminal `SUCCEEDED` run with exit code 0,
   exact verified build, and its own dataset ID. If the Apify Zapier action does not
   expose these fields, add Webhooks by Zapier requests to the exact run API;
   do not use a latest-run lookup.
4. Action: **Apify → Get Dataset Items**, using only the dataset ID from step 2.
5. Filter each row: schema is `nomad-ai-job-fit-v1`, scoring algorithm is
   `scoring-v3`, status is `scored`, and `deliveryScore >= 2`.
6. Action: **Google Sheets → Lookup Spreadsheet Row**, lookup column
   `matchKey`.
7. Paths: update the located row or create a new row. Map columns in
   [`../shared/ai-job-fit-google-sheets-columns.csv`](../shared/ai-job-fit-google-sheets-columns.csv)
   order; serialize blocking gates and the complete evaluation as JSON.

Before enabling the Zap, inspect scorer `RUN-SUMMARY` v3 or v4 manually or add
an exact key-value-store Webhook step. For v4, reconcile all drop, hold, scored,
failed, filtered, and output counts and confirm every shortlist row meets the
declared delivery threshold. Reconcile the single `job-fit-result` meter at
$0.02 per retained policy-compatible row, confirm the $0.25/two-attempt provider circuit
breaker, and inspect per-source provenance.
Prove one named row was created, rerun the same fixture and prove it updated,
then prove partial-source and failed/AI-failed fixtures do not create unsafe
writes. Record the live run/build and destination evidence; a successful editor
test alone is not publication or natural-workload proof.
