# Test strategy

| ID | Layer | Probe | Expected result |
|---|---|---|---|
| CT-01 | Unit | Running and healthy | Container gate passes |
| CT-02 | Unit | Exited, starting or missing healthcheck | Container gate fails |
| CT-03 | Unit | Zero or multiple Compose label matches | Inspection stops with a diagnostic |
| CT-04 | Unit | JSON severity and plain ERROR/CRITICAL/FATAL | Sampled line positions identified |
| CT-05 | Unit | WARN, INFO mentioning errors, malformed and non-UTF-8 text | No false error classification or parser crash |
| CT-06 | Unit | 200, equivalent invalid health bodies, and oversize response | Only valid health body passes |
| CT-07 | Unit | 404 and network failure | Expected HTTP code can pass; transport error fails |
| CT-08 | Live | Healthy Compose app, HTTP and clean logs | JSON report passes; CLI exits 0 |
| CT-09 | Live | Unknown endpoint | 404 is observed without a redirect |
| CT-10 | Live | Controlled ERROR fixture with healthy HTTP and container | Only the log gate fails; CLI exits 1 |

A startup wait keeps normal application initialization out of the health regression. The monitor samples a bounded tail and supports structured severity and leading plaintext severity. It does not aggregate logs across replicas, infer outages from historical patterns, or alert continuously. Capture diagnostics before teardown. When testing a genuine failure, file a report using the [defect template](bug-report-template.md).
