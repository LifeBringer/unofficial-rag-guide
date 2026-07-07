# The Unofficial Guide — UC Berkeley Housing (Project 1)

A RAG system that makes student-shared knowledge about UC Berkeley housing searchable and answerable, with citations, from 12 real r/berkeley threads and 2 student guides.

**Quick start**

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your free Groq key (console.groq.com)

python ingest.py              # raw documents -> cleaned records
python chunk.py               # -> 387 chunks (documents/processed/chunks.jsonl)
python build_index.py         # embed + load into ChromaDB
python app.py                 # web UI at http://localhost:7860
python query.py "What happens if I decline my housing offer?"   # or CLI
python evaluate.py            # reproduce the evaluation report
```

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

Generation runs on Groq's `llama-3.3-70b-versatile` (course default). Because the network this project was built on blocks `api.groq.com` at the IP level (403 for *any* key — verified with a deliberately invalid one), `query.py` automatically falls back to the **identical model** (`meta-llama/Llama-3.3-70B-Instruct`) served through Hugging Face's OpenAI-compatible Inference Providers router. With a working Groq key on a normal network, the fallback never runs.

**System prompt grounding instruction:** the actual system prompt (see `SYSTEM_PROMPT` in `query.py`):

> You are The Unofficial Guide, answering questions about housing at UC Berkeley using ONLY the numbered sources provided in the user message. […]
> 1. Use only information stated in the sources. Never add facts from your general knowledge, even if you are confident they are true.
> 2. If the sources do not contain enough information to answer the question, reply with exactly: "I don't have enough information on that in my documents." — do not attempt a partial guess from general knowledge.
> 3. Cite every claim with its source number in brackets, e.g. [Source 2].
> 4. These are student opinions, not verified facts: attribute them ("one commenter reports…") and mention the year when the sources span different years or the info could be dated (e.g. prices).
> 5. If sources disagree, present both sides with their citations.

Structurally, the retrieved chunks are injected as a numbered context block — `[Source 1] (r/berkeley thread "TITLE", YEAR)` followed by the chunk text — so every citation the model makes maps to a specific chunk with a year attached. The exact-refusal-phrase rule makes refusals detectable and keeps them from drifting into "however, generally speaking…" answers.

One deliberate *non*-mechanism: there is **no distance-threshold refusal gate**. Milestone 4 measurements showed near-domain off-scope queries ("best boba near campus?", distance 0.448) are indistinguishable by distance from hard on-topic queries ("decline my housing offer", 0.44), so a cutoff would either miss off-scope queries or reject legitimate ones. Refusal is the LLM's job, given the grounding prompt — and the out-of-scope tests below show it works, including on that exact boba query.

**How source attribution is surfaced in the response:** twice, independently. (1) The model cites `[Source N]` markers inline per the prompt. (2) The `sources` list under every answer is **built in code** from the retrieval metadata of the chunks actually placed in the context window — numbered exactly as the model saw them — so attribution is guaranteed even if the model forgot to cite. The LLM has no ability to add or remove entries from that list.

**Known grounding limits (from adversarial testing):** I red-teamed the system with 15 adversarial probes (general-knowledge bait, false-premise questions, prompt injection). It held on 12/15 — including refusing "What is the capital of France?", correcting "Since BART is free for Cal students…" from the corpus, and rejecting persona-override injections. Three honest weaknesses: (1) under a false-premise question about the lottery it asserted a *plausible but uncited* negation and pinned it to a real source number whose chunk says nothing about the lottery — the code guarantees the source *list* is real, but cannot guarantee every *claim* actually appears in its cited chunk (see Failure Case Analysis); (2) a direct "ignore your instructions" injection was resisted but answered with meta-commentary instead of the exact refusal phrase, leaking one generic sentence; (3) one answer conflated two co-ops mentioned in the same thread (attributed a POC resident's experience to Casa Zimbabwe). Grounding enforces *provenance of context*, not *fidelity of every generated sentence* — a limitation worth stating plainly.

---

## Example Responses

All three are real `python query.py "<question>"` outputs — quoted verbatim except where an abridgement is explicitly marked (`[…]` / *"+2 more context sources"*).

**Grounded response 1**

Query: `What happens if I decline my UC Berkeley housing offer?`

Response:

> One commenter reports that if you decline your UC Berkeley housing offer, you will have about 1.5 months to secure housing for yourself, which can be a "nightmare" [Source 1, 2019].

Source attribution (in the output text, built programmatically from retrieval metadata):

> Retrieved from:
> • [Source 1] reddit_housing-lottery — "How exactly does housing work?" (2019) https://www.reddit.com/r/berkeley/comments/bf0l31/how_exactly_does_housing_work/
> • [Source 2] reddit_apartment-timeline — "Good time to look for housing?" (2022) …
> • [Source 3] reddit_freshman-dorms — "URGENT: how to switch out of 'blackwell'" (2022) …
> *(+2 more context sources listed in the actual output)*

**Grounded response 2**

Query: `When should I start looking for an off-campus apartment for the fall?`

Response:

> One commenter reports that it's not necessary to secure housing as early as January or February [Source 5]. The Off-Campus Housing team recommends starting the search 6-8 weeks before the move-in date [Source 3], while another student suggests starting to look in March and April [Source 4]. Additionally, one guide advises waiting at least until April to start the search and not to secure housing until the desired start date is available [Source 5].

Source attribution:

> Retrieved from:
> • [Source 1] reddit_apartment-timeline — "Good time to look for housing?" (2022) https://www.reddit.com/r/berkeley/comments/t16je2/good_time_to_look_for_housing/
> • [Source 2] web_offcampus_search_tips — "Off-Campus Housing Search Tips" (2024) https://life.berkeley.edu/off-campus-housing-search-tips/
> • [Source 3] web_housing_what_to_expect — "Finding Housing Off Campus: What to Expect" (2024) https://life.berkeley.edu/finding-housing-what-to-expect/
> *(+2 more context sources listed in the actual output)*

Note how rule 5 of the grounding prompt shows up here: the corpus genuinely disagrees about timing (the 2022 Reddit thread says start in February; the student-life guides say 6–8 weeks out is fine), and the answer presents both camps with citations instead of picking one.

**Out-of-scope query**

Query: `What's the best boba place near campus?`

