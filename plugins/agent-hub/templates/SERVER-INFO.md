# SERVER-INFO — {project_name}

**Location**: `{workspace_root}/docs/devops/SERVER-INFO.md`, one per product — `docs/devops/` is a registered directory at the workspace root (`refs/artifact-layout.md § Where the workspace root is` and `refs/artifact-layout.md § Where writing is allowed`), not a sub-repo folder. NEVER commit secrets — use placeholders + reference to vault.

**Owner**: devops agent reads + maintains. brainstorm reads when debugging server-side issue.

---

## 1. Environments

| Env | Hostname | IP / DNS | Region | Purpose |
|---|---|---|---|---|
| development | dev.{project}.local | 127.0.0.1 | local | dev loop |
| staging | staging.{project}.com | — | {region} | pre-prod gate |
| production | {project}.com | — | {region} | live |

## 2. SSH / Access

| Env | User | Host | Port | Key ref | Bastion? | MFA? |
|---|---|---|---|---|---|---|
| staging | deploy | staging.{project}.com | 22 | `~/.ssh/{project}-staging` (vault: `op://devops/{project}/staging-ssh`) | no | no |
| production | deploy | {project}.com | 22 | vault: `op://devops/{project}/prod-ssh` | yes (bastion.{project}.com) | yes |

**Connect (example)**:
```bash
ssh -i ~/.ssh/{project}-staging deploy@staging.{project}.com
ssh -J deploy@bastion.{project}.com deploy@prod-internal.{project}.com
```

## 3. CI/CD

| Pipeline | Trigger | Tool | Config path |
|---|---|---|---|
| build-test | PR open/push | GitHub Actions / GitLab CI | `.github/workflows/ci.yml` |
| deploy-staging | merge to `develop` | {tool} | `.github/workflows/deploy-staging.yml` |
| deploy-prod | tag `v*` | {tool} | `.github/workflows/deploy-prod.yml` |

**Manual deploy commands** (idempotent, dry-run first):
```bash
# staging
{tool} deploy --env=staging --version={tag} --dry-run
{tool} deploy --env=staging --version={tag}

# production (requires approval gate)
{tool} deploy --env=production --version={tag} --dry-run
{tool} deploy --env=production --version={tag}
```

**Rollback**:
```bash
{tool} rollback --env={env} --to={previous_tag}
```

## 4. Infra runtime

| Component | Type | Endpoint / id | Notes |
|---|---|---|---|
| App | Docker / k8s / VM | `{cluster}/{namespace}/{deployment}` | replicas: N |
| DB | Postgres / MySQL / Mongo | `db.{project}.com:5432` | primary + N replicas |
| Cache | Redis | `cache.{project}.com:6379` | TLS yes/no |
| Queue | RabbitMQ / SQS | `{url}` | |
| Storage | S3 / GCS | bucket `{project}-{env}` | |
| CDN | Cloudflare / CloudFront | `cdn.{project}.com` | |

## 5. Logs

| Source | Path / system | Access cmd | Retention |
|---|---|---|---|
| App stdout | k8s pod logs | `kubectl logs -n {ns} deploy/{app} --tail=200 -f` | 7d |
| App stderr | same | same | 7d |
| Access log | nginx | `ssh deploy@host -- tail -f /var/log/nginx/access.log` | 14d |
| Aggregated | Loki / Datadog / Splunk | URL: `{log-ui-url}` | 30d |
| Audit | system journal | `journalctl -u {service} --since '1h ago'` | per system |

**Quick log-fetch shortcuts** (for brainstorm debug requests):
```bash
# tail app log
ssh deploy@{host} -- 'kubectl logs -n {ns} deploy/{app} --tail=500'

# grep error around timestamp
ssh deploy@{host} -- 'journalctl -u {service} --since "{iso8601}" --until "{iso8601}" | grep -i error'

# pull last crash dump
scp deploy@{host}:/var/crash/{app}-latest.dump /tmp/{app}-crash.dump
```

## 6. Monitoring / Alerts

| System | URL | What it watches |
|---|---|---|
| Metrics | Grafana / Datadog | latency, error rate, saturation |
| Uptime | UptimeRobot / Pingdom | health endpoint |
| Errors | Sentry / Rollbar | exceptions |
| APM | Datadog APM / NewRelic | request traces |

**Health endpoint**: `https://{host}/health` → `200 {"status":"ok"}`

## 7. Secrets

Reference the vault path only. NEVER store actual values here.

| Secret | Vault path | Rotation cadence |
|---|---|---|
| DB password | `op://prod/{project}/db-password` | 90d |
| JWT signing key | `op://prod/{project}/jwt-key` | 180d |
| Stripe API key | `op://prod/{project}/stripe-live` | on incident |
| OAuth client | `op://prod/{project}/oauth-client` | on incident |

Pull at deploy time via CI secret / `op read` / `aws secretsmanager get-secret-value`.

## 8. Mobile (if applicable)

| Platform | Store id | Signing | Distribution |
|---|---|---|---|
| iOS | com.{org}.{app} | match (`op://devops/{project}/match-password`) | TestFlight + App Store |
| Android | com.{org}.{app} | Google Play App Signing + upload key | Internal + Play |

EAS / Fastlane configs in `eas.json` / `fastlane/Fastfile`.

## 9. Common brainstorm → devops requests

When brainstorm needs server data, devops fetches via these patterns:

| Need | Command pattern |
|---|---|
| "Why is endpoint X 500ing?" | Pull last 500 lines of app log + filter by request_id from error trace |
| "Memory leak?" | `ssh deploy@host -- 'kubectl top pod -n {ns}'` + `kubectl exec ... -- ps aux \| sort -rk6 \| head` |
| "DB slow?" | `ssh db-host -- 'psql -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY 2 DESC LIMIT 10"'` |
| "Cert expiring?" | `echo \| openssl s_client -connect {host}:443 2>/dev/null \| openssl x509 -noout -dates` |
| "Disk full?" | `ssh deploy@host -- 'df -h'` |
| "Recent deploys?" | `{tool} deployments list --env={env} --limit=10` |

devops returns: command run + first 50 lines of relevant output + path to full log artifact. Never paraphrase. Never dump >200 lines into chat — save to `{plan_dir}/logs/{task_id}-{YYYYMMDD-HHMMSS}.log` and cite path.

## 10. Rollback decision tree

```
incident detected
├── error rate >5% AND/OR p95 latency 2 times baseline
│   └── revert last deploy: `{tool} rollback --env=prod --to={previous}`
├── data corruption suspected
│   └── stop writes (feature flag off) → restore DB snapshot → rollback app
├── security incident (secret leak / unauthorized access)
│   └── rotate secret → invalidate sessions → patch + redeploy → forensics
└── partial degradation (1 region / 1 endpoint)
    └── drain traffic from region → investigate → fix forward or rollback that region
```
