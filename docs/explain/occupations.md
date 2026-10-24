# Any occupation: evidence preview

The page helps people outside finance look up their occupation's available evidence. It does not
promise full learning plans outside the verified finance pack. Suggestions always need the person's
confirmation. Examples are search inputs, not invented occupation records.

`GET /api/occupations/status` reports observed catalogue/vector counts, O*NET release and update
time. An empty catalogue directs the person to Live intelligence; it does not silently claim a
model failure. `detect.py` embeds a query, compares stored occupation vectors and reranks candidates
on RunPod. Its cache now checks database identity and every vector text hash, and discards codes
not in the catalogue. Invalid/mismatched model responses use a labelled keyword fallback.

The fallback searches English occupation text. The example “Kerani akaun” has a team-reviewed
query alias to “accounts clerk”; this is not full Malay keyword support. The GPU embedding model
provides broader multilingual semantic search when configured and available. Missing evidence
in the preview stays missing; the page never invents wages, job-ad figures or company names.

Local diagnosis: 1,016 catalogue rows and 1,016 vectors were present, not the older 718 figure.
English lookup worked with GPU calls disabled; the Malay example previously returned no fallback
hits. The page now explains index readiness, model/fallback engines and empty results separately.
Cloud catalogue state and successful paid inference still require the deployed app's run log.

Tests use fake catalogue/model responses, including the bilingual example. Browser QA uses the
real local API with a copied database, no paid inference. Source: O*NET database (CC BY 4.0), source
and date displayed; a query match is not verified proficiency, future demand or a hiring prediction.
