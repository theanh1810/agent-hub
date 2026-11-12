---
slug: demo-fix
date: "2026-10-27"
run:
  started_at: "2026-10-27T02:00:00Z"
  finished_at: "2026-10-27T02:02:00Z"
files_changed: ["src/app.py"]
data_impact:
  purpose: ["Fix a wrong count"]
  flow: "none: one line fixed, the flow is unchanged"
  ui: "none: no screen is touched"
  endpoints: "none: no endpoint changes"
  db_schema: "none: no table or column changes"
  data_reads: "none: no data is read"
  data_writes: "none: no data is written"
  business_rules: "none: no new rule"
  access: "none: no access change"
  events_jobs: "none: no event or job"
  config: "none: no config change"
  code_changes: [{file: "src/app.py", symbol: "count_retries", before: "counted one too few", after: "counted fully"}]
  risk_rollback: {risks: [], rollback: "restore the file from the backup"}
---

# demo-fix

A sample record for the test case.
