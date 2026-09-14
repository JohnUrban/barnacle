# Plan: external 24/7 nowcast trigger — READY FOR OWNER CREDENTIALS

Status: written 2026-08-07 (event #7 tripped the revisit trigger).
Half-A (launchd on the user's Mac, `bin/install_local_scheduler.sh`)
was BELIEVED installed 2026-08-07 but never fired once: the clone
was created 42 s before `bin/` existed on origin and never pulled
(2,077 consecutive failures; found by the 2026-09-02 audit sweep;
fixed + revived that night — first genuine tick 03:52Z). It now
covers Mac-awake hours. This plan closes the cron-trigger gap during
nights/travel — its case is STRONGER than first written, since GH cron was the ONLY nowcast
scheduler for the entire 8/7–9/2 span, including the 8/27 dark
window. It does **not** survive a wedged GitHub Actions execution
queue and is therefore trigger redundancy, not an independent half-B.
Needs ~10 minutes of the user; no agent can create the credential.

1. USER: github.com → Settings → Developer settings → Fine-grained
   personal access tokens → Generate new token.
   - Name: barnacle-nowcast-dispatch · Expiration: 1 year
   - Repository access: ONLY JohnUrban/barnacle
   - Permissions: Actions = Read and write. NOTHING else.
   - Copy the token (ghp_… / github_pat_…).
2. USER: cron-job.org (free) → create account → new cron job:
   - URL: https://api.github.com/repos/JohnUrban/barnacle/actions/workflows/nowcast.yml/dispatches
   - Schedule: every 10 minutes
   - Request method: POST
   - Headers: Authorization: Bearer <TOKEN>
              Accept: application/vnd.github+json
   - Body: {"ref":"main"}
   - Expected response: 204 No Content.
3. Verify: Actions tab shows nowcast runs at true 10-min cadence
   (workflow_dispatch events). GH cron + launchd + external cron
   coexist safely (concurrency group serializes; day-max monotonic).
4. Revoke anytime at the token page; delete the cron job to stop.

Independent observation is a separate layer. Run
`bin/public_health_watchdog.py --notify` every 10 minutes from a host
outside GitHub; it checks Pages artifacts and successful workflow age,
and can publish a bounded ntfy failure alert. `WATCHDOG_NTFY_TOPIC`
selects the topic. Add `--require-arm local-launchd` only when the Mac
is expected to remain awake. Until that external process is actually
deployed, Barnacle still has no independent failure observer.

Execution redundancy is also separate. The local arm computes and
publishes nowcasts, but local alert delivery is intentionally not enabled:
it would require securely provisioning the production SMTP/ntfy secrets
outside GitHub and validating idempotency against the hosted arm. Treat
that as an owner-approved security/operations project, not an implied
property of this trigger plan.

Risk: the service holds a token scoped to Actions-write on this one
public repo — worst case an attacker triggers workflow runs. No code,
contents, or secrets access.
