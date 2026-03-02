Read the current codebase state — recent commits, open tasks, file structure, any messy bits. Then roast it. Be genuinely funny, specific to what you actually see (not generic jokes), and brutally honest. Reference real file names, real code patterns, real decisions. Think comedy roast, not code review. Keep it to a few paragraphs max — hit hard, get out.

## And you...

After the codebase roast, add an **"And you..."** section that roasts the developer's habits. Read `.claude/stats.json` and analyse the `recentSessions` array (last 10 entries), `lifetime` stats, `badges`, and `streak` data. Pull real numbers — no generic filler.

Look for these patterns and roast whichever are funniest:

- **Session timing** — Check dates. If most sessions cluster on the same day, or if there are long gaps between active days, call it out. (e.g. "3 sessions in one day then radio silence for 48 hours — the binge-and-ghost approach to software development")
- **Infrastructure vs product ratio** — Count sessions where `stepsCompleted` is 0 (tooling/planning sessions). If the ratio is high, roast it. (e.g. "5 out of 10 sessions completed zero steps — you're building tools to build tools to eventually build something")
- **Score trends** — Compare early vs recent `finalScore` values. If scores are dropping, rising, or wildly inconsistent, roast the trend.
- **Badge patterns** — Check `badges.allTimeEarned`. If one badge dominates (e.g. SURGICAL 6 times), roast the pattern. If NIGHT OWL is frequent, roast the sleep schedule. If CENTURION appears many times, question why it keeps triggering. Combine badges for comedy (e.g. "NIGHT OWL 7 times + SURGICAL 6 times = you make tiny precise cuts at 2am like some kind of vampire surgeon")
- **Commits/session** — Calculate average from recent sessions. If consistently low, roast it. If one session had a huge outlier, call it out.
- **Steps completed** — If lifetime `totalStepsCompleted` is low relative to `totalSessions`, roast the throughput.
- **Streak** — If current streak is low, or if best streak is embarrassingly short, roast it.

Tone: Same comedy roast energy as the codebase section. Specific, brutal, funny. Use the real numbers. 2-4 bullets max — quality over quantity.