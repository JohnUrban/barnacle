# Plan: external 24/7 nowcast scheduler (half-B) — READY TO EXECUTE

Status: written 2026-08-07 (event #7 tripped the revisit trigger).
Half-A (launchd on the user's Mac, `bin/install_local_scheduler.sh`)
is INSTALLED and covers Mac-awake hours. This plan closes nights/
travel. Needs ~10 minutes of the user; no agent can do step 1.

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

Risk: the service holds a token scoped to Actions-write on this one
public repo — worst case an attacker triggers workflow runs. No code,
contents, or secrets access.
