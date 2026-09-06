#!/usr/bin/env node
// Bounded exact-run REST example. Requires Node 18+ and APIFY_TOKEN.
import { readFile } from 'node:fs/promises';

const ACTOR = 'nomad-agent~ai-job-fit-scorer';
const VERIFIED_BUILD = '0.1.22';
const EXPECTED_BUILD = (process.env.ACTOR_BUILD_NUMBER || VERIFIED_BUILD).trim();
const MAX_TOTAL_CHARGE_USD = 0.10;
const TERMINAL = new Set(['SUCCEEDED', 'FAILED', 'ABORTED', 'TIMED-OUT']);
const token = (process.env.APIFY_TOKEN || '').trim();
const base = (process.env.APIFY_API_BASE_URL || 'https://api.apify.com').replace(/\/$/, '');
if (!token) throw new Error('APIFY_TOKEN is required');
if (EXPECTED_BUILD !== VERIFIED_BUILD) {
  throw new Error(`ACTOR_BUILD_NUMBER must remain pinned to verified build ${VERIFIED_BUILD}`);
}

const inputPath = process.argv[2] || new URL('./ai-job-fit-scorer-input.json', import.meta.url);
const actorInput = JSON.parse(await readFile(inputPath, 'utf8'));
if (
  actorInput.mode !== 'search'
  || !actorInput.search
  || !Array.isArray(actorInput.search.keywords)
  || actorInput.search.keywords.length < 1
) {
  throw new Error('starter requires search mode with explicit keywords');
}
if (!Number.isInteger(actorInput.maxItems) || actorInput.maxItems < 1 || actorInput.maxItems > 5) {
  throw new Error('starter maxItems must be 1 through 5');
}

async function request(path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!response.ok) throw new Error(`Apify API ${path} returned HTTP ${response.status}`);
  return response.json();
}

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const query = new URLSearchParams({
  build: EXPECTED_BUILD,
  maxTotalChargeUsd: String(MAX_TOTAL_CHARGE_USD),
});
const started = await request(`/v2/actors/${ACTOR}/runs?${query}`, {
  method: 'POST',
  body: JSON.stringify(actorInput),
});
let run = started.data;
if (!run?.id) throw new Error('Actor start response contained no run ID');
const exactRunId = run.id;
const deadline = Date.now() + 10 * 60_000;

while (!TERMINAL.has(run.status)) {
  if (Date.now() >= deadline) throw new Error('Actor polling deadline exceeded after 600 seconds');
  const polled = await request(`/v2/actor-runs/${exactRunId}?waitForFinish=60`);
  run = polled.data;
  if (run?.id !== exactRunId) throw new Error('poll response changed the exact run ID');
}

if (run.status !== 'SUCCEEDED' || run.exitCode !== 0) {
  throw new Error(`Actor run ${exactRunId} ended ${run.status} exitCode=${run.exitCode}`);
}
if (run.buildNumber !== EXPECTED_BUILD) {
  throw new Error(`Actor used build ${run.buildNumber}; expected ${EXPECTED_BUILD}`);
}
if (!run.defaultDatasetId || !run.defaultKeyValueStoreId) {
  throw new Error('terminal run omitted its immutable storage IDs');
}

