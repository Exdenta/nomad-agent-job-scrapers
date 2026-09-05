# Zapier editor recipe

Zapier has no portable workflow-import format for this template. Build the Zap
from [`ai-job-fit-scorer-template-spec.json`](ai-job-fit-scorer-template-spec.json) and preserve these controls.

1. Trigger: **Schedule by Zapier → Every Day**. Keep the Zap off during setup.
2. Action: **Apify → Run Actor**.
   - Actor: `nomad-agent/ai-job-fit-scorer`
   - build: keep the template on selector `latest`; record the returned immutable build
   - input: the bounded five-item search starter after reviewing the explicit
     search terms and candidate profile; keep `resultMode: "shortlist"` and
     `minDeliveryScore: 2` for the first run
   - maximum total charge: USD 0.10
3. Configure Run Actor to wait for completion and retain its returned run ID,
   immutable build ID, and numeric build number as `startedRun`.
4. Add **Webhooks by Zapier → GET** for that exact run ID. Map its `data`
   object to `run`. Require `SUCCEEDED`, exit code 0, the scorer Actor ID,
   and unchanged run/build identity. Stop if the run is non-terminal.
5. Add a required **Webhooks by Zapier → GET** for
   `https://api.apify.com/v2/key-value-stores/{{run.defaultKeyValueStoreId}}/records/RUN-SUMMARY`.
   Map its JSON body to `summary`. Both GET actions use a private Apify bearer
   connection; keep the token out of prompts and template files.
6. Add **Apify → Get Dataset Items** using `run.defaultDatasetId`.
7. Before any Sheet write, bind the filter to `startedRun`, `run`, `summary`,
   and the dataset row as specified in the editor recipe. Require summary
   actor/run/build ID/build number to equal the exact `run` receipt. Also
   require row schema `nomad-ai-job-fit-v1`, status `scored`, and
   `deliveryScore >= 2`.
8. Add **Google Sheets → Lookup Spreadsheet Row**, lookup column `matchKey`.
   Update the located row or create a new row using
   [`../shared/ai-job-fit-google-sheets-columns.csv`](../shared/ai-job-fit-google-sheets-columns.csv).

The summary fetch and identity filter are required on every execution.
Before enabling the Zap, additionally inspect the closed v3/v4 contract,
result-policy count arithmetic, $0.02 meter, and $0.25/two-attempt provider
circuit breaker. The editor specification has not been executed in Zapier.
Prove one named row was created, rerun the same fixture and prove it updated,
then prove partial-source and failed/AI-failed fixtures do not create unsafe
writes. Record the live run/build and destination evidence; a successful editor
test alone is not publication or natural-workload proof.
