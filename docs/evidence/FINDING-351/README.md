# ADR-417 frozen evidence

`adr417-receipts.tar.gz` contains the complete exclusive scratch attempt plus its
execution log. No credentials, broker records or generated repository data were
written. Read the governing ADR-417 and FINDING-351 before inspecting it.

- Archive SHA256: `c9a8f080aee87eec270896217a7b765095af6bba62222086e2fe8cd611955d78`.
- `start.json` SHA256: `dbd1b4ccabff4e7f66738eb1ccf7144e008af4be2cc855e139ee358a4055cf46`
- `result.json` SHA256: `4e1539c7101059a10e24b0b3ba6ce45cd01c52028abb5a34e16eb7a0473f697e`
- Terminal state: UNEVALUABLE, AVB empty, request23/284; no economics calculated.

The start context pins historical score/roster Git blobs, publication-receipt
hash/time, current pool hash/count/max and exact executable/test/protocol digests.
Its eligible score rows preserve every flag and missing provenance. Publication
was confirmed in successful workflow32145869280's log:

```
2026-08-18T14:13:24.4427047Z    f213059..ca73b30  master -> master
```

The full source-run log hash is in start.json. This excerpt is availability
evidence, not filing authenticity. Each source's exact file hash is in result.json.
The archive includes 23 attempt/source/quality files and22 evidence envelopes;
source0022 is empty. Twenty-two passed56-session dates. No subset returns allowed.
All retained canonical bars are six-decimal normalized vendor adjusted prices.

Offline verification may validate archive hashes, canonical PriceBars, reports,
calendars, selection and costs on synthetic fixtures. Do not invoke the acquisition
script again, recreate its root or request missing series. Preserve this record.

The separate `executed-code.tar.gz` preserves the exact acquisition-time module,
driver and protocol (each hash checked against start.json before any change).
After the attempt, the existing no-literal-driver-dates test required extracting
the identical datetime values into shared library constants. Tests also received
type annotations/formatting. These release-only changes do not repeat acquisition
or alter frozen evidence. No current-file hash is substituted for executed bytes.

Executed-code archive SHA256: `27a3a9e09cdd36b9693f7180f2b71051cfe1eb83173567c9b213364ec23d5209`.
