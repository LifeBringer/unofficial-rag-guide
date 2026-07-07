# Document Sources — Milestone 1

## Domain

**Student-shared knowledge about housing at UC Berkeley** — how the dorm lottery actually works, which landlords to avoid, what rent is "normal," whether co-ops are worth it, which side of campus is safer, and whether commuting from Oakland is a real option. This knowledge is scattered across years of r/berkeley threads and student-written guides; none of it appears in the official housing portal, which tells you application deadlines but not that you should *never decline your housing offer* or that one property company operates under eight different names.

## Questions this system should be able to answer

1. When should I start looking for an off-campus apartment for the fall?
2. Which property management companies do students warn against, and why?
3. How much do students actually pay in rent near campus?
4. How does the freshman housing application/lottery process work, and should I ever decline an offer?
5. Is living in a co-op cheaper than an apartment, and what are the downsides?
6. Which areas of Berkeley do students consider less safe to live in?
7. Is commuting from Oakland/El Cerrito via BART viable, and what does it cost?
8. How can I avoid rental scams when signing a lease sight-unseen?

## Sources (14 documents)

| # | File | Type | Source | Collected |
|---|------|------|--------|-----------|
| 1 | `raw/reddit_apartment-timeline.json` | Reddit thread (2022, 16 comments) | ["Good time to look for housing?"](https://www.reddit.com/r/berkeley/comments/t16je2/good_time_to_look_for_housing/) | PullPush archive API |
| 2 | `raw/reddit_housing-lottery.json` | Reddit thread (2019, 13 comments) | ["How exactly does housing work?"](https://www.reddit.com/r/berkeley/comments/bf0l31/how_exactly_does_housing_work/) | PullPush archive API |
| 3 | `raw/reddit_northside-southside.json` | Reddit thread (2020, 11 comments) | ["Pros/cons of living in northside vs southside"](https://www.reddit.com/r/berkeley/comments/f4iex8/proscons_of_living_in_northside_vs_southside/) | PullPush archive API |
| 4 | `raw/reddit_coops-bsc.json` | Reddit thread (2022, 17 comments) | ["Exposing the CO-OPs / Casa Zimbabwe"](https://www.reddit.com/r/berkeley/comments/tcreyk/exposing_the_coops_casa_zimbabwe/) | PullPush archive API |
| 5 | `raw/reddit_landlords.json` | Reddit thread (2023, 87 comments) | ["PSA: DO NOT RENT WITH RAJ PROPERTIES"](https://www.reddit.com/r/berkeley/comments/12f4qqb/psa_do_not_rent_with_raj_properties/) | PullPush archive API |
| 6 | `raw/reddit_rent-prices.json` | Reddit thread (2023, 84 comments) | ["How much do you pay in rent?"](https://www.reddit.com/r/berkeley/comments/11503dk/how_much_do_you_pay_in_rent_i_want_some_rent/) | PullPush archive API |
| 7 | `raw/reddit_roommates.json` | Reddit thread (2023, 31 comments) | ["Parents posting for their kid's housing"](https://www.reddit.com/r/berkeley/comments/12scrpc/parents_posting_for_their_kids_housing/) | PullPush archive API |
| 8 | `raw/reddit_safety.json` | Reddit thread (2025, 73 comments) | ["What are the more dangerous parts of Berkeley?"](https://www.reddit.com/r/berkeley/comments/1ih8viq/what_are_the_more_dangerous_parts_of_berkeley/) | PullPush archive API |
| 9 | `raw/reddit_freshman-dorms.json` | Reddit thread (2022, 63 comments) | ["URGENT: how to switch out of 'blackwell'"](https://www.reddit.com/r/berkeley/comments/v1xbix/urgent_how_to_switch_out_of_blackwell/) | PullPush archive API |
| 10 | `raw/reddit_subletting.json` | Reddit thread (2022, 43 comments) | ["Subletter denies me of housing last minute…"](https://www.reddit.com/r/berkeley/comments/upw41v/subletter_denies_me_of_housing_last_minute/) | PullPush archive API |
| 11 | `raw/reddit_scams.json` | Reddit thread (2022, 35 comments) | ["Signing a lease without actually seeing the place?"](https://www.reddit.com/r/berkeley/comments/wkkkiu/please_help_signing_a_lease_without_actually/) | PullPush archive API |
| 12 | `raw/reddit_commute-nearby.json` | Reddit thread (2023, 33 comments) | ["How's the BART? Is it viable as a commute option?"](https://www.reddit.com/r/berkeley/comments/13b5bve/hows_the_bart_is_it_viable_as_a_commute_option/) | PullPush archive API |
| 13 | `raw/web_offcampus_search_tips.html` | Web guide (Berkeley Life) | [Off-Campus Housing Search Tips](https://life.berkeley.edu/off-campus-housing-search-tips/) | curl (raw HTML) |
| 14 | `raw/web_housing_what_to_expect.html` | Web guide (Berkeley Life) | [Finding Housing Off Campus: What to Expect](https://life.berkeley.edu/finding-housing-what-to-expect/) | curl (raw HTML) |

## How these were collected

Reddit blocks direct scraping (both `reddit.com` and `old.reddit.com` return 403 to scripts, and the JSON API requires OAuth), so the threads were pulled from the **PullPush Reddit archive API** (`api.pullpush.io`) — a public archive of Reddit submissions and comments. For each topic I searched r/berkeley, picked the thread with the most substantive discussion (preferring ≥10 comments and concrete specifics like prices, company names, and street names), then saved the submission plus all archived comments as one JSON file per thread. Requests were spaced out and retried on rate limits. The two Berkeley Life guides are plain WordPress pages and were saved as raw HTML with `curl`.

Raw files are exactly what the sources returned — no cleaning yet. Cleaning happens in the ingestion pipeline (Milestone 3).

## Skim notes (what the documents look like, for chunking decisions)

- **Reddit threads are two-layered:** a submission (title + sometimes a long selftext, sometimes empty — thread 10 is an image post with *no* selftext) and a pile of comments ranging from one line to several paragraphs. Most useful facts live in individual comments (a price, a company name, a timeline) — each comment is usually a self-contained thought.
- **Comment quality is uneven:** `[deleted]`/`[removed]` bodies, jokes, and one-word replies sit next to 200-word expert answers. The archive also returns duplicate comment records (a live copy and a deleted copy with the same id) in 3 files — the pipeline must dedupe by comment id and filter junk.
- **The web guides are long-form:** structured sections with headers (timeline, budgeting, scam warnings, neighborhood profiles), several paragraphs each. Facts spread across paragraphs, unlike the punchy comments.
- **Dates matter:** threads span 2019–2025. Rent figures are mostly 2022–2023, lottery mechanics are from 2019 — responses should surface which thread (and year) they came from.

The two document shapes (short self-contained comments vs. long-form guide sections) suggest chunking should respect natural units — per-comment for threads, per-section/paragraph for guides — rather than a fixed character split. Final numbers to be decided in `planning.md` (Milestone 2).