System response (refusal):

> I don't have enough information on that in my documents.

This is the hard refusal case on purpose: retrieval still returns *something* (neighborhood-overview chunks mentioning Telegraph Avenue cafes, at distance 0.448 — nearly identical to legitimate queries), but the model correctly judges that nothing retrieved answers the actual question. A second probe, `Who is the best professor for CS 61A?`, refuses identically.

---

## Query Interface

A Gradio web UI (`python app.py` → http://localhost:7860). There is also a CLI (`python query.py "<question>"`) used for the retrieval tests and evaluation above.

**Input fields:**

- **Your question** — a single free-text box (submit with Enter or the **Ask** button).
- Five clickable example questions below the box for instant demoing.

**Output format:**

- **Answer** — the grounded response with inline `[Source N]` citations.
- **Retrieved from** — the programmatic source list: `[Source N] document — "thread title" (year) URL`, numbered to match the citations.
- **Retrieved chunks (what the model actually saw)** — a collapsed accordion showing the raw top-5 chunks with their cosine distances, for transparency and debugging.

---

**Sample Interaction Transcript**

As it appears in the interface — Answer and Retrieved-from fields verbatim (the third output field, the collapsed Retrieved-chunks accordion, is omitted here for length):

> **User:** What happens if I decline my UC Berkeley housing offer?

> **System (Answer):** One commenter reports that if you decline your UC Berkeley housing offer, you will have about 1.5 months to secure housing for yourself, which can be a "nightmare" [Source 1, 2019].
>
> **System (Retrieved from):**
> • [Source 1] reddit_housing-lottery — "How exactly does housing work?" (2019) https://www.reddit.com/r/berkeley/comments/bf0l31/how_exactly_does_housing_work/
> • [Source 2] reddit_apartment-timeline — "Good time to look for housing?" (2022) https://www.reddit.com/r/berkeley/comments/t16je2/good_time_to_look_for_housing/
> • [Source 3] reddit_freshman-dorms — "URGENT: how to switch out of 'blackwell'" (2022) https://www.reddit.com/r/berkeley/comments/v1xbix/urgent_how_to_switch_out_of_blackwell/
> • [Source 4] web_housing_what_to_expect — "Finding Housing Off Campus: What to Expect" (2024) https://life.berkeley.edu/finding-housing-what-to-expect/
> • [Source 5] reddit_subletting — "Subletter denies me of housing last minute…" (2022) https://www.reddit.com/r/berkeley/comments/upw41v/subletter_denies_me_of_housing_last_minute/

---

## Evaluation Report

Run with `python evaluate.py` — full traces (answers, sources, retrieved chunk ids with distances) are in [`documents/processed/eval_results.json`](documents/processed/eval_results.json). Judgments were made by hand against the expected answers written in `planning.md` *before* implementation.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | How much does a one-way BART ride from Oakland to Berkeley cost, and which transit is free for Cal students? | ~$2.25 one-way; AC Transit buses free for students; no general BART discount (randomized pilot only) | "$2.25 [Source 1]… AC Transit buses are free for Cal students [Source 1, 2, 5]" — all 5 chunks from the commute thread, distances 0.21–0.27. (Omits the no-general-BART-discount detail, which was in the retrieved chunk; both asked sub-questions answered correctly) | Relevant | **Accurate** |
| 2 | Which other company names do students say Raj Properties operates under? | ≥3 of the 8 aliases (Everest, URSA, Domingo, University Walk, Berkeley Park, A.S.K., Square One, Anchor Valley); great answers reflect that replies dispute the list | Named **all 8 aliases** [Source 1], then presented the former employee's dispute ("only associated with Kiran Properties and Sapna Investments") [Source 2] and the SquareOne confirmation [Source 4] | Relevant | **Accurate** |
| 3 | What do students warn will happen if you decline your UC Berkeley on-campus housing offer? | Never decline — ~1.5 months left to scramble; once declined you can only request a swap while holding an assignment | **"I don't have enough information on that in my documents."** — a refusal on a question the corpus can answer | **Off-target** (answering chunk ranked 8th, outside k=5) | **Inaccurate** |
| 4 | How do students compare Blackwell Hall and Unit 3 as freshman dorms? | Blackwell: newest, best facilities (study rooms, gym, game tables); Unit 3: worst facilities but good location, very social, cheaper | Quoted "objectively the best dorm facilities-wise" vs "the worst facilities-wise… good location and is very social", plus "far superior" amenities comment, with 2022 attribution [Sources 1–4] | Relevant | **Accurate** |
| 5 | What does a room in a shared apartment near campus typically cost, according to students? | Roughly $800–$1,500/month for private rooms in shared units (2023 thread), with concrete examples; studios and 1b1b higher | Gave three real, correctly-cited 2023 price points ($1,225, $1,300, $1,000) — but presented a **narrower range than the corpus supports** ($800–$1,500+), and 2 of 5 retrieval slots went to guide sections with no prices | Partially relevant | **Partially accurate** |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Score: 3 accurate, 1 partially accurate, 1 inaccurate.** The two imperfect results are exactly the failure modes `planning.md` anticipated (aggregation questions vs. top-k, and retrieval sensitivity) — analyzed below.

---

## Failure Case Analysis

**Question that failed:** Q3 — *"What do students warn will happen if you decline your UC Berkeley on-campus housing offer?"*

**What the system returned:** the exact refusal phrase — "I don't have enough information on that in my documents." — even though the corpus contains a direct answer (the 2019 housing-lottery comment: *"when you get the offer - DO NOT DECLINE - you're fucked if you do because now you have essentially about 1.5 months to secure housing for yourself"*).

**Root cause (tied to a specific pipeline stage):** this is a **retrieval failure, measured precisely**. Ranking the full index for this exact question puts the answering chunk (`reddit_housing-lottery:003`) at **rank 8, distance 0.432** — the k=5 cutoff fell at 0.417, so it missed the context window by 0.015 cosine distance. Two mechanisms produced that miss:

1. *Query phrasing pulled the wrong neighborhood.* The words "students warn," "on-campus," and "housing offer" match the two Berkeley Life guides' Q&A-style prose ("Finding Housing: What to Expect") better than any single Reddit comment — guide sections took 4 of the top 5 slots without containing the warning.
2. *The answering chunk's embedding is diluted.* That comment covers the whole housing process in one breath (offer timing, the decline warning, and general advice), so its embedding sits "between topics" instead of squarely on declining offers.

The proof it's retrieval and not generation: the paraphrase **"What happens if I decline my UC Berkeley housing offer?" retrieves the same chunk at rank 1 and answers correctly** (it's Grounded Response 1 in the Example Responses section). Same index, same prompt, same model — a 7-word phrasing change flips the outcome. Given the chunks it actually received, the model's refusal was the *correct* behavior; the failure happened one stage earlier.

