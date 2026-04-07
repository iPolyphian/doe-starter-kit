# Directive: Data Safety

## Goal
Prevent accidental or AI-caused destruction, exposure, or corruption of data across all environments. This directive protects regulated political data that cannot legally be lost once collected.

## When to Use
- Writing or modifying SQL, database migrations, or schema changes
- Configuring Supabase, Neon, or any database service
- Setting up environment variables or credential files
- Creating or modifying `.env` files
- Writing execution scripts that connect to any database
- Configuring storage buckets (Supabase Storage, Vercel Blob)
- Setting up CI/CD pipelines or deployment workflows
- Any Bash command containing `psql`, `supabase`, `neon`, or database connection strings
- Reviewing AI-generated code that touches data infrastructure

## Inputs
- `legal-framework.md` -- legal obligations for data retention
- `directives/data-compliance.md` -- GDPR/DPA 2018 requirements
- `data-governance.md` -- dataset register and retention policy
- Environment configuration (`.env*`, Vercel env vars)

## The Golden Rule

**Production data is irreplaceable regulated data. Every rule below exists to protect it.**

Once the system collects personal data (membership, canvass responses, donations), that data is subject to UK GDPR retention requirements and PPERA record-keeping obligations. Losing it is not just an inconvenience -- it is a reportable data breach (72-hour ICO notification window) and potential regulatory violation. Even before personal data enters the system, treating all data as irreplaceable builds the right habits.

### Data Controller Liability

**If you are building this solo, YOU are the data controller.** Under UK GDPR Article 4(7), the data controller is the person who determines the purposes and means of processing personal data. If no party has formally adopted the system and taken over controllership, the developer is the controller by default. This means:
- ALL GDPR obligations (Articles 5-49) apply to you personally, not to a company
- ICO enforcement actions can be taken against you as an individual
- Data subjects can sue you directly (Article 82) for material or non-material damage
- You must be able to demonstrate compliance (accountability principle, Article 5(2))

This remains true until a formal, documented handover of data controllership to a party or organisation. The handover must specify: what data is transferred, what obligations transfer with it, what happens to data if the relationship ends, and who is responsible during the transition period. Document this in `legal-framework.md` when it occurs.

### Electoral Register Data — Criminal Liability

**Misuse of the full electoral register is a criminal offence carrying imprisonment.** Under the Representation of the People (England and Wales) Regulations 2001 (reg. 115), it is an offence to:
- Use full register data for any purpose other than those specified in law
- Disclose full register data to an unauthorised person
- Fail to comply with security requirements for register data

Political parties may use the full register for electoral purposes, but merging it with commercial data, sharing it with third parties, or using it for non-electoral purposes is criminal. If the system integrates electoral register data:
- It must be stored separately from other data, with its own access controls
- Access must be logged and auditable
- It must never be included in seed data, test data, backups shared outside the secure environment, or any non-production system
- A leak of electoral register data is both a GDPR breach (ICO notification) AND a criminal matter (police)

This is not a fine. This is a court appearance.

---

## 0. The First Personal Data Gate

**No personal data enters any environment until ALL of the following are completed and documented.**

This is the most important section in this directive. The transition from "no personal data" to "personal data in the system" is irreversible -- once obligations attach, they never go away. There is no "undo" for having processed personal data without the proper foundations.

### Hard Gate Checklist
Every item must have a dated artifact proving completion:

- [ ] **DPIA completed and approved** — Article 35 assessment covering: what data, why, legal basis for each category, risks, mitigations. Signed and dated by the data controller. Artifact: `docs/compliance/dpia-v1.pdf` (or equivalent).
- [ ] **Legal basis documented for each data category** — Legitimate interest balancing test OR consent mechanism OR legal obligation basis, for each type of personal data. Artifact: updated `legal-framework.md`.
- [ ] **Privacy notice written and accessible** — Plain English description of what data is collected, why, how long it's kept, who it's shared with, and how to exercise rights. Must be accurate from day one. Artifact: privacy notice page in the application.
- [ ] **SAR procedure tested** — Subject Access Request export function works: query all tables for a test person, compile export, verify it contains everything. Must complete in seconds (legal deadline is 30 days, but a manual process will fail). Artifact: test run output.
- [ ] **Erasure procedure tested** — Delete a test person and verify: no records remain in any table (or all marked deleted_at), audit log shows deletion, person cannot be reconstructed. Artifact: test run output.
- [ ] **Consent withdrawal mechanism works** (if using consent as legal basis) — Person can withdraw, processing stops immediately, data is deleted unless another legal basis applies. Artifact: test run output.
- [ ] **Backup and recovery tested** — Backup created, restored to scratch database, data integrity verified. Artifact: restore test log with timestamp.
- [ ] **Environment isolation verified** — Production credentials confirmed absent from all non-production environments. Non-production databases confirmed to contain only seed data. Artifact: env var audit output.
- [ ] **Supabase Pro tier active** (or equivalent with automated backups) — Free tier has no backups. Storing personal data without automated backups is negligent. Artifact: billing plan confirmation.
- [ ] **ICO registration** (if required) — Most organisations processing personal data must register with the ICO (Data Protection (Charges and Information) Regulations 2018). Fee is £40-£2,900/year depending on size. Check exemptions. Artifact: ICO registration number.
- [ ] **Data Processing Agreements** — For every third-party service receiving personal data (Supabase, Sentry, email provider, etc.). Artifact: signed DPAs or provider DPA URLs.

**None of these are optional. None can be done "later." All must be complete before the first INSERT of personal data.**

### The Demo Temptation

Under pressure -- especially before a party meeting, investor pitch, or demo -- there will be a temptation to load real member data to show the system working with "real" data. **This is the single most likely way the system breaks from "safe" to "uncontrolled."**

**What happens if you load real data for a demo without the gate checklist:**
- You become the data controller for that data immediately
- Every GDPR obligation applies from that moment
- If anything goes wrong (laptop stolen, database exposed, demo environment shared), it's a reportable breach
- "I was just testing" is not a legal defence

**Safe alternative:** The seed data script generates realistic synthetic data that looks convincing in a demo. Names, addresses, constituencies, donation amounts, canvass responses -- all fake, all safe. Build the seed script to produce demo-quality output. Invest time in the seed script, not in risking real data.

### IP Addresses and Logging

**IP addresses are personal data under UK GDPR** (CJEU Breyer v Germany, C-582/14). If any part of the system logs IP addresses -- including Vercel function logs, application error logs, analytics, or access logs -- you may already be processing personal data even without user accounts.