let summary;
let rows;
const settlementDeadline = Date.now() + 45_000;
while (true) {
  const refreshed = await request(`/v2/actor-runs/${exactRunId}`);
  run = refreshed.data;
  if (run?.id !== exactRunId) throw new Error('settlement read changed the exact run ID');
  summary = await request(
    `/v2/key-value-stores/${run.defaultKeyValueStoreId}/records/RUN-SUMMARY`,
  );
  rows = await request(
    `/v2/datasets/${run.defaultDatasetId}/items?clean=true&limit=${actorInput.maxItems}`,
  );
  const successfulRows = Array.isArray(rows)
    ? rows.filter((row) => row?.evaluationStatus !== 'ai_failed').length
    : -1;
  const runCharged = run.chargedEventCounts?.['job-fit-result'] ?? 0;
  if (
    Array.isArray(rows)
    && summary?.counts?.outputRows === rows.length
    && summary?.billing?.chargedCount === successfulRows
    && runCharged === successfulRows
  ) {
    break;
  }
  if (Date.now() >= settlementDeadline) {
    throw new Error('run, dataset, summary, and charge receipts did not settle within 45 seconds');
  }
  await sleep(3_000);
}
const acceptedSummarySchemas = new Set([
  'nomad-ai-job-fit-run-summary-v3',
  'nomad-ai-job-fit-run-summary-v4',
]);
if (!acceptedSummarySchemas.has(summary.schemaVersion)) {
  throw new Error('unexpected RUN-SUMMARY schema');
}
const isV4 = summary.schemaVersion === 'nomad-ai-job-fit-run-summary-v4';
if (!['complete', 'partial', 'empty'].includes(summary.status)) {
  throw new Error(`unusable RUN-SUMMARY status ${summary.status}`);
}
if (summary.algorithm?.name !== 'scoring-v3' || summary.algorithm?.interactionStateUsed !== false) {
  throw new Error('unexpected scoring algorithm contract');
}
if (!Number.isInteger(summary.counts?.outputRows) || summary.counts.outputRows < 0) {
  throw new Error('RUN-SUMMARY contains an invalid outputRows count');
}
if (isV4) {
  const countNames = [
    'evaluatedJobs', 'staticDropped', 'staticHeld', 'aiScored', 'aiFailed',
    'resultFilteredOut', 'outputRows',
  ];
  if (countNames.some((name) => !Number.isInteger(summary.counts[name]) || summary.counts[name] < 0)) {
    throw new Error('RUN-SUMMARY contains invalid v4 evaluation counts');
  }
  if (
    summary.counts.staticDropped + summary.counts.staticHeld
      + summary.counts.aiScored + summary.counts.aiFailed
    !== summary.counts.evaluatedJobs
  ) {
    throw new Error('v4 evaluation counts do not partition evaluatedJobs');
  }
  if (summary.counts.resultFilteredOut + summary.counts.outputRows !== summary.counts.evaluatedJobs) {
    throw new Error('v4 filtered and output counts do not reconcile');
  }
  if (
    !['shortlist', 'audit'].includes(summary.parameters?.resultMode)
    || !Number.isInteger(summary.parameters?.minDeliveryScore)
    || summary.parameters.minDeliveryScore < 0
    || summary.parameters.minDeliveryScore > 5
  ) {
    throw new Error('RUN-SUMMARY contains an invalid v4 result policy');
  }
  if (
    summary.parameters.resultMode === 'audit'
    && (summary.counts.resultFilteredOut !== 0 || summary.counts.outputRows !== summary.counts.evaluatedJobs)
  ) {
    throw new Error('v4 audit counts do not preserve the complete dataset');
  }
}
if (
  !summary.ai
  || summary.ai.providerCostLimitUsd !== 0.25
  || summary.ai.maxProviderAttempts !== 2
  || typeof summary.ai.providerCostLimited !== 'boolean'
  || typeof summary.ai.providerCostReservedUsd !== 'number'
  || summary.ai.providerCostReservedUsd < 0
  || summary.ai.providerCostReservedUsd > 0.25
) {
  throw new Error('unexpected owner provider cost guard');
}
const expectedBillingKeys = [
  'budgetAuthorizedCount', 'budgetLimited', 'chargedCount', 'eventName',
  'totalChargedUsd', 'unitPriceUsd',
].sort();
if (
  !summary.billing
  || JSON.stringify(Object.keys(summary.billing).sort()) !== JSON.stringify(expectedBillingKeys)
  || summary.billing.eventName !== 'job-fit-result'
  || summary.billing.unitPriceUsd !== 0.02
  || !Number.isInteger(summary.billing.chargedCount)
) {
  throw new Error('unexpected billing contract');
}
const expectedTotal = summary.billing.chargedCount * 0.02;
if (Math.abs(summary.billing.totalChargedUsd - expectedTotal) > 0.0000001) {
  throw new Error('total charged amount does not reconcile');
}
if (isV4) {
  const expectedCharged = summary.parameters.resultMode === 'shortlist'
    ? summary.counts.outputRows
    : summary.counts.outputRows - summary.counts.aiFailed;
  if (summary.billing.chargedCount !== expectedCharged) {
    throw new Error('v4 billing does not reconcile with result policy');
  }
}
if (summary.status === 'empty' && (!summary.cleanEmpty || summary.counts.outputRows !== 0)) {
  throw new Error('invalid clean-empty RUN-SUMMARY');
}

if (!Array.isArray(rows) || rows.length !== summary.counts.outputRows) {
  throw new Error('dataset count does not reconcile with RUN-SUMMARY');
}
const successful = rows.filter((row) => row.evaluationStatus !== 'ai_failed');
const expectedChargedRows = isV4 && summary.parameters.resultMode === 'shortlist'
  ? rows.length
  : successful.length;
if (expectedChargedRows !== summary.billing.chargedCount) {
  throw new Error('dataset rows do not reconcile with result-policy billing');
}
if ((run.chargedEventCounts?.['job-fit-result'] ?? 0) !== expectedChargedRows) {
  throw new Error('run charge receipt does not reconcile with successful evaluations');
}
const expectedKeys = [
  'blockingGates', 'candidateHash', 'candidateSnapshotHash', 'company',
  'deliveryScore', 'evaluatedAt', 'evaluationKey', 'evaluationStatus',
  'externalId', 'fitScore', 'gapSummary', 'gates', 'job', 'jobKey',
  'location', 'matchKey', 'postedAt', 'recommendation', 'schemaVersion',
  'scoreAdjustedForGates', 'scoring', 'source', 'staticDecision', 'title',
  'url', 'why',
].sort();
const sha256 = /^[a-f0-9]{64}$/;
const statuses = new Set([
  'scored', 'static_drop', 'static_hold', 'forward_cap_hold', 'ai_failed',
]);
const seen = new Set();
for (const row of rows) {
  if (
    !row || typeof row !== 'object' || Array.isArray(row)
    || JSON.stringify(Object.keys(row).sort()) !== JSON.stringify(expectedKeys)
    || row.schemaVersion !== 'nomad-ai-job-fit-v1'
    || row.scoring?.algorithm !== 'scoring-v3'
    || !row.scoring?.sourceProvenance
    || row.job?.schemaVersion !== 'nomad-agent-job-v1'
    || !statuses.has(row.evaluationStatus)
    || !sha256.test(row.matchKey)
    || !sha256.test(row.evaluationKey)
    || !sha256.test(row.candidateHash)
    || !sha256.test(row.candidateSnapshotHash)
  ) {
    throw new Error('dataset contains an unexpected result contract');
  }
  if (
    isV4
    && summary.parameters.resultMode === 'shortlist'
    && (
      row.evaluationStatus !== 'scored'
      || !Number.isInteger(row.deliveryScore)
      || row.deliveryScore < summary.parameters.minDeliveryScore
    )
  ) {
    throw new Error('dataset contains a row outside the v4 shortlist policy');
  }
  if (seen.has(row.matchKey)) throw new Error(`dataset repeats matchKey ${row.matchKey}`);
  seen.add(row.matchKey);
}

process.stdout.write(`${JSON.stringify({ runId: exactRunId, summary, rows }, null, 2)}\n`);
