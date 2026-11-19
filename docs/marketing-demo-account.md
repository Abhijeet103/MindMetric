# Marketing recording account

Provision the dedicated synthetic account against the configured application database:

```sh
python manage.py create_marketing_demo
```

This creates `marketing-demo@mindmetric.invalid` on the default platform tenant,
verifies its email for password login, grants a non-renewing month of admin-funded
paid access, and excludes it from audience campaigns. It grants no staff, tenant
admin, or superuser permissions. The account has no real customer data and this
command does not send email or contact a payment provider.

Credentials are stored in `.local/marketing-demo.json` with owner-only permissions.
The directory is ignored by Git. Recording scripts should read this file at
runtime; never include it in a video, prompt, log, or commit. The synthetic
account's welcome-email marker is set during creation to prevent welcome email
attempts when recordings log it in.

Rerunning reuses the password and account. Access is extended only when fewer
than two days remain. The command refuses to change an existing account unless
its saved credentials match, and refuses credential-file symbolic links.
For another platform tenant, pass `--tenant SLUG`. It deliberately does not
alter institutional access rules or enable hidden test tracks.

Claude's project demo skill is `.claude/skills/demo-video/SKILL.md`. Use the
separate marketing workflow under `video/` for production of shorts; the account
command only provisions recording access. Configure `OPENAI_API_KEY` in ignored
`.env` for new OpenAI narration. YouTube and Instagram remain disconnected.
