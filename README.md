# odyssey-ticket-watch

Watches Cineplex for new bookable **IMAX 70mm** sessions of *The Odyssey* at
Cinéma Banque Scotia Montréal and pushes a phone notification via
[ntfy.sh](https://ntfy.sh).

Runs on GitHub Actions. No dependencies, no account beyond GitHub.

## How it works

One request to Cineplex's public showtimes API returns every 70mm session
across all bookable dates. Each session is tracked as `YYYY-MM-DDTHH:MM` in
`seen_sessions.json`, committed back to the repo after each change. You are
only notified about sessions that have never been seen before — so a new date
going on sale alerts once, not once every five minutes.

The first run seeds the state file and stays deliberately quiet.

## Setup

1. **Install the ntfy app** on your phone (iOS / Android) and subscribe to your
   topic. The topic name is the only secret — anyone who knows it can read your
   alerts, so keep it private.

2. **Add the topic as a repo secret**: Settings → Secrets and variables →
   Actions → New repository secret, named `NTFY_TOPIC`.

3. **Enable Actions**: the Actions tab → "I understand my workflows, go ahead
   and enable them".

4. **Trigger it once manually**: Actions → odyssey-watch → Run workflow. This
   seeds the state file *and* activates the schedule (GitHub does not start a
   cron until the workflow has run at least once on the default branch).

## Notes and limits

- **Cron is best-effort.** `*/5` is GitHub's floor, but scheduled runs are
  routinely delayed 10–30+ minutes under load. Treat this as "you'll hear
  within the hour", not "within five minutes".
- **Schedules auto-disable after 60 days of repo inactivity.** The state
  commits count as activity, so in practice this keeps itself alive.
- **Public repo** is recommended: Actions minutes are free on public repos,
  whereas this schedule would blow through the private-repo free tier. The
  topic stays private because it lives in a secret, not in the code.
- If the API returns zero sessions (outage, or the film finishing its run) the
  state file is left untouched rather than wiped.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `NTFY_TOPIC` | *(unset)* | ntfy topic. If unset, alerts print to stdout instead of sending. |
| `STATE_FILE` | `seen_sessions.json` | Where seen sessions are stored. |
| `ALERT_ON_NEW_TIMES` | `1` | Set `0` to alert only on brand-new dates, ignoring extra showtimes added to dates already on sale. |

## Running locally

```bash
NTFY_TOPIC=your-topic python3 check_odyssey.py
```

Credit: forked from [vicliv/odyssey-ticket-watch](https://github.com/vicliv/odyssey-ticket-watch).
