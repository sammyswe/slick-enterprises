# Dedupe leads by domain

- Scope: business (example-ai-lead-scraper)
- Risk: low
- Proposed by: evaluator

When ingesting leads, normalize each company's URL to its **registrable domain**
(e.g. `mail.acme.ai` → `acme.ai`) and dedupe on that. This prevents counting the same
company multiple times across subdomains or tracking links.

## Steps
1. Parse the URL; extract the registrable domain (public-suffix aware).
2. Lowercase and strip `www.`.
3. Upsert by domain; keep the richest record.

## Verify
- Two leads with `acme.ai` and `www.acme.ai` collapse into one row.
