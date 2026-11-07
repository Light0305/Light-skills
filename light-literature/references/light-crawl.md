# Optional light-crawl handoff

Locate the actual installed `light-crawl` skill or source checkout and read its
`SKILL.md` before a live acquisition task. It owns crawling, routing and browser
sessions; light-literature owns paper records, source reading and synthesis.

Use it when APIs miss a public page, a lawful repository, supplementary files,
or a code/data page and repeatable extraction is useful. Prefer a simple HTTP
request for a single straightforward page. Do not run a browser just to search
metadata already available through an existing adapter.

## Invocation

Use its verified launcher path (`<crawl-root>` is the actual skill location):

```text
python "<crawl-root>/run_light_crawl.py" doctor
```

For a scoped public target already authorized by the user, create a case under
the project's `Acquisition/ACQ-...` workspace (replace the URL with the actual
target). A pre-existing acquisition layout can be reused. Link the case from the
search run or article instead of creating a competing nested acquisition tree:

```text
python "<crawl-root>/run_light_crawl.py" new-case case --case-root "<ACQ>" --target "<actual-url>" --authorized
python "<crawl-root>/run_light_crawl.py" probe "<ACQ>/case"
python "<crawl-root>/run_light_crawl.py" route "<ACQ>/case"
```

Use `--authorized` only for the task's real authorized scope. Inspect generated
`scope.md`, `target.json`, `probe.json` and `route.json`; fill the actual volume,
limits and stop conditions before collecting. A case being created is not proof
that materials were retrieved. Follow the selected lane in light-crawl's skill,
then verify the acquired sample and generate its report. Browser/login work is
conditional on the actual route; do not make it a universal step.

For a different installation use its installed `light-crawl` command or verified
checkout entrypoint. There is no Python import dependency, automatic crawler
launch, or requirement to install a second model backend.

## Return evidence to the reading workflow

Keep the crawler case's `evidence.jsonl`, hashed `artifacts/`, verified fixtures
and `reports/report.md`. In the paper's `meta.json`, optional `acquisition` entries
can record `source_url`, `retrieved_at`, `case_dir`, `artifact_path`, `sha256`,
`access_route` and `status`. Preserve actual filenames and hashes from the case.

- PDF: verify the bytes/content and title/DOI identity, then use `literature add`.
- Publisher HTML/text: preserve the source artifact, use structure-grounded
  block/section locators in `source_map.json`, and let the host model read it.
  The current `literature add` command accepts PDFs, not HTML.
- Supplement/code/data: keep in a clearly named subfolder or reference its saved
  artifact. Identify its role and link it from the note; do not merge it into the
  main article without recording provenance.
- Failure/challenge: record the actual blocked/unavailable state. Do not relabel
  a landing page as full text or guess unseen content.

Imported metadata must use the normal paper ID and provenance contract before
being cited in a synthesis. The crawler's arbitrary item ID is not a `[[p_id]]`.
