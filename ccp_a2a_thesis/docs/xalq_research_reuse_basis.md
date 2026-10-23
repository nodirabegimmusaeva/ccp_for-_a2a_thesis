# Xalq Nazorati: research-reuse evidence record

Assessed 2026-10-05. Status: **public access documented; external research-reuse
basis not yet established**. This records available evidence, not a legal ruling
that research is forbidden or that written permission is always required.

## Published evidence

The [user agreement and privacy policy](https://xalqnazorati.uz/ru/policies/)
describes publication for public access in section 2.1.11. Section 8.2 grants a
nonexclusive content-use licence to the operator. Section 8.9 describes the
operator's research using de-identified information. These provisions do not
expressly grant outside researchers an open licence, authorize external LLM
processing, or establish a right to redistribute complaint texts.

The [legal-documents page](https://xalqnazorati.uz/ru/documents/) links a mayoral
decision PDF and presidential resolution PP-4642. This review inspected the index,
not the full linked instruments, and does not claim they contain no relevant rule.
The [about page](https://xalqnazorati.uz/ru/about/) was also inspected.

## Evidence retained

The git-ignored `real_llm_comparison/private_data/xalq_20261005/` directory contains
the saved pages (`about.html`, `policies.html`, `documents.html`), original map
snapshot and response headers. `review_v4/reuse_evidence.json` records page hashes,
URLs and the unresolved scope. The map response was retrieved without login or
an access-control workaround. That demonstrates accessibility, not a reuse licence.

## Intended research use to establish

- A small selected sample of real municipal complaint narratives for an academic
  study of multi-agent handoff quality, with source attribution.
- Original-language processing and documented translations/redactions.
- Submission of selected redacted text to an external LLM API for inference and
  display to human evaluators through Google Forms. No fine-tuning is proposed.
- Publication of aggregate results and, only if covered, limited redacted examples.
  Public release of the raw snapshot is not proposed.

The current development set retains incident street/building locations and removes
one apartment number. It is **not certified anonymous**. Researcher translation,
criteria and privacy review does not itself establish copyright permission or the
basis for processing/disclosing any personal information. The held-out reserve
still needs its own review.

## Next evidence needed

Obtain either an applicable published licence/permission covering the intended
uses, or a documented institutional determination of an applicable research-use
basis. An operator reply must establish its authority and scope; institutional
ethics approval alone should not be recorded as a content licence. Assess external
API processing, reviewer access and publication separately rather than assuming
one approval covers everything.

An unsent clarification request is prepared in
`docs/xalq_reuse_request_draft.md`. No message has been sent. Until the basis is
documented, dataset `reuse_status` remains `unconfirmed`; it must not be changed
to `permitted` merely to pass the loader. No live-model result is claimed.

## Wording usable in the current methodology draft

The study uses a locally archived snapshot of publicly accessible Xalq Nazorati
complaint records retrieved on 5 October 2026. Original narratives and recorded
locations are retained with traceable transformations. The researcher reviewed
the development translations and criteria. External research-reuse conditions
remain under review; the source is not described as openly licensed.