**Check immediately:**
- Does the application log request headers or IP addresses? Remove or anonymise.
- Is Vercel Analytics enabled? Check what it collects (Vercel's first-party analytics is privacy-friendly, but verify).
- Do error handlers (try/catch blocks) log request objects that include IP addresses?
- Do any third-party scripts or libraries send telemetry that includes user IP?

If any of these are true, you need at minimum a privacy notice and a legal basis for processing (legitimate interest for security logging is usually sufficient, but it must be documented).

---

## 1. Environment Isolation

### The Rule
Production credentials must ONLY exist in production environment variables. No other environment -- preview, development, local, CI -- may connect to the production database. This is a physical barrier, not a policy one.

### How to Implement

| Environment | Database | Credentials |
|-------------|----------|-------------|
| **Production** | Production Supabase/Neon instance | Production env vars only (Vercel production scope) |
| **Preview** (PR deploys) | Neon branch OR seed-only database | Preview env vars (auto-provisioned by Vercel) |
| **Local dev** | Local seed database or Neon branch | `.env.local` with non-production creds only |
| **CI/CD** | Seed-only database or no database | GitHub Actions secrets (non-production only) |

### Non-Negotiable Requirements
- **Never copy `.env.local` between machines** -- regenerate credentials per environment.
- **Never use production connection strings in any `.env.local` file** -- even "just for testing." There is no "just for testing" with regulated data.
- **Vercel preview deployments MUST use a separate database** -- Neon branching (recommended) creates an isolated copy automatically. If branching is unavailable, use a seed-only database.
- **AI agents (Claude Code, GitHub Actions, Vercel Agent) physically cannot connect to production.** Their environment variables point to non-production databases only. No exceptions. No "temporary" production access.

---

## 2. Destructive Operation Prevention

**It is not just SQL.** Destructive operations come from raw SQL, ORM methods, client libraries, CLI tools, storage APIs, and build-time code execution. The Bash hook (`.claude/hooks/block_dangerous_commands.py`) catches literal SQL strings in shell commands -- it is a tripwire, not a wall. Defence-in-depth is required: hooks catch the obvious, code review catches the subtle, environment isolation prevents the catastrophic.

### Blocked SQL Operations
The following SQL operations are blocked by the Bash hook and must also be blocked in CI:

| Operation | Why Blocked | Safe Alternative |
|-----------|-------------|------------------|
| `DROP TABLE` | Irrecoverable data loss | Rename table, keep for retention period, then drop with explicit approval |
| `DROP DATABASE` | Irrecoverable total loss | Never. There is no safe alternative to dropping a production database. |
| `TRUNCATE` | Instant irrecoverable loss | `DELETE FROM ... WHERE ...` with conditions, or soft-delete |
| `DELETE FROM table` (no WHERE) | Unconditional wipe | Always require a WHERE clause. Soft-delete preferred. |
| `ALTER TABLE ... DROP COLUMN` | Silent data loss | Create a new table without the column, migrate data, rename |
| `UPDATE ... SET ...` (no WHERE) | Mass corruption | Always require a WHERE clause with specific conditions |

### Blocked ORM and Client Library Operations
These are equally destructive but invisible to the Bash hook. Catch them in code review and CI linting:

| Operation | Language/Library | Safe Alternative |
|-----------|-----------------|------------------|
| `prisma.user.deleteMany()` (no where) | Prisma | Always pass a `where` clause. Soft-delete preferred. |
| `db.delete(users)` (no where) | Drizzle | Always chain `.where()`. |
| `supabase.from('users').delete()` (no filter) | Supabase JS | Always chain `.eq()`, `.in()`, or `.match()`. |
| `supabase.storage.emptyBucket('name')` | Supabase JS | Never. Delete individual files with documented justification. |
| `supabase.auth.admin.deleteUser(id)` | Supabase JS | Soft-delete the user record. Only hard-delete auth users with legal basis. |
| `Model.objects.all().delete()` | Django ORM | Always filter first. |

### Blocked CLI Operations
These CLI commands are as dangerous as raw SQL and must be treated with the same caution:

| Command | What It Does | Safe Alternative |
|---------|-------------|------------------|
| `supabase db reset` | Wipes entire database, replays migrations from scratch | Never run against production. Use only on local/branch databases. |
| `supabase db push --linked` | Pushes schema diff to the linked database | Verify which database is linked first (`supabase status`). Never link to production from a dev machine. |
| `supabase db dump` | Dumps schema/data -- output may contain secrets | Review output before storing. Never commit dumps to git. |
| `vercel env pull` then edit production vars | Could expose or corrupt production env vars | Use Vercel dashboard for production env changes. CLI for preview/dev only. |

### Build-Time Execution Risk
Next.js evaluates module-level code during `next build`. If a database client is eagerly initialised at the top of a module, it connects (and potentially runs operations) at build time -- not at request time.

**Dangerous pattern:**
```ts
// This runs during `next build` -- could execute against whatever DATABASE_URL is set
const db = new PrismaClient()
await db.$executeRaw`SOME DANGEROUS THING`  // runs at build time!
```

**Safe pattern:**
```ts
// Lazy initialisation -- only connects when first called at request time
let _db: PrismaClient | null = null
function getDb() {
  if (!_db) _db = new PrismaClient()
  return _db
}
```

Always use lazy initialisation for database clients. Never run migrations, seeds, or destructive operations at module scope.

### Migration Safety Protocol
Every schema migration must follow this sequence:
1. **Backup first.** Before running any migration, create a database backup. No exceptions.
2. **Write a rollback script.** Every migration gets a paired rollback. If the migration adds a column, the rollback removes it. If the migration transforms data, the rollback reverses it.
3. **Test on non-production first.** Run the migration against the preview/branch database. Verify the result. Only then run against production.
4. **One migration at a time.** Never batch multiple migrations. If one fails, you need to know which one.
5. **Keep the old schema compatible.** For at least one deployment cycle, both old and new code must work. This means: add columns before requiring them, stop writing to columns before removing them.

### Soft-Delete Policy
All regulated records (membership, canvass, donations, communications) use soft deletes:
- Add `deleted_at TIMESTAMP DEFAULT NULL` to every table containing personal or regulated data.
- "Deleted" records have `deleted_at` set. Application queries filter `WHERE deleted_at IS NULL`.
- Hard deletes happen only: (a) after the documented retention period expires, (b) in response to a verified Right to Erasure request (Article 17), or (c) with explicit written approval from the data controller.
- Hard deletes are logged in the audit trail with the legal basis for deletion.

---

## 3. AI Agent Constraints

### Common AI Mistakes (and how we prevent them)

**This section exists because AI coding agents consistently make these mistakes.** Every one of these has been documented in real projects. Claude, Cursor, Copilot, v0 -- they all do these.

| AI Mistake | Why It Happens | Prevention |
|-----------|----------------|------------|
| **Using `service_role` key in client code** | AI sees both keys in `.env`, picks the one that "works" (bypasses RLS) | Hook: block any file in `src/`, `app/`, or `components/` from containing `service_role`. Only server-side execution scripts may use it. |
| **Creating public Supabase storage buckets** | AI defaults to `public: true` because it's simpler | Hook: block `createBucket` calls with `public: true`. All buckets default to private. Public access requires explicit approval with documented justification. |
| **Hardcoding API keys in source files** | AI writes the key inline instead of reading from env | Pre-commit hook: scan for patterns matching API keys, JWTs, connection strings. Existing hook covers some patterns; expand for Supabase, Neon, Stripe. |
| **Committing `.env` files** | AI creates `.env` and stages it | `.gitignore` must include `.env*` except `.env.example`. Pre-commit hook blocks any staged file matching `.env*` (excluding `.env.example`). |
| **Running unguarded DELETE/UPDATE** | AI generates SQL without WHERE clause | Hook: block SQL containing `DELETE FROM` or `UPDATE ... SET` without a WHERE clause. |
| **Disabling RLS "temporarily"** | AI adds `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` to fix a permissions error | Hook: block any command containing `DISABLE ROW LEVEL SECURITY`. RLS is never disabled, even temporarily. Fix the policy, not the enforcement. |
| **Logging sensitive data** | AI adds `console.log(user)` or `console.log(request.body)` for debugging | Code review check: no logging of request bodies, user objects, or any variable likely to contain personal data. Log IDs and operation names, not data values. |
| **Exposing secrets in error messages** | AI returns `catch (e) { return Response.json({ error: e.message })` which may include connection strings | Never return raw error objects to clients. Map to safe error messages. Log the full error server-side only. |
| **Using `anon` key for server-side operations** | AI uses the simpler key, missing RLS context | Server-side code that needs elevated access uses `service_role` in execution scripts only. Server-side code that respects user context uses the user's JWT with `anon` key. Document which is appropriate for each use case. |
| **Adding `NEXT_PUBLIC_` to server secrets** | AI adds the prefix to make a key "work" in a client component. This embeds the secret in the JavaScript bundle sent to every browser. | HARD RULE: `NEXT_PUBLIC_` prefix is ONLY for values safe to expose publicly (publishable keys, URLs). Never for secret keys, service_role keys, connection strings, or tokens. Scan for: `NEXT_PUBLIC_.*SECRET`, `NEXT_PUBLIC_.*SERVICE_ROLE`, `NEXT_PUBLIC_.*TOKEN` (except explicitly public tokens). |
| **Creating public Vercel Blob uploads** | AI defaults to `access: 'public'` for convenience | Same as Supabase buckets: default to `access: 'private'`. Public access only with documented justification. Sensitive files (legal docs, member data exports) must always be private. |
| **Mass ORM deletions without filters** | AI writes `deleteMany()` or `.delete()` without where clauses | Block unfiltered deletes in code review. See "Blocked ORM and Client Library Operations" above. |
| **Running `supabase db reset` on linked database** | AI runs it to "fix" a migration error, not realising it wipes everything | Add `supabase db reset` to the Bash hook block list. See "Blocked CLI Operations" above. |
| **Eager database connection at module scope** | AI writes `const db = connect(url)` at the top of a file, which executes at build time | Use lazy initialisation. See "Build-Time Execution Risk" above. |

### Read-Only Database User for Automated Tooling
When CI, Claude Code, or any automated tool needs to query the database:
- Create a dedicated database role with `SELECT` only -- no `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`.
- AI agents connect using this read-only role.
- Write operations go through application code with proper validation, not raw SQL from agents.

### Parameterised Queries Only
- No string concatenation for SQL: `f"SELECT * FROM users WHERE id = '{user_id}'"` is forbidden.
- Use parameterised queries: `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))` or ORM methods.
- This prevents SQL injection AND makes destructive typos less likely.

---

## 4. Secret Management

### Rules
- **Secrets live in `.env` files (local) or Vercel environment variables (deployed).** Nowhere else. Not in code, not in comments, not in commit messages, not in error logs.
- **`.env.example` contains key names with empty values.** It documents what secrets are needed without containing secrets.
- **`.env*.local` is in `.gitignore`.** Always. No exceptions. Verify after every `.gitignore` change.
- **Rotate immediately if exposed.** If a secret appears in a commit, log, error message, or any public surface: revoke it, generate a new one, update all environments. Do not just delete the commit -- the secret is compromised the moment it's pushed, even if force-pushed away.
- **Environment variable scoping on Vercel.** Use Vercel's environment scoping (Production, Preview, Development) to ensure production secrets are only available in production. Preview deployments get their own non-production secrets.

### Secret Patterns to Scan For
Pre-commit hooks and CI should scan for these patterns:
- Supabase keys: `eyJ` (JWT prefix), `sbp_` (Supabase project ref)
- Neon connection strings: `postgresql://...@...neon.tech`
- Stripe keys: `sk_live_`, `sk_test_`, `pk_live_`, `pk_test_`
- Generic patterns: `-----BEGIN (RSA |EC )?PRIVATE KEY-----`, URLs with embedded credentials (`://user:pass@`)
- Clerk keys: `sk_live_`, `pk_live_`
- Any string matching `SUPABASE_SERVICE_ROLE_KEY` outside `.env*` files

## Secret Rotation
All secrets (database passwords, API keys, auth provider secrets) must have a documented rotation procedure. Rotation triggers: scheduled (every 90 days for high-sensitivity keys), reactive (after any suspected compromise or team member departure). Procedure: generate new secret → update in Vercel env vars → verify app works → revoke old secret. Never rotate by deleting first. Test rotation in preview environment before production.

---

## 5. Seed Data Strategy

### The Rule
Non-production environments use synthetic seed data. Real data never leaves production.

### Implementation
- Create a seed database script (e.g. seed_database.py) that generates realistic but fictional data.
- Seed data must cover edge cases: long names, Unicode characters, boundary values, empty fields.
- Seed data quantity should be sufficient for performance testing (1000+ records for key tables).
- Never `pg_dump` production and restore to development. Not even "anonymised" -- anonymisation is hard to verify and easy to reverse.
- The seed script is idempotent: running it twice produces the same result (use `ON CONFLICT DO NOTHING` or truncate seed tables before inserting).

---

## 6. Outbound Data Flows (Third-Party Processors)

Any third-party service that receives personal data is a "data processor" under UK GDPR Article 28. This includes services you might not think of as data processors:

| Service | What Data It Receives | Risk | Mitigation |
|---------|----------------------|------|------------|
| **Sentry** (error tracking) | Error context, stack traces, request data -- may include user IDs, form data, personal data in error messages | PII in error reports | Configure Sentry's `beforeSend` to strip personal data. Never include request bodies in error context. |
| **PostHog / Vercel Analytics** | User events, page views, potentially custom properties | Behavioural tracking | Minimise custom event properties. No personal data in event names or properties. |
| **Email services** (Resend, SendGrid) | Recipient emails, message content | Direct personal data | Data Processing Agreement required. Retention policy on sent messages. |
| **AI providers** (via AI Gateway) | Any data sent in prompts | Personal data in prompts | Never send raw personal data in AI prompts. Anonymise or use IDs. Check provider data retention policies. |
| **Log drains** (Datadog, Grafana) | Application logs -- may contain personal data if logging is sloppy | PII in logs | Log IDs and operation names, never data values. See "Logging sensitive data" in AI Mistakes table. |

**For each third-party service:**
1. Confirm they have adequate UK GDPR compliance (adequacy decision or standard contractual clauses).
2. Execute a Data Processing Agreement (DPA) before sending personal data.
3. Document the service in `data-governance.md` as a sub-processor.
4. Configure the service to minimise data retention.
5. Ensure data stays in UK/EEA/adequate jurisdictions (check Supabase region, Sentry region, etc.).

---

## 7. Backup and Recovery

### Before Any Schema Change
1. Create a backup: `pg_dump` or Supabase dashboard backup.
2. Document the backup location and timestamp.
3. **Test the backup**: restore to a scratch database and verify data integrity. An untested backup is not a backup.
4. Only then proceed with the migration.

### Regular Backups
- Supabase Pro tier includes daily automated backups. Free tier does not -- this is a blocker for production use on free tier.
- Supplement with weekly manual backups stored in a separate location (not the same Supabase project).
- Backup retention: match the longest data retention period in `data-governance.md`.

### Recovery Procedure
If data loss or exposure occurs:
1. **Stop the bleeding.** Immediately restrict database access to prevent further damage. Revoke compromised credentials. Do NOT delete evidence.
2. **Assess scope.** What data was affected? How many individuals? What categories (names, emails, political opinions, financial)? When did the breach occur vs when was it discovered?
3. **Restore from backup** (if data loss). Use the most recent backup before the incident.
4. **Gap analysis.** Identify data created between the backup and the incident. This may be unrecoverable.
5. **Incident report.** Document what happened, root cause, scope, and remediation. Keep this document -- it's evidence of compliance.
6. **ICO notification** (if personal data affected). The 72-hour clock starts from DISCOVERY, not occurrence.

### Data Breach Notification Chain

**This must be followed exactly. "I didn't know the procedure" is not a defence.**

**Hour 0 -- Discovery:**
Someone (you, Sentry, a user, Claude) discovers personal data may have been compromised. The 72-hour window starts NOW.

**Hour 0-1 -- Triage:**
- What happened? (data loss, unauthorised access, exposure, corruption)
- What data? (names, emails, political opinions, financial, electoral register)
- How many people affected? (estimate is acceptable at this stage)
- Is the breach ongoing? If yes, stop it before anything else.
- Is electoral register data involved? If yes, this is also a criminal matter -- take legal advice immediately.

**Hour 1-4 -- Containment:**
- Revoke compromised credentials
- Restrict access to affected systems
- Preserve evidence (logs, access records, database state)
- Do NOT destroy or alter evidence

**Hour 4-24 -- Assessment:**
- Determine the exact scope (which records, which individuals)
- Assess risk to individuals (could this cause them harm?)
- Decide if individuals need to be notified directly (required if "high risk to rights and freedoms" -- Article 34)

**Hour 24-72 -- ICO Notification (if required):**
- File notification at https://ico.org.uk/make-a-complaint/data-protection-complaints/data-protection-complaints/
- Notification must contain (Article 33(3)):
  - Nature of the breach
  - Categories and approximate number of individuals affected
  - Categories and approximate number of records affected
  - Name and contact details of the data controller (you, until a party takes over)
  - Likely consequences of the breach
  - Measures taken or proposed to address the breach
- If you don't have all details, file what you have and supplement later. Missing the 72-hour window is worse than filing incomplete information.

**Post-incident:**
- Notify affected individuals if required (high risk breaches)
- Document everything in a breach register (Article 33(5) -- you must keep records of ALL breaches, even ones not reported to ICO)
- Root cause analysis and prevention measures
- Update this directive if the breach revealed a gap

### GDPR Right to Erasure vs PPERA Retention Conflict

There is a genuine legal tension: GDPR Article 17 gives individuals the right to have their data deleted. But PPERA requires parties to retain donation records (s.71) and expenditure records (s.81) for specific periods.

**Resolution:** GDPR Article 17(3)(b) provides an exemption from the right to erasure where processing is necessary "for compliance with a legal obligation." PPERA record-keeping IS a legal obligation. Therefore:
- **Donation records:** Retain for the period required by PPERA (currently 6 years). The individual cannot demand deletion during this period. Document the legal basis: "Retention required under PPERA s.71 for Electoral Commission reporting."
- **Expenditure records:** Same -- PPERA requires retention for EC reporting periods.
- **All other personal data:** Right to erasure applies normally. If someone asks to be deleted, delete everything except what PPERA legally requires you to keep.
- **After the PPERA retention period expires:** The legal basis for retention disappears. Delete the records.

---

## 8. Stacked PR Prevention

### The Problem
Files like `todo.md`, `STATE.md`, and `ROADMAP.md` are touched by every feature. Stacking PRs (building a new feature before merging the previous one) creates conflict chains that require manual resolution and risk data loss during rebase.

### The Rule
**Merge each PR before starting the next feature.** Do not stack PRs. If `/crack-on` detects open PRs for completed features, it should warn before creating a new branch.

This is not just a workflow preference -- in a regulated data context, complex merge conflicts on state-tracking files increase the risk of silently losing compliance-relevant metadata (audit decisions, legal basis documentation, DPIA references).

---

## Edge Cases

- **Neon branching is not available on all plans.** If unavailable, use a completely separate Neon project for non-production. Document the project IDs in `.env.example`.
- **Supabase free tier has no backups.** Production MUST use Pro tier ($25/mo). This is a hard blocker for personal data. If cost is a concern, do not store personal data until Pro is budgeted.
- **Supabase Dashboard access bypasses RLS.** Dashboard credentials are superuser. Treat them as root access. Enable MFA. Do not share dashboard access with AI agents or CI.
- **Vercel preview deployments share the same Vercel project.** Environment variable scoping (Production vs Preview) is the isolation mechanism. Verify scoping after any environment variable change.
- **`pg_dump` output may contain secrets** if functions reference connection strings. Review dump files before committing them anywhere.
- **Electoral register data** -- see "Electoral Register Data -- Criminal Liability" section above. Criminal offence, not just a fine. Any seed data that resembles real electoral data is a risk.

## Verification

### Technical Controls
- [ ] Production credentials are NOT in any `.env.local` file
- [ ] `.env*.local` is in `.gitignore`
- [ ] Pre-commit hook blocks DROP TABLE, DROP DATABASE, TRUNCATE, DISABLE ROW LEVEL SECURITY, `supabase db reset`
- [ ] Pre-commit hook blocks staged `.env*` files (except `.env.example`)
- [ ] Storage buckets default to private (Supabase Storage AND Vercel Blob)
- [ ] `service_role` key is not referenced in any client-side code
- [ ] No `NEXT_PUBLIC_` prefix on any secret, service_role key, token, or connection string
- [ ] Seed data script exists and generates synthetic data only
- [ ] Every migration has a paired rollback script
- [ ] AI agents use read-only database credentials
- [ ] No raw SQL string concatenation in application code
- [ ] No unfiltered ORM deletions (`deleteMany()`, `.delete()` without where/filter)
- [ ] Database clients use lazy initialisation (not module-scope eager connection)
- [ ] Third-party services receiving personal data have DPAs and are documented in data-governance.md
- [ ] Backups have been test-restored at least once
- [ ] No IP addresses logged in application code
- [ ] No real personal data in any non-production environment

### Legal/Compliance Controls (before first personal data)
- [ ] DPIA completed, signed, and dated
- [ ] Legal basis documented for each data category
- [ ] Privacy notice written and accessible
- [ ] SAR export procedure tested
- [ ] Erasure procedure tested
- [ ] Breach notification chain documented and rehearsed
- [ ] ICO registration completed (if required)
- [ ] Data Processing Agreements signed for all third-party processors
- [ ] Data controller identity documented in legal-framework.md
- [ ] PPERA retention periods documented for regulated records

## Cross-References
- `directives/data-compliance.md` -- GDPR/DPA 2018 legal requirements (complementary -- this directive covers technical enforcement, that one covers legal compliance)
- `legal-framework.md` -- Legal obligations including ICO breach notification
- `data-governance.md` -- Dataset register, retention periods, provenance
- `.claude/hooks/block_dangerous_commands.py` -- Technical enforcement of destructive operation blocking