**What you would change to fix it:** three candidate fixes, in order of expected value: (1) **hybrid retrieval** — BM25 would score the literal word "decline" heavily and rank the comment in the top 3 (this motivated the Hybrid Search stretch feature); (2) raise k from 5 to 8 (would have caught it here, at the cost of more dilution on questions like Q5); (3) query expansion — retrieve on 2–3 LLM-generated paraphrases and merge results, directly attacking phrasing sensitivity.

**Secondary failures worth recording:** Q5 (rent) retrieved only 3 of the 38 price-bearing chunks in the index (the raw thread has 44 price-bearing comments; 6 didn't survive dedup/length filtering) and reported an unrepresentatively narrow range — the aggregation-vs-top-k failure `planning.md` predicted; it can't be fixed by retrieval tuning alone (a "what's typical" question needs *all* the data points, i.e., a metadata-filtered aggregation step, not similarity search). And adversarial red-teaming (see Grounded Generation) found a reproducible **citation fabrication** under false-premise questions — a generation-stage failure where a plausible uncited claim gets pinned to a real source number.

---

## Spec Reflection

**One way the spec helped you during implementation:** writing the evaluation plan — with expected answers verified against the raw corpus *before any pipeline code existed* — turned evaluation from a vibe check into a mechanical comparison, and it forced better questions: Q5 was deliberately designed as an aggregation stressor because the spec's Anticipated Challenges section predicted top-k retrieval would fail at "what's typical" questions, and that prediction landed exactly (Q5 graded partially accurate for an unrepresentative range). The chunking section paid off the same way: because the spec committed to numbers and reasons (900-char cap, 120 overlap, title prefix, per-comment chunks), the AI-generated implementation matched intent on the first pass and every deviation was detectable as a deviation instead of a silent choice.

**One way your implementation diverged from the spec, and why:** two ways worth owning. First, the spec's "1 comment = 1 chunk" rule turned out to be self-contradictory for the 12 comments longer than the 900-char cap — a 1,056-char comment can't both stay whole and respect the cap. The implementation splits oversized comments like long prose (never across authors), and `planning.md` was updated to say so. Second, the spec named Groq's `llama-3.3-70b-versatile` as the generation endpoint; it turned out `api.groq.com` is IP-blocked from the network this was built on (403 for *any* key, including a deliberately invalid one — a network block, not an auth failure). Rather than swap models and invalidate the course setup, `query.py` keeps Groq as the default path and falls back automatically to the *identical* model (`meta-llama/Llama-3.3-70B-Instruct`) via Hugging Face's OpenAI-compatible router — so graders on a normal network run exactly what the spec promised.

---

## AI Usage

The AI tool used throughout was **Claude (Claude Code CLI)**, following the per-milestone plan in `planning.md`.

**Instance 1 — ingestion & chunking (`ingest.py`, `chunk.py`)**

- *What I gave the AI:* the Chunking Strategy and Documents sections of `planning.md`, the skim notes from `documents/SOURCES.md` (including the known data quirks: duplicate live/deleted comment records in 3 files, one image post with empty selftext), and the architecture diagram.
- *What it produced:* the two pipeline scripts implementing the spec — per-comment chunks, 900-char cap, selective 120-char overlap, title prefixes, id-dedup.
- *What I changed or overrode:* I didn't accept the first output. I had the generated pipeline audited against the actual corpus, which surfaced four cleaning gaps the code missed: "Want More?" cross-promo boilerplate leaking into both web guides' final chunks, WordPress image captions landing as context-free fragments, a `![gif](giphy|…)` embed surviving as junk text, and U+2060 word-joiner characters glued to "URSA" (which would have silently broken keyword search later). I directed fixes for all four and re-ran the audit. I also resolved a spec bug the audit exposed — "1 comment = 1 chunk" contradicts the 900-char cap for 12 oversized comments — by choosing the split-within-author behavior and updating `planning.md`.

**Instance 2 — grounding design & adversarial testing (`query.py`)**

- *What I gave the AI:* the grounding requirement from the project instructions (context-only answers, refusal on insufficient context, source attribution), my output contract (`ask() → {answer, sources, hits}`), and — after Milestone 4 — the measured distance data showing near-domain off-scope queries (boba, 0.448) are indistinguishable from hard on-topic queries (decline-offer, 0.44).
- *What it produced:* the system prompt with the exact-refusal-phrase rule and the numbered-source context block, plus a proposed distance-threshold refusal gate.
- *What I changed or overrode:* I killed the distance-threshold gate — the 0.448-vs-0.44 measurement proves it would either miss off-scope queries or reject legitimate ones — and made prompt-level refusal the only scope mechanism, with attribution moved out of the model's hands entirely (the source list is built in code from retrieval metadata). I then directed a 15-probe adversarial red-team against the finished system; when it found a reproducible citation fabrication under false-premise questions, I chose to document it as a known limitation rather than patch-and-hide it, since the course values honest failure analysis over cosmetic robustness.

**Instance 3 — a bug the AI's design caused, caught in testing**

- *What I gave the AI:* the source-attribution requirement ("list which documents the answer draws from").
- *What it produced:* a source list deduplicated by document — which silently broke citation numbering: an answer citing `[Source 4]` could ship with no "Source 4" line when that chunk's document already appeared earlier in the list.
- *What I changed or overrode:* caught it by reading real output during Milestone 5 testing (the landlords query cited `[Source 4]` and `[Source 5]` but listed entries 1, 2, 3, 5). I overrode the dedup: the printed list now shows every context slot, numbered exactly as the model saw them, even when documents repeat — alignment beats brevity for attribution.
