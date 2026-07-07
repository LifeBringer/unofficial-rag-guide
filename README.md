# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

**Student-shared knowledge about housing at UC Berkeley** — the dorm lottery, freshman dorm tradeoffs, co-op life, off-campus apartment hunting, landlord reputations, real rent prices, neighborhood safety, subletting, scams, and commuting from nearby cities.

This knowledge is valuable precisely because official channels don't carry it. The housing portal tells you the application deadline; it doesn't tell you that students warn **never to decline your housing offer** (you'd have ~1.5 months to scramble), that one notorious property company operates under at least eight different names, or that a private room in a shared apartment ran $800–$1,500/month in 2023. Those answers live in years of r/berkeley threads where Reddit's search can't reliably find them — buried in comment #47 of a thread from two years ago.

---

## Document Sources

14 documents: 12 r/berkeley threads (2019–2025) + 2 Berkeley Life student guides. Reddit blocks scrapers (403s even from a real browser on this network), so threads were collected via the **PullPush Reddit archive API** (`api.pullpush.io`) — one raw JSON file per thread (submission + all archived comments, saved unmodified). Full manifest with collection details: [`documents/SOURCES.md`](documents/SOURCES.md).

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | r/berkeley: "Good time to look for housing?" (2022) | Reddit thread | [reddit.com/…/t16je2](https://www.reddit.com/r/berkeley/comments/t16je2/good_time_to_look_for_housing/) · `documents/raw/reddit_apartment-timeline.json` |
| 2 | r/berkeley: "How exactly does housing work?" (2019) | Reddit thread | [reddit.com/…/bf0l31](https://www.reddit.com/r/berkeley/comments/bf0l31/how_exactly_does_housing_work/) · `documents/raw/reddit_housing-lottery.json` |
| 3 | r/berkeley: "Pros/cons of living in northside vs southside" (2020) | Reddit thread | [reddit.com/…/f4iex8](https://www.reddit.com/r/berkeley/comments/f4iex8/proscons_of_living_in_northside_vs_southside/) · `documents/raw/reddit_northside-southside.json` |
| 4 | r/berkeley: "Exposing the CO-OPs / Casa Zimbabwe" (2022) | Reddit thread | [reddit.com/…/tcreyk](https://www.reddit.com/r/berkeley/comments/tcreyk/exposing_the_coops_casa_zimbabwe/) · `documents/raw/reddit_coops-bsc.json` |
| 5 | r/berkeley: "PSA: DO NOT RENT WITH RAJ PROPERTIES" (2023) | Reddit thread | [reddit.com/…/12f4qqb](https://www.reddit.com/r/berkeley/comments/12f4qqb/psa_do_not_rent_with_raj_properties/) · `documents/raw/reddit_landlords.json` |
| 6 | r/berkeley: "How much do you pay in rent?" (2023) | Reddit thread | [reddit.com/…/11503dk](https://www.reddit.com/r/berkeley/comments/11503dk/how_much_do_you_pay_in_rent_i_want_some_rent/) · `documents/raw/reddit_rent-prices.json` |
| 7 | r/berkeley: "Parents posting for their kid's housing" (2023) | Reddit thread | [reddit.com/…/12scrpc](https://www.reddit.com/r/berkeley/comments/12scrpc/parents_posting_for_their_kids_housing/) · `documents/raw/reddit_roommates.json` |
| 8 | r/berkeley: "What are the more dangerous parts of Berkeley?" (2025) | Reddit thread | [reddit.com/…/1ih8viq](https://www.reddit.com/r/berkeley/comments/1ih8viq/what_are_the_more_dangerous_parts_of_berkeley/) · `documents/raw/reddit_safety.json` |
| 9 | r/berkeley: "URGENT: how to switch out of 'blackwell'" (2022) | Reddit thread | [reddit.com/…/v1xbix](https://www.reddit.com/r/berkeley/comments/v1xbix/urgent_how_to_switch_out_of_blackwell/) · `documents/raw/reddit_freshman-dorms.json` |
| 10 | r/berkeley: "Subletter denies me of housing last minute…" (2022) | Reddit thread | [reddit.com/…/upw41v](https://www.reddit.com/r/berkeley/comments/upw41v/subletter_denies_me_of_housing_last_minute/) · `documents/raw/reddit_subletting.json` |
| 11 | r/berkeley: "Signing a lease without actually seeing the place?" (2022) | Reddit thread | [reddit.com/…/wkkkiu](https://www.reddit.com/r/berkeley/comments/wkkkiu/please_help_signing_a_lease_without_actually/) · `documents/raw/reddit_scams.json` |
| 12 | r/berkeley: "How's the BART? Is it viable as a commute option?" (2023) | Reddit thread | [reddit.com/…/13b5bve](https://www.reddit.com/r/berkeley/comments/13b5bve/hows_the_bart_is_it_viable_as_a_commute_option/) · `documents/raw/reddit_commute-nearby.json` |
| 13 | Berkeley Life: "Off-Campus Housing Search Tips" | Web guide | [life.berkeley.edu](https://life.berkeley.edu/off-campus-housing-search-tips/) · `documents/raw/web_offcampus_search_tips.html` |
| 14 | Berkeley Life: "Finding Housing Off Campus: What to Expect" | Web guide | [life.berkeley.edu](https://life.berkeley.edu/finding-housing-what-to-expect/) · `documents/raw/web_housing_what_to_expect.html` |

---

## Chunking Strategy

**Chunk size:** structure-aware, body capped at 900 characters (~225 tokens). **One Reddit comment = one chunk** — comments are never merged across authors. Submission selftexts, web-guide sections, and the 12 comments longer than 900 chars are split on paragraph boundaries into ≤900-char pieces. Comments under 120 chars are dropped unless they're top-level replies ≥15 chars (that exception keeps data-bearing one-liners like *"800 single 2 blocks"* in the rent thread; it also admits some filler — see Failure Case Analysis).

**Overlap:** 120 characters, applied **only** when splitting long continuous prose (e.g., the 6,500-char Casa Zimbabwe exposé, web-guide sections). Overlapping pieces start with an `…` continuation marker. There is deliberately *no* overlap between comments: they're independent utterances by different authors, and overlap would bleed one person's opinion into another's chunk and break attribution.

**Why these choices fit your documents:** the corpus has two document shapes. Reddit comments are already natural chunks — a typical substantive comment (median chunk is 249 chars) is one self-contained thought: a price point, a warning, a timeline opinion. A fixed 500-char splitter would cut them mid-sentence or concatenate unrelated authors. Long-form prose (selftexts, guide sections) is the opposite: unsplit, it embeds as a diluted "about everything" vector that matches nothing strongly — hence the 900-char cap, which also fits comfortably inside MiniLM's ~256-token input window. Every chunk is prefixed with its thread/guide title (e.g., `[PSA: DO NOT RENT WITH RAJ PROPERTIES]`) so referential comments like *"avoid them at all costs"* carry their topic into the embedding. Preprocessing before chunking: dedupe comments by id (the PullPush archive returns live/deleted duplicate records in 3 files), drop `[deleted]`/`[removed]` bodies and bare-URL comments, unescape HTML entities, strip zero-width characters, markdown link syntax, image embeds, and web-page boilerplate (nav, image captions, "Want More?" cross-promo outros).

**Final chunk count:** **387** chunks from 14 documents — 335 comment chunks, 21 selftext pieces, 31 guide-section pieces (run `python chunk.py` to reproduce). Per-document counts range from 10 (northside-southside) to 51 (safety). This landed just above the 250–380 estimate in `planning.md`; the overshoot came from the top-level short-comment exception admitting more one-liners than estimated.

---

## Sample Chunks

Five **random** chunks (`python chunk.py --sample 5 --seed 201` — seeded so the sample is reproducible, not cherry-picked), each with an inspection note.

**Chunk 1** — source: `reddit_commute-nearby` (comment, 2023)

> [How's the BART? Is it viable as a commute option?] Ah, I see. That's unfortunate. I suppose I'll watch the alerts and see if it's reliable enough for my purposes. Thank you for the info.

*Inspection:* self-contained and clean, but content-free — a conversational sign-off that passed the 120-char filter on length alone. An honest limitation of length-based filtering (~12% of chunks are filler like this, per a full-corpus audit); retrieval ranking has to bury these, and the Failure Case Analysis section revisits it.

**Chunk 2** — source: `web_housing_what_to_expect` (guide section, split piece, 2024)

> [Finding Housing Off Campus: What to Expect — What to Consider When Searching] …pictures is not enough. If you can't tour a place yourself, try to find a friend or family member to view it for you. Preslee: I prioritized location and cost. I knew that I was going to sell my car upon arriving so I didn't want to be farther than walking distance from campus. I considered convenient amenities such as hand soap, paper towels, and weekly cleaning being provided, for example. I live in a place that comes with a meal plan so that was a huge appeal for me because convenience is ideal during the busy academic year. […]

*Inspection:* a long guide section correctly split — the leading `…pictures is not enough…` is the designed 120-char overlap carrying the tail of the previous piece, so the "tour it yourself or send a friend" advice survives on both sides of the boundary.

**Chunk 3** — source: `reddit_northside-southside` (comment, 2020)

> [Pros/cons of living in northside vs southside:] RSF is at the south end of campus, so point for South
> More restaurants on Durant, Telegraph etc so point for South.
>
> North is where the Soda and Cory lab buildings for CS and EE are, GPB and LKS for CNR and Bio, so point for North. Much less riffraff (not always) on the north end, so another point for North.

*Inspection:* exactly what a good chunk looks like — one author's complete, information-dense comparison, retrievable on its own for any "northside vs southside" query.

**Chunk 4** — source: `reddit_rent-prices` (comment, 2023)

> [How much do you pay in rent? I want some rent transparency so I know I'm not getting scammed] 950 for a single room half a block north of campus (utilities all included)

*Inspection:* a 76-char body kept by the top-level exception — this is precisely the data-bearing one-liner the exception exists for. Without the `[thread title]` prefix, "950 for a single room" would embed with almost no topical signal.

**Chunk 5** — source: `reddit_apartment-timeline` (comment, 2022, score 22)

> [Good time to look for housing?] I came in July and had three offers from landlords I found on calrental within a week. One was a room in an old lady's house for $900 a month 20 min walk north of campus, one was an efficiency in El Cerrito hills for $1450, and another was a maid room in a rich family house with no use of their kitchen allowed for $1300 (yikes). […] Definitely wouldn't use Cal rental or any other school-oriented platforms after that one time, CL and local FB groups is the way. […]

*Inspection:* high-value chunk — concrete prices, timing, and platform advice in one author's experience; abridged here with `[…]` for the README, stored in full (910 chars including the title prefix) in the index.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` — local, no API key or rate limits, 384-dimensional embeddings, normalized and stored in a persistent ChromaDB collection with cosine distance (`build_index.py`). All 387 chunks embed in ~2 seconds on a laptop. Its ~256-token input window is part of why chunks were capped at 900 characters — every chunk fits without truncation.

**Production tradeoff reflection:** if this were deployed for real users and cost weren't the deciding factor, I'd weigh:

- **Accuracy on informal text.** MiniLM is trained on general sentence pairs; Reddit slang ("traphouse," "fish" for unofficial co-op residents) is out-of-distribution. A stronger model (`bge-large`, OpenAI `text-embedding-3-large`, Cohere embed-v4) would likely rank idiomatic content better — but I'd A/B it on this eval set before paying for it, because on our observed queries MiniLM already puts the right chunk in the top 3 with distances 0.25–0.36.
- **Context length.** MiniLM's ~256-token window forces small chunks. A long-context embedding model would allow whole-comment-tree chunks and fewer split-boundary artifacts.
- **Local vs. API.** Local means zero per-query cost, no rate limits, and queries never leave the machine — which matters here, since housing queries can be sensitive ("is my landlord scamming me?"). An API model adds accuracy but also ~100–300 ms latency, a billing dependency, and an availability dependency. For a free campus tool I'd stay local (upgrading to `bge-small`/`gte-base` is nearly free accuracy); for a funded product I'd benchmark API models first.
- **Multilingual support.** MiniLM is English-only. If we ingested international-student housing groups (WeChat, KakaoTalk), code-switched posts would need `multilingual-e5` or an API model.

---

## Retrieval Test Results

Run with `python query.py "<question>"` — distances are cosine (lower = closer). On-topic top hits land 0.25–0.44. Far-off-topic queries ("best CS professor for 61A?") land 0.62+, but **near-domain off-scope queries land much closer** — "best boba near campus?" hits 0.448, essentially tied with the legitimate "decline my housing offer" query at 0.44. That measurement drove a design decision: distance alone cannot decide refusals, so out-of-scope handling is enforced in the generation prompt (see Grounded Generation) rather than by a similarity cutoff.

**Query 1:** `How much does a one-way BART ride from Oakland to Berkeley cost?`

Top returned chunks (all from `reddit_commute-nearby`, 2023):

- *(0.286)* "[How's the BART? Is it viable as a commute option?] I commute using a combination of Amtrak and BART (Davis > Richmond BART > Downtown Berkeley), so in my opinion, Oakland > Berkeley via BART is perfectly viable. There are low-income passes/rates if you qualify, otherwise you can save $3 by autoloading $48 for $45."
- *(0.313)* "…as other people mentioned, buses are free for students. the 6 down Telegraph has 10-12 min frequencies, the 51B down College has 15 min frequencies…"
- *(0.316)* "…Going from Oakland to Berkeley is only 2.25 one way on BART. Also AC Transit (buses) is free for students. Cal students don't get a BART discount as someone said unless they are chosen for part of the pilot program…"

Relevance explanation: every hit comes from the one thread where students discuss exactly this commute. The chunk that answers the literal question ($2.25 one-way) is #3 — the two chunks above it are *about* BART costs and viability (fare-loading discounts, free buses as the cheaper alternative), which is semantic search working as intended: it ranks by topical closeness, not by "contains the number the user wants." This is why generation gets k=5 chunks, not just the top hit.

**Query 2:** `Which other company names does Raj Properties operate under?`

Top returned chunks (all from `reddit_landlords`, 2023):

- *(0.254)* "…I am a former employee. Whatever you do DO NOT rent here! The name of other companies listed is completely false. Raj Properties is not associated with any of those. They are linked to Kiran Properties in the Fresno area and Sapna Investments."
- *(0.257)* "A lot of the other companies in Berkeley are actually owned by Raj. It's Raj with a different name. Everest Properties, Square One Management, Anchor Valley Partners, etc. All Raj. Here's a list I found: - Everest Properties - Raj Properties - URSA Apartments - Domingo Properties - University Walk Apartments - Berkeley Park Apartments - A.S.K. Rentals - Square One Management"
- *(0.287)* "what properties are the ones tha raj group controls?"

Relevance explanation: #2 is the 72-point comment containing the full alias list — a direct answer. But the *top* hit is a former employee's rebuttal claiming the alias list is false and naming two different affiliated companies. Both are maximally "about" the query, and cosine distance can't tell claim from counterclaim — the corpus genuinely disputes this fact, so good retrieval here means surfacing **both** sides, and it does. (#3 is the question that prompted the list; near-zero information but topically dead-on — a known cost of keeping short top-level comments.)

**Query 3:** `How do students compare Blackwell Hall and Unit 3 as freshman dorms?`

Top returned chunks (all from `reddit_freshman-dorms`, 2022):

- *(0.279)* "You were trolled. Blackwell is objectively the best dorm facilities-wise. Unit 3 is probably the worst facilities-wise but has a good location and is very social."
- *(0.293)* "Blackwell is far superior to most dorms. I've been there several times. Great study rooms, Gym, pool tables and Table Tennis Tables. Only a problem if you needed an apartment 😭"
- *(0.360)* "We r pretty sure ur trolling, but on the off chance ur not; many consider Blackwell to be the best dorm cuz it's the newest, unit 3 is def not the best, so u shoulda j stayed in Blackwell."

Relevance explanation: the top hit *is* the canonical comparison (the thread's 123-point top comment), and #2 adds the concrete amenities. Note the query never uses the words from the thread title ("URGENT: how to switch out of blackwell") — it matches on meaning, which is exactly what embeddings buy over keyword search: "compare X and Y as dorms" finds comments written as "X is objectively the best, Y is probably the worst."

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Example Responses

<!-- Provide at least 2 grounded responses (query + response + source attribution)
     and 1 out-of-scope query showing your system's refusal.
     All entries must be text — not screenshots. -->

**Grounded response 1**

Query:

Response:

Source attribution:

---

**Grounded response 2**

Query:

Response:

Source attribution:

---

**Out-of-scope query**

Query:

System response (refusal):

---

## Query Interface

<!-- Describe your query interface: what are the input fields, what does the output look like?
     Then provide a complete sample interaction transcript showing a real exchange. -->

**Input fields:**

**Output format:**

---

**Sample Interaction Transcript**

<!-- Show a complete query → response exchange as it actually appears in your interface.
     Must be text — not a screenshot. -->

> **User:** 

> **System:** 

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
