# Plan: external 24/7 nowcast scheduler (half-B) — READY TO EXECUTE

Status: written 2026-08-07 (event #7 tripped the revisit trigger).
Half-A (launchd on the user's Mac, `bin/install_local_scheduler.sh`)
was BELIEVED installed 2026-08-07 but never fired once: the clone
was created 42 s before `bin/` existed on origin and never pulled
(2,077 consecutive failures; found by the 2026-09-02 audit sweep;
fixed + revived that night — first genuine tick 03:52Z). It now
covers Mac-awake hours. This plan closes nights/travel — its case
is STRONGER than written, since GH cron was the ONLY nowcast
scheduler for the entire 8/7–9/2 span, including the 8/27 dark
window. Needs ~10 minutes of the user; no agent can do step 1.

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
