# Demo recording plan and script

Status: LOCAL PLAN. Nothing has been recorded and nothing has been uploaded.

Target length: 3 minutes. The competition asks for one demonstrated multi-turn
session, so the live run is the spine of the video and everything else is
support.

The recording deck is `docs/demo_presentation.html`. Open it directly in a
browser. Arrow keys move between shots, `N` toggles private speaker notes, `C`
hides the controls for a clean recording, `F` enters full screen, and `H` shows
the keyboard guide. Shot 3 deliberately hands off to the real terminal demo.

The companion teleprompter is `docs/demo_teleprompter.html`. Space starts or
pauses auto-scroll, the speed slider changes pace, arrow keys change shots,
`+` and `-` change script size, `C` hides presenter cues, and `F` enters full
screen.

## Before recording

1. Confirm the catalog is present:
   `ls -l data/catalog.jsonl` should show about 60.5 MB.
2. Run the tests once so the terminal shows a clean state:
   `python3 -m unittest discover -s tests`
3. Set the terminal to a large readable font. The product IDs must be legible.
4. Close anything showing a machine-local path, a credential, a private
   message, or another project.
5. Decide the recording tool and check that it captures terminal text sharply.

## Shot list

| # | Time | Shot | Command or content |
| --- | --- | --- | --- |
| 1 | 0:00 to 0:20 | Title and problem | Slide or spoken intro |
| 2 | 0:20 to 0:35 | Starter baseline | Show `results/baseline.json` |
| 3 | 0:35 to 1:35 | Live multi-turn session | `python3 demo.py --top-k 3` |
| 4 | 1:35 to 2:10 | How it works | Diagram or four-point slide |
| 5 | 2:10 to 2:40 | Full evaluation result | `python3 -m evaluator.local_evaluator --output results.json` or the pre-run `results/final-verification.json` |
| 6 | 2:40 to 3:00 | Cost, latency, honesty slide | Spoken over a static slide |

Shot 5 note: the full run takes about 28 seconds. Either record it and speed it
up in the edit, or show the checked evidence file. Do not cut the run and imply
it was instant.

## Script

Numbers below are locally verified. Do not change them without rerunning.

The diction follows the Tend demo style: start with a concrete customer
story, let the product speak for itself, explain the mechanism only after the
product moment, and finish by separating verified evidence from what remains
unknown.

Mention the algorithm, but do not lead with it. In the narration, describe it
as a deterministic retrieval and reranking algorithm, meaning the same input
produces the same output without a model call. Keep `SQLite FTS5`, `BM25`, and
field weights as optional text on the slide rather than spoken jargon.

**Shot 1, problem (0:00 to 0:20)**

"Here is the entire customer brief: 'I need a wallet.' That is it.

No brand, no material, no colour, no price. And somewhere inside fifty thousand
products is the one they actually want.

So rather than tell you our agent understands shopping intent, here is the
whole conversation running end to end."

**Shot 2, baseline (0:20 to 0:35)**

"Before I run it, one number, just so you know where we started.

The official starter found the target in twenty five out of two hundred
released public sessions. Twelve and a half percent.

Finding wallets was only the first step. The system still had to carry the
conversation forward."

**Shot 3, live session (0:35 to 1:35)**

Run `python3 demo.py --top-k 3`. Narrate over the real output.

"Alright. So this is the first message: 'I'm looking for wallets, but I'm still
exploring.'

It is a decent start. The matches are wallets, and it asks what requirement
matters most.

But it still does not know the material or the colour. The customer has not
said either of them yet. Which is exactly why it asks.

So this is what I'm going to give it: leather, black.

That is it. Two words.

And there we go. Black leather wallets have moved to the top.

Notice what I did not repeat. I never said wallet again.

The first message gave it the shopping job. The second message gave it the
judgment. The agent kept both."

Do not claim the shown product is the hidden target. It is not scored here.

**Shot 4, how it works (1:35 to 2:10)**

"Now, underneath that, four small things are happening.

It keeps the useful words from earlier. It asks for the missing detail. It drops
filler like 'what matters is.' Then it reranks the same catalog.

A match in the product title counts more than a loose mention in the
description.

And the same conversation gives the same result every time. There is no model
call behind it.

The customer never sees any of that. They just do not have to start again."

**Shot 5, results (2:10 to 2:40)**

"Alright, that is one conversation. So then we ran all two hundred released
public sessions.

The starter found twenty five targets. This agent found one hundred and eighty
seven. That gives us a Hit Rate at 10 of 0.935, a technical score of 0.808740,
and an average of 2.945 turns to reach the target.

We tried other changes along the way. Some sounded clever and made the score
worse, so they did not make it into this agent."

**Shot 6, cost and honesty (2:40 to 3:00)**

"Now, the demo and the evidence are two different things, so here is exactly
what we can claim.

Zero model tokens. Zero API cost. No network call.

On one local run, the median was twenty two milliseconds. On a later run it was
forty six, so that number depends on the machine and its load.

These are public development results. We have not seen the private set.

What we can prove is that the complete public result reproduced exactly.

The customer added two words, and the agent knew what those two words belonged
to. That is the whole thing."

## Hard rules for the recording

- Never state or imply a private-set result.
- Never call a demo recommendation the correct hidden target.
- Do not show `data/catalog.jsonl` contents on screen beyond incidental product
  titles already visible in normal agent output.
- Do not show any absolute machine path, credential, or private message.
- Do not show unrelated repositories or teammate personal information.
- If a take shows a wrong number, rerecord rather than correcting it in text.

## Decisions that remain Shoham's

- [SHOHAM DECISION REQUIRED] Which take to publish.
- [SHOHAM DECISION REQUIRED] Whether the video is public or unlisted.
- [SHOHAM DECISION REQUIRED] Who narrates, and how teammates are credited on
  screen.
- [SHOHAM DECISION REQUIRED] Final video URL. No upload has been performed.
