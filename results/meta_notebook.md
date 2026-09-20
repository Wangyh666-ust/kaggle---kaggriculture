# Kaggriculture: notes from replay hunting

I started this notebook as a collection of engine notes. It gradually
turned into a record of how I have been changing my own agent: download
the current leaders, work out which moves repeat, turn the repeatable
part into a local agent, and try to beat it from both seats.

That distinction matters. A replay is one match, not source code. The
losing player may be excellent, and the winner may only have had the
favorable seed or market order. I use both sides as evidence and do not
label every losing action as a mistake.

Kaggriculture is a 720-turn, two-player simulation. The leaderboard is a
skill rating based on wins, losses and ties; a larger coin margin does
not directly buy more rating. Local bank totals and ladder rating answer
different questions.

The first half of the notebook records the mechanics and earlier public
strategy families. Section 4 is the working diary: c14, Hamburger's
market-timing idea, c15/c16, the multi-leader refresh that produced
c18, the public-notebook ablation that produced c27, the horizon sweep
that produced c45/c64, the 9 August refresh that produced c68/C70, and
the 10 August loss audit and tournament that produced C71, the
intraday-capital experiment that produced C72, and the C90-C92 weed
recovery sequence. The fourth-quadrant experiment produced the negative C93 result. The
next live-loss audit then isolated opening feed denial and one-turn
fertilizer preemption; the bounded combination becomes C94.

### Public work I used

| Author / notebook | What I took from it |
| --- | --- |
| [Bovard — Getting Started](https://www.kaggle.com/code/bovard/kaggriculture-getting-started) | Agent contract |
| [Georgy Mamarin — Visualized](https://www.kaggle.com/code/georgymamarin/kaggriculture-visualized-what-every-crop-pays) | Mechanics and market charts |
| [Roman Rozen — Barnyard Economist](https://www.kaggle.com/code/romanrozen/strong-statr-baseline-agent-lb-950) | Melon timing and job-value framing |
| [Roman Tamrazov — Hamburger](https://www.kaggle.com/code/romantamrazov/kaggriculture-hamburger) | Staged mixed herds and clone-aware market timing |
| [Pilkwang Kim — Scenario-Aware](https://www.kaggle.com/code/pilkwang/kaggriculture-scenario-aware-economic-policy) | Economic scheduler lineage |
| [Kun Zhang — C03/C04/C05](https://www.kaggle.com/code/beicicc/kaggriculture-c05-mid-herd-10) | Herd target experiments |
| [prvsiyan — Frontier Lab](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals) | Cross-play gates |
| Public leaderboard replays | Repeated schedules, opponent responses and market timing |

The notebook embeds the exact candidate used in the final local gate.
Running it creates `main.py` and `submission.tar.gz`; it does not upload
anything by itself.


## 0. Setup

Uses the competition environment from `kaggle-environments` (see the competition data kit `AGENTS.md` / `README.md`).


### [CODE]import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version

try:
    installed_ke = version("kaggle-environments")
except PackageNotFoundError:
    installed_ke = "0"

# Kaggle's base notebook image may lag the competition runner. The replay-tape
# policies in this notebook require the current Kaggriculture mechanics.
# 1.32.4 is load-bearing, not just "recent": it made BUY_PRODUCT/BUY_SEED fail when
# the shed is at capacity, so a full shed can now silently block feed and starve
# animals. An agent tuned on 1.32.3 can desynchronise on the real runner.
if tuple(map(int, installed_ke.split(".")[:3])) < (1, 32, 4):
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "-U", "kaggle-environments>=1.32.4"
    ])

import kaggle_environments
print("kaggle-environments", kaggle_environments.__version__)

from kaggle_environments import make

BOARD, DAYS, TURNS_PER_DAY = 10, 30, 24
EPISODE_STEPS = DAYS * TURNS_PER_DAY  # 720
STARTING_MONEY = 3000


## 1. The game in one screen

| Knob | Default | Why it matters |
| --- | ---: | --- |
| Turns | 720 (30 x 24) | Long-horizon capital plan |
| Start cash | $3000 | Opening buys compete with each other |
| Land | NE $1k, SW $2k, SE $4k | Top public leaders almost always take **NE+SW**, rarely SE |
| Hire cost | fib(n) per extra hand **today** | First ~10 hands are cheap; 12+ gets expensive fast |
| Shed | 100 non-seed items | Overflow is destroyed — you must sell / liquidate |
| Win | Most **bank** coins | Unsold inventory does **not** count |
| Ladder | Skill rating | **Only** W/L/T; coin margin is irrelevant for Elo |

### Action economy beats the crop table

Each unit (farmer + hired hands) gets **one field op per turn**.  
A high-margin crop that costs two extra walks often loses to a weaker crop next to the shed.

**Rule of thumb:** hiring about 10 hands costs roughly **$143 for a full day** of parallelism. Under-hiring early is usually more expensive than over-hiring inside the cheap Fibonacci region.


### [CODE]def fib(n):
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def hire_day_cost(n_hands):
    # total cost to hire n hands starting from 0 hires today (mult = 1)
    return sum(fib(i) for i in range(n_hands))


ns = np.arange(1, 17)
costs = [hire_day_cost(int(n)) for n in ns]

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(ns, costs, "o-", lw=2, color="#0f766e")
ax.axvline(10, color="#f59e0b", ls="--", label="~10 hands (end of cheap region)")
ax.axvline(12, color="#dc2626", ls="--", label="~12 hands (steep)")
ax.set(
    xlabel="Hands hired today",
    ylabel="Total hire cost (coins)",
    title="Fibonacci hire curve (default mult=1)",
)
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

pd.DataFrame({"hands": ns, "day_cost": costs}).query("hands in [6, 8, 10, 11, 12, 14]")


## 2. Engine details that separate weak agents from strong ones

### 2.1 Melon yield window (trust the engine, not only the overview table)

For one-time crops, watering during a bonus window adds yield immediately:

- Melon `max_yield_day = 12` implies window start `ceil(12/2) = 6` → ages **6..12**
- A melon starts at `yield_units = 1`
- Each watered day in-window: **+1** (or **+2** if fertilized)
- Cap is **6**, so full water reaches max around **age 10**, not 12

**16 tiles x 6 = 96 melons** when execution is perfect.  
Missing water on days 6-10 is a common silent leak (for example ~70 units instead of ~96).

### 2.2 `SELL` only sees the shed

- `HARVEST` puts items into the **unit inventory**
- `SELL` spends items from the **shed**

If you harvest 90 melons and never `DROP` while shed-adjacent, the market may not see them until end-of-day auto-drop — often **too late** to fund same-turn land / animal buys.

### 2.3 Fertilizer can be sold

Competition text emphasizes buying fertilizer; the engine's generic `SELL` path still accepts it.  
Each animal generates fertilizer daily → a real sidecar income stream until the market is flooded.

### 2.4 Ladder scoring

Rating updates from **win / loss / tie only**.  
A 140k bank that loses still loses rating. Local mean bank vs `starter` is a useful filter, not the objective.


### [CODE]# Illustrative melon glut curve (public MARKET_PARAMS style, glut side only)
I0, BASE, T = 10000, 250, 300
above_target = 3.6  # melon above_target


def melon_price(inv):
    x = max(0.0, inv - I0)
    amp = above_target * BASE / (T ** 2)
    return max(1, int(round(BASE - amp * x * x)))


units_per_tile = 6
tiles = np.arange(1, 31)
marginal = []
inv = I0
for t in tiles:
    rev = 0
    for _ in range(units_per_tile):
        p = melon_price(inv)
        rev += p
        if p > 1:
            inv += 1
    marginal.append(rev - 80)  # minus seed cost

cum = np.cumsum(marginal)
best = int(tiles[np.argmax(cum)])

fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
axes[0].bar(tiles, marginal, color=["#0f766e" if v > 0 else "#cbd5e1" for v in marginal])
axes[0].axhline(0, color="#334155", lw=1)
axes[0].set(
    title="Marginal net value of the next melon tile",
    xlabel="Tile # sold into one glut path",
    ylabel="Revenue - seed",
)
axes[1].plot(tiles, cum, lw=2.5, color="#0f766e")
axes[1].scatter([best], [cum[best - 1]], s=80, color="#dc2626", zorder=3, label=f"peak ~{best} tiles")
axes[1].set(title="Cumulative net (labor ignored)", xlabel="Melon tiles", ylabel="Cumulative net coins")
axes[1].legend()
for ax in axes:
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print({
    "illustrative_peak_tiles": best,
    "note": "Labor and rival sales move the real optimum; public leaders often use ~6-16 melons, not a full 25-tile dump.",
})


## 3. Strategy clusters in the public meta

| Cluster | Opening | Peak farm | Strengths | Failure mode |
| --- | --- | --- | --- | --- |
| **A. Pure cow ranch** | 3-10 cows, little crop | ~10 cows, often NE only | Punishes soft / crop-only bots | Milk wars collapse banks; coin-flip H2H |
| **B. Melon IPO** | 16 melons + 2 cows | Day-10 dump to 12c+8s and 3 quads | Huge capital spike when uncontested | Second melon dumper hits the $1 floor |
| **C. Staged economic herd (C0x)** | **3 cows + 1 sheep** floor | Stages **4 to 8/10 to 14/15** | Strongest *public code* family | Everyone forks it → correlated losses |
| **D. Adaptive leader style** | 3c+1s, ~6 melons | Dynamic cow/sheep/goose mix | Rebalances when milk is contested | Harder to clone cleanly |
| **E. Stable efficiency tape** | Repeated elite trajectory | Tight 8c/6s production and labor schedule | Reproducible across opponents; current best live result | Can become correlated if widely copied |

### Approximate local strength ordering (sandbox H2H)

```text
starter << pure cow << melon IPO << C03 << C05 << Radiant routers << c11/c12/c13 << c14
```

**Caveat:** a bot that prints 100k-170k vs `starter` can still sit mid-ladder, because ladder opponents are other strong farms.


## 4. Replay diary: from c14 to the current multi-leader market meta

### 4.1 The first useful replay rule

My first mistake was treating the winner's tape as the target. That is
too noisy. I now look for three things before copying anything:

1. Does the same field schedule appear against several opponents?
2. Is the market schedule also stable, or is it reacting to the match?
3. Does the distilled tape beat the previous agent from both seats?

The earlier senkin13 refresh passed that test unusually cleanly: the
exact 720-turn field and market schedule appeared in five games. It
ended near 8 cows, 6 sheep and 7 strawberry plots, and became c14 after
I added an observation-driven final-eight-turn cleanup routine.

c14 beat c11, c12 and c13 27-3 each in the paired-seat gate and reached
2182.2 on its standalone ladder run. That was the point where replay
stability became more useful to me than selecting a spectacular single
score.


### 4.2 Hamburger changed the question from *what to build* to *when to sell*

The newer Hamburger notebook did not discover a radically different
mature farm. Its best branch, `Clone Quad H1`, checks whether the two
public farms remain nearly identical. After two close checkpoints it
looks one turn ahead in its own schedule and sells one available
premium line—melon, strawberry, milk or wool—before the expected
shared-market dump.

That is a small wrapper with a large mirror-match effect. Hamburger
reported 6-0 against its anchor, with a mean margin of +1,865.7. I
moved the same one-turn front-run onto the stronger refreshed Senkin
schedule. That hybrid became c15.


### [CODE]c15_gate = pd.DataFrame([
    ["raw refreshed Senkin", 14, 2, 0, 2249.8],
    ["Vlad stable", 9, 7, 0, 725.5],
    ["Hamburger Clone Quad H1", 16, 0, 0, 2083.9],
    ["c14", 16, 0, 0, 2300.2],
    ["Batuhan rank-one replay", 12, 0, 0, 2538.3],
    ["Chloe common tape", 12, 0, 0, 2431.1],
    ["Kenmatsu anchor", 12, 0, 0, 2735.2],
], columns=["opponent", "wins", "losses", "ties", "mean_margin"])
c15_gate


The important row is the first one. c15 went 14-2 against the same
refreshed Senkin tape without the wrapper. That convinced me the
timing rule was doing real work rather than merely decorating a
stronger base.

### 4.3 Refreshing the leaders—and catching my own downloader mistake

On 3 August I pulled five replays for each displayed top-five team:

```bash
python scripts/download_top_replays.py --top 5 --per-team 5 \
    --leader-submission-only --force
```

The `--leader-submission-only` part was added after a bad first pass.
Simulation teams can have two active submissions. My original script
merged both episode lists and picked the newest games, which sampled
Tran H Hoang's and Knight of Favonius's newer *lower-rated* agents,
not the submissions responsible for their displayed leaderboard
scores. The corrected run matches `publicScore` to the displayed team
score before choosing episodes.

The leaderboard moved while I was doing this, so the numbers below
are a timestamped snapshot, not permanent ranks.


### [CODE]replay_snapshot = pd.DataFrame([
    [1, "Tran H Hoang", 2858.3, 55203154, 5, 5, "5-0-0", "8c/5s, 5 strawberry, 12 hands"],
    [2, "Knight of Favonius", 2778.8, 55208294, 4, 4, "3-2-0", "8c/5s, 5 strawberry, 12 hands"],
    [3, "VN-Orion", 2735.3, 55207137, 1, 1, "4-1-0", "8c/5s, 5 strawberry, 12 hands"],
    [4, "Superallen001", 2717.9, 55207089, 1, 1, "2-3-0", "8c/5s, 4-5 strawberry, 12 hands"],
    [5, "ömer kiraz", 2700.9, 55210461, 3, 3, "4-0-1", "8c/5s, 5 strawberry, 12 hands"],
], columns=[
    "rank", "team", "rating", "submission_id", "field_variants",
    "market_variants", "sample_record", "mature_farm",
])
replay_snapshot


The striking result was not one clever move. It was convergence.
All five teams were using versions of the same 8-cow/5-sheep,
12-hand, three-quadrant plan. Many tapes from different teams differed
on only 2-5 field turns and 2-6 market turns. By contrast, this family
differed from c15 on about 226 field turns and 402 market turns.

Tran and Knight had several variants, so I did not use their highest
scoring replay as the new base. VN-Orion repeated one exact full tape
in all five games. Superallen also repeated one tape, and the two
stable versions are only four field turns and three market turns
apart. VN-Orion was the cleaner source for a standalone test.

I kept c15's clone-aware premium front-run and terminal cleanup, but
replaced its base schedule with the stable VN-Orion tape. That is the
c16 candidate below.


### [CODE]c16_gate = pd.DataFrame([
    ["c15", 14, 2, 0],
    ["Hamburger Clone Quad H1", 15, 1, 0],
    ["c14", 11, 1, 0],
    ["Vlad stable", 11, 1, 0],
    ["refreshed Senkin", 11, 1, 0],
    ["Batuhan rank-one replay", 11, 1, 0],
    ["Superallen common-meta tape", 7, 7, 2],
], columns=["opponent", "wins", "losses", "ties"])
c16_gate


The 7-7-2 control is reassuring rather than disappointing: the two
independently sampled common-meta tapes behave like the same policy.
Against the previous families, the new schedule has a clear edge.

### 4.4 Why identical uploads can show very different ratings

I also chased what looked like a packaging bug. The standalone c14
scored 2182.2, while a notebook-produced c14 initially showed 1210.1.
I downloaded the notebook's actual server artifact and compared it
byte for byte. Both `main.py` files had SHA-256
`569cf2d20e3b37c3805c2a4ca7c4e5728eaa85df85c78392cdc3df77c5ddc17b`.

They really were the same agent. Kaggle had simply created a new
rating instance. The standalone copy accumulated 89 public games;
notebook v9 had 26 before it was displaced. While I was checking,
v9 moved from 1210.1 to 1865.6 without a code change. Early opponents,
seeds and seats can put identical copies on very different rating
paths, and only the latest two team submissions continue receiving
games.


### 4.5 A ten-team refresh: the farm stayed fixed, the market moved

The next leaderboard snapshot had Ueddy first at 2847.0 and Tran H
Hoang second at 2821.9. I downloaded 12 public episodes for each of
the top ten teams, restricted to each score-matching active
submission: 120 replay selections in total.

The top ten had converged even more tightly than before. Almost all
mature farms ended near 8 cows, 6 sheep, 3 quadrants and 12 hands,
with 21 melon seeds and 44 strawberry seeds. The useful divergence
was market execution. Ueddy kept the same supply chain but scheduled
materially more premium liquidation than c16.

I distilled all 12 Ueddy traces with the same controller and screened
each against c16. Eleven swept the first 4-game paired-seat gate.
Episode `89746553`, player 1, had the strongest screen margin and
became c18.


### [CODE]premium_sales = pd.DataFrame([
    ["MELON", 146, 172],
    ["MILK", 360, 472],
    ["STRAWBERRY", 394, 505],
    ["WOOL", 241, 297],
], columns=["item", "c16_attempted_sales", "c18_attempted_sales"])

c18_gate = pd.DataFrame([
    ["c11", 10, 0, 14269.7],
    ["c12", 9, 1, 11128.0],
    ["c13", 9, 1, 10654.1],
    ["c14", 9, 1, 6263.7],
    ["c15", 7, 3, 2339.4],
    ["c16", 9, 1, 2794.4],
    ["c17", 9, 1, 2794.4],
], columns=["opponent", "c18_wins", "losses", "mean_margin"])

display(premium_sales)
c18_gate


The extended c16 gate finished **35-5** over 20 seeds and both
seats, with a +3,161.3 mean margin and no errors. Representative
tapes from the other refreshed leaders were also screened directly.
Anton's was the only close challenger; c18 won their extended
20-seed match 23-17, so c18 was preferred for head-to-head
reliability.

c18 changes only 20 pre-terminal field turns from c16 but 112 market
turns. This is the clearest evidence in the diary that the current
edge comes from inventory-sale timing rather than another change in
herd composition.


### 4.6 Three public notebooks and one terminal-timing correction

I then compared three newer public notebooks directly:

- Navaz's notebook restores Tran H Hoang episode `89674601`;
- Hamburger V27 uses that exact same source as its anchor and tests
  SELL-slot ordering plus terminal inventory relays;
- Kaito V18 selects complete market experts once per day using
  public-state distance, seat priors and hysteresis.

Navaz/Tran and Hamburger's anchor have the same SHA-256, so they are
one base strategy rather than two independent confirmations. Kaito
was the strongest import and beat c20, Navaz and Hamburger 18-2
each, but c17 still beat Kaito 17-3.

Field/market swaps were informative but did not promote. Kaito's
field with c17's market was competitive, while Kaito's market on a
mismatched field was weaker. A seat router also remained just below
c17. The transferable Hamburger finding was more mechanical: step
718 executes, while action index 719 does not.

c17's terminal field controller had taken over at step 712. Delaying
it to 717 preserves five more turns of the locally stronger tape and
still leaves steps 717 and 718 for terminal cleanup. This one-line
correction became c27.


### [CODE]c27_gate = pd.DataFrame([
    ["c17 Market Common", 13, 7, 0, 42.0],
    ["c20 Rank-One Medoid", 20, 0, 0, 5226.8],
    ["Navaz / Tran 89674601", 19, 1, 0, 3558.9],
    ["Kaito V18 Closed Loop", 19, 1, 0, 3559.8],
    ["Hamburger V27 experimental", 19, 1, 0, 4157.1],
], columns=["opponent", "c27_wins", "losses", "ties", "mean_margin"])
c27_gate


The fresh promotion gate finished **90-10**, using ten untouched
seeds, both seats and the official 1.32.2 engine, with no runtime
errors. This remains local evidence rather than a leaderboard-score
claim. More importantly, it came from a falsifiable engine detail
and survived direct comparison with the previous best.


### 4.7 The horizon arms race and the 9 August field refresh

By 8 August, 11 of the top 12 teams had converged on a
three-quadrant field ending near 8 cows, 6 sheep, 23 strawberries
and 31 wheat tiles. C45 kept that route but shifted eligible premium
sales two turns earlier, recording a debt so the original later sale
was reduced by exactly the shifted quantity. It reached 3085.4 and
rank 9 in the first live snapshot.

A sweep through horizon 28 was a useful warning. Horizon 25 won the
restricted long-horizon finalist gate, but then lost 0-6 to C45,
unmodified V14 and several shorter horizons on fresh seeds. Its live
score also finished below C45. Aggregate wins against weak historical
agents had hidden the strategically important parent regression.

On 9 August I downloaded ten scoring-submission replays from each of
the live top 20 teams: 200 selections. A single field hash appeared
in 144 episodes from 40 teams. Most ranks 3-20 were 99-100% identical
on field actions, and their recorded market decisions fit horizon 3
best. The real alternatives were Seb, HealthStone and THUNDER;
THUNDER's wheat-heavy route was the strongest in local cross-play.


### [CODE]refreshed_meta = pd.DataFrame([
    ["dominant common route", 40, 144, "~8c/6s, 23 strawberry, 31 wheat", "mostly horizon 3"],
    ["Seb family", 1, 10, "four quadrants, adaptive livestock", "distinct"],
    ["HealthStone family", 1, 10, "wheat-heavy, adaptive herd", "distinct"],
    ["THUNDER family", 1, 10, "wheat-heavy alternative", "strongest local exception"],
], columns=["family", "teams_seen", "episodes", "mature_field", "market_note"])

c68_gates = pd.DataFrame([
    ["focused frozen-candidate screen", "850000-850009", 253, 7, 0],
    ["all 60 refreshed top-replay reconstructions", "860000-860004", 622, 8, 0],
    ["untouched final block", "900000-900019", 342, 18, 0],
], columns=["gate", "seeds", "wins", "losses", "errors"])

display(refreshed_meta)
c68_gates


C68 combines the strongest refreshed THUNDER public field tape
(episode `91211393`, player 0) with a new market controller. The
controller observes premium-product market inventory changes,
removes its own sale and deterministic town drain, fits the
opponent's extra batches to horizons 1-6, and races one turn ahead.
It defaults to horizon 4 until enough evidence arrives.

This is narrower than C64's fixed horizon 25: it moves only as far
as the observed near-clone race requires. In diagnostics it correctly
identified horizons 2, 3, 4 and 5. The classifier is gated by public
farm similarity, so unrelated field families keep the base schedule.

The field tape is explicitly competitor-derived public replay data;
the online horizon inference is the original contribution. C68 was
frozen before the final block, finished **342-18** there with zero
errors, and was submitted as `55371099`.


### 4.8 Why C70 stalled below 3000, and the search that produced C71

C70 was not broken. I downloaded all 88 public episodes from its
live submission `55389625`, reconstructed the recorded opponents,
and verified the submitted agent action-for-action on 2,157 sampled
observations. It finished every game and went **83-5** with a
+14,196 mean margin. Its five losses were narrow against Jince, WBF,
Gould and Pranjal, plus one larger Ueddy loss.

That explains the rating plateau: Kaggle rating rewards wins, not
surplus coins. C70 already crushed weaker agents, while its rigid
route and largely fixed sell timing failed to convert the few close
games that mattered. Increasing margins against agents it already
beat could not reliably move a sub-3000 rating.

I reconstructed current public top-agent trajectories and screened
26 field/market combinations. Several routes fixed one historical
loss but regressed badly across the wider field. The useful change
was narrower: keep the proven route family, use market timing from
GiovanniCR episode `91533875` player 0, then sort premium SELLs by
estimated self-induced price impact. MELON, STRAWBERRY, MILK and
WOOL may move ahead of competing market dumps; WHEAT and FERTILIZER
retain safer timing because opponents can buy them.

This candidate became **C71 Giovanni Impact**. The replay-derived
backbone remains attributed to GiovanniCR. The reconstruction and
impact-ordering overlay are the contribution documented here.


### [CODE]c71_validation = pd.DataFrame([
    ["88 historical live opponents", "C70", "83-5", 14196, None],
    ["88 historical live opponents", "C71", "83-5", 14523, None],
    ["shared 39-agent holdout + direct", "C70", "341-56-3", None, 1953],
    ["shared 39-agent holdout + direct", "C71", "354-46", None, 1996],
    ["untouched four-agent round robin", "C70", "57-63", 81, 1487],
    ["untouched four-agent round robin", "C71", "83-37", 404, 1605],
    ["untouched direct matchup", "C71 vs C70", "31-9", 231, None],
], columns=["test", "agent", "record", "mean_margin", "Bradley_Terry"])
c71_validation


C71 ranked first in the untouched round robin and made zero runtime
errors. It beat C70 **31-9**, Nikita **25-15**, and the Ezz
alternative **27-13**. A separate broad holdout also preferred C71:
Bradley–Terry 1996 versus 1953 for C70.

The negative result is just as important. On the 88 historical live
episodes C71 improved mean margin by only +327 and converted none of
C70's five losses. Those games are an in-sample diagnostic, not a
forecast of a higher Kaggle score. Promotion rests on the fresh
holdouts; C71 has deliberately **not** been submitted at the time of
this notebook update.


### 4.9 C72: bank only the large load that is already beside the shed

A later replay against Aleks Lviv exposed a different opportunity.
Aleks briefly held roughly 4,000 more coins than C71. Copying the
whole irregular route did not transfer, and aggressive continuous
liquidation was much worse. The useful hypothesis was narrower:
some premium inventory could become working capital sooner without
disrupting the proven farm schedule.

I wrapped C71 with a protected logistics rule. From steps 120-679 it
may replace only `PASS` or movement—never planting, watering,
harvesting, feeding, collecting or care. A worker is diverted only
when carrying at least 2,000 coins of melon, strawberry, milk or wool
at current prices and already at most one move from a center-shed
access tile. On deposit, a sufficiently priced premium sale is moved
forward in the market queue.

This cutoff was sharp. No-diversion sale promotion, thresholds of
500 or 1,000, and every two-step diversion lost 0-8 to both C70 and
C71. Only the one-step, 2,000-value rule survived. Across ten
liquidity games it caused just 16 extra actor drops: 1.6 per game.


### [CODE]c72_threshold_gate = pd.DataFrame([
    ["d0_v1000", "0 steps / value 1000", "0-8", "0-8"],
    ["d1_v500",  "1 step / value 500",  "0-8", "0-8"],
    ["d1_v1000", "1 step / value 1000", "0-8", "0-8"],
    ["d2_v1000", "2 steps / value 1000", "0-8", "0-8"],
    ["d2_v2000", "2 steps / value 2000", "0-8", "0-8"],
    ["d1_v2000", "1 step / value 2000", "7-1", "7-1"],
], columns=["variant", "banking trigger", "vs C70", "vs C71"])

c72_validation = pd.DataFrame([
    ["day 15 liquidity", "9/10 positive", 208.9, "liquid-value delta"],
    ["15-opponent broad gate", "109-11", 5224.8, "120 games"],
    ["untouched vs C70", "29-11", 1352.7, "20 seeds, both seats"],
    ["untouched vs C71", "27-13", 1197.2, "20 seeds, both seats"],
    ["88 historical live tapes", "84-4", 24291.6, "fixed-tape diagnostic"],
], columns=["test", "result", "mean_delta_or_margin", "note"])

display(c72_threshold_gate)
c72_validation


On day 15 C72 averaged +168.5 cash and +208.9 liquid value versus
C71, with a positive liquid edge in 9 of 10 games. This is a reliable
few-hundred-coin improvement, not a reproduction of Aleks's 4,000
coin spike.

The final evidence was stronger than the small screen: **109-11**
against 15 representative reconstructed agents, then **29-11**
against C70 and **27-13** against C71 on 20 untouched seeds in both
seats. There were zero runtime errors. On the same 88 historical
live-opponent tapes used in the C70/C71 audit it went **84-4**, with
+24,291.6 mean margin and 93,615.6 mean bank. Fixed opponent tapes
are correlated diagnostics, so promotion rests on the fresh gates.

The transferable lesson is not “sell constantly.” It is: interrupt
logistics only for a large premium load whose banking cost is almost
free. C72 remains a local experiment and has **not** been submitted.


### [CODE]openings = pd.DataFrame([
    {"name": "Pure cow open", "melon_seeds": 0, "cows": 3, "sheep": 0, "notes": "expand cows later"},
    {"name": "Melon IPO open", "melon_seeds": 16, "cows": 2, "sheep": 0, "notes": "dump around day 10"},
    {"name": "C0x / radiant open", "melon_seeds": 6, "cows": 3, "sheep": 1, "notes": "mixed option value"},
    {"name": "Nishchal-like open", "melon_seeds": 9, "cows": 4, "sheep": 0, "notes": "early dairy density"},
])
openings["seed_cost"] = openings.melon_seeds * 80
openings["animal_cost"] = openings.cows * 400 + openings.sheep * 500
openings["rough_spend"] = openings.seed_cost + openings.animal_cost
openings["cash_left_from_3000"] = STARTING_MONEY - openings.rough_spend
openings


## 5. Live mini-simulations

### 5.1 Environment smoke test


### [CODE]def run_pair(a="starter", b="starter", seed=0, steps=720):
    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed}, debug=False)
    env.run([a, b])
    final = env.steps[-1]
    return {
        "seed": seed,
        "r0": final[0].reward,
        "r1": final[1].reward,
        "s0": str(final[0].status),
        "s1": str(final[1].status),
    }

pd.DataFrame([run_pair("starter", "random", seed=s) for s in range(3)])


### 5.2 Built-in baseline matrix

Expect `starter` to beat `random` and `pass` on average. Your bot should crush `starter` locally before you overfit the public leaderboard number.


### [CODE]rows = []
for a, b in [("starter", "random"), ("starter", "pass"), ("random", "pass")]:
    for seed in range(2):
        rows.append({"a": a, "b": b, **run_pair(a, b, seed=seed)})
pd.DataFrame(rows)


## 6. The build ladder I actually followed

I began with agents that merely survived validation, then moved through
pure cows, a melon capital event, staged mixed herds and public tape
routers. The last four steps mattered most:

- **c14:** choose a full schedule only after it repeats across opponents;
- **c15:** keep the schedule but front-run a clone's premium sale by one turn;
- **c16:** refresh the base when several leaders converge on a demonstrably
  stronger operating plan.
- **c18:** hold the common farm fixed and promote the premium market
  schedule that survives a ten-team replay screen.
- **c27:** preserve c17's strong market route but move terminal field
  control from step 712 to the verified final window at step 717;
- **c45:** preserve the converged route and shift premium clone sales by
  a conservative, debt-tracked two turns;
- **c68/c70:** refresh to THUNDER and use observation-driven or
  price-impact market ordering;
- **c71:** keep the proven route family, replace its market trace with
  the GiovanniCR public reconstruction, and promote premium sells by
  estimated price impact after a broad reconstruction tournament.
- **c72:** preserve C71's productive actions and bank only premium loads
  worth at least 2,000 when the shed costs no more than one move.

Every promotion used both seats. I keep the previous agent as an opponent
and add at least one unrelated public family. A high bank against
`starter` is a smoke test, not a promotion test.


## 7. Common bugs (high frequency)

| Bug | Symptom | Fix |
| --- | --- | --- |
| CARE ranked above melon WATER | Day 9 waters only part of the field; yield ~70 not ~96 | Water priority first in ages 6-12 |
| No DROP after HARVEST | Produce stuck in unit inventory; IPO underfunded | DROP when carrying melon/milk stacks |
| Dig melon tiles for pastures too early | Destroy fruit before harvest | Protect valuable melons until sold |
| Buy many cows day 0 with no feed reserve | Animals escape by day 2 | Reserve wheat cash before animal spam |
| Fixed 10 cows forever | Mirror banks collapse toward ~40k | Add sheep/strawberry/opponent routing |
| Optimize only mean bank vs starter | High local bank, mediocre Elo | H2H vs strong bots, both seats |
| Two near-identical active submits | Meta shift kills both | Diversify the second slot |


## 8. Local evaluation protocol

```text
1. Compile/import the exact packaged main.py
2. Self-play validation: both agents must finish DONE
3. Play the incumbent and the unmodified parent on disjoint seeds, both seats
4. Treat a loss to either as a veto, even if aggregate wins look strong
5. Play several genuinely different public field families
6. Report per-opponent records, not only the aggregate
7. Freeze all parameters, then run one untouched final seed block
8. Audit cash, feed, animal survival, shed overflow and runtime
9. Keep the result files, including losses
10. Only then build an archive
```

Shared-market games are not symmetric. A one-seat test can reverse the
apparent winner.


### [CODE]def h2h(agent_a, agent_b, seeds=range(3), both_seats=True):
    """Quick head-to-head helper. agent_* may be callables or built-in names."""
    seats = (0, 1) if both_seats else (0,)
    rows = []
    for seed in seeds:
        for seat in seats:
            env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)})
            order = [agent_a, agent_b] if seat == 0 else [agent_b, agent_a]
            env.run(order)
            final = env.steps[-1]
            r0, r1 = final[0].reward, final[1].reward
            me, opp = (r0, r1) if seat == 0 else (r1, r0)
            rows.append({
                "seed": seed,
                "seat": seat,
                "me": me,
                "opp": opp,
                "win": me > opp,
                "status0": str(final[0].status),
                "status1": str(final[1].status),
            })
    df = pd.DataFrame(rows)
    summary = {
        "games": len(df),
        "wins": int(df.win.sum()),
        "win_rate": float(df.win.mean()),
        "mean_bank": float(df.me.mean()),
        "mean_opp": float(df.opp.mean()),
    }
    return df, summary


# Example using built-ins only (swap in your agent callables locally)
df, summary = h2h("starter", "random", seeds=range(2))
print(summary)
df


## 9. The strategy history in one line

```text
melon tutorials -> cow ranches -> staged mixed herds -> economic schedulers
  -> larger target herds -> tape routers -> stable c14 efficiency schedule
    -> c15 clone-aware sale timing -> c16 common-meta schedule
        -> c18 rank-one premium-liquidation schedule
        -> c17 refreshed market-common tape -> c27 terminal-717 correction
          -> c45 debt-tracked horizon 2 -> rejected fixed horizon 25
            -> c68 refreshed field + online opponent-horizon inference
              -> c70 impact-first ordering -> c71 Giovanni market timing
                -> c72 one-step high-value intraday banking
```

The endpoint alone never explained the full gain. c14 improved labor and
inventory timing. c15 exploited market order in mirror games. c16 changed
hundreds of turns while actually using one fewer sheep: the current
leaders are buying more labor and coordinating the whole route, not just
maximizing animal count. c18 then changes almost no field structure but
more than one hundred market turns. c27 changes no economic policy at
all; it corrects when the terminal controller is allowed to replace the
proven field tape. C45 then showed that a small market-timing change can
transfer better than another full clone. C68 responds to the next meta
by separating field refresh from an observation-driven market race.
C71 keeps that lesson: broad route swaps regressed, while a targeted
market-trace refresh plus impact ordering beat C70 on untouched seeds.
C72 then adds a rare, protected logistics override: monetize only large
premium loads already beside the shed, leaving productive work intact.


## 10. Checklist before building the next archive

- [ ] Validation self-play ends `DONE` / `DONE`
- [ ] Harvested goods are dropped before a planned sale
- [ ] Final shed inventory is liquidated
- [ ] The replay source repeats across several opponents
- [ ] The selected replay belongs to the leaderboard-scoring submission,
  not merely the team's newest active submission
- [ ] Both seats were tested against the previous best
- [ ] The unmodified parent and incumbent are explicit veto opponents
- [ ] Parameters were frozen before an untouched final seed block
- [ ] A near-mirror control was included
- [ ] At least two non-mirror current field families were included
- [ ] Losses were inspected instead of removed as “bad demonstrations”
- [ ] The exact packaged `main.py` was imported in the smoke test


## 11. Where I would look next

C92 is the current local stopping point. It is not a general replanner: it
repairs only a random weed that blocks an operation the established route is
trying to perform, then resynchronizes at the next `PASS`. That narrowness is
the point. Broad cleanup and broad expansion spend action budget without a
demonstrated increase in win probability.

The next useful test is live calibration against changing opponents. A future
replacement should improve untouched, paired-seat win conversion while keeping
C92, C90/C91 and at least two unrelated farm families as veto opponents.


## 12. Random weeds: cleanup is useful only when it restores the route

Random weed spawns are asymmetric: one can appear on only one player's farm
and invalidate a deterministic build tape. The important question was not
"can a hand remove it?" but "does removal recover production without stealing
more valuable work?" Three successive agents isolated that question.

### 12.1 C90 — spend only genuinely idle labor

C90 may route either the farmer or a hired hand to a visible weed only when the
worker's current action and every remaining action that day are `PASS`, the
worker carries nothing, and enough turns remain to walk there and `DIG`. Day-end
reset returns the worker to the shed, so the original next-day route is intact.

In episode 91672053's local seed (`1623701510`), the weed appeared at `(0, 3)`
on step 72, was dug on step 90, and the planned wheat cycle planted the freed
tile on step 131. On an untouched 30-seed paired-seat block, C90 went
**16-14-30** against C89 (mean margin **+234**) and **37-15-8** against C72
(**+331**), with zero errors.

### 12.2 C91 — require demonstrated future use

C91 adds a future-use guard: even idle labor clears a weed only if the frozen
route later schedules `BUILD_PASTURE`, `BUILD_COOP`, `PLANT`, `PLACE`, `WATER`,
`HARVEST`, `FERTILIZE`, `FEED` or `CARE` on that tile. The episode-91672053 tile
qualifies because the route uses it repeatedly at steps 131, 235, 333, 429,
520 and 612.

The guard was economically neutral, as intended: over 100 paired-seat games,
C91 and C90 were **17-17-66**, with C91 at **-35.2** mean coins. In a corrected
nine-agent round robin they tied at **BT 1870**. The guard improves causal
discipline, not measured strength: freed space must actually be reused.

### 12.3 C92 — repair a productive action that is blocked now

Idle-tail cleanup misses the most expensive case: a worker arrives with animals
or seed and the scheduled productive operation fails because a weed occupies the
tile. C92 detects a weed under the actor's current `BUILD_PASTURE`, `BUILD_COOP`,
`PLANT` or `PLACE`, substitutes `DIG`, delays only that actor's route by one
turn, and carries the displaced action forward until the next scheduled `PASS`
absorbs the delay. Other actors and every market order remain unchanged.

In episode 91707480, C91's first hand reached `(5, 3)` with three cows at step
176; the weed caused both pasture construction and cow placement to fail. C92
instead executed `DIG`, delayed `BUILD_PASTURE`, `PLACE COW`, `FEED WHEAT` and
`CARE` on steps 177-180, then rejoined the tape. Against DePie's exact action
tape on seed `247063490`, that changed a **-7,288 loss** into a **+3,455 win**.
With weeds disabled, C91 and C92 tie exactly, confirming that the overlay is
dormant when nothing productive is blocked.

### 12.4 Opponent-aware result

| Gate | C92 record | Mean C92 margin |
| --- | ---: | ---: |
| vs C91, 100 games | **22-6-72** | **+446.6** |
| vs C90, 100 games | **22-6-72** | **+388.1** |
| vs C91, independent 40 games | **3-1-36** | **+17.2** |

The ten-agent final used three seeds, both seats and six games per pairing
(270 games, zero errors). C92 ranked first at **37-4, BT 1876**, ahead of
C90/C91 (both BT 1839), C72 (1784), C89 (1761), C70/C71 (1611), C45 (1239),
C27 (945) and C88 (495). Combining that tournament with the two 100-game
direct gates gives C92 **BT 1973** versus **1810** for C90/C91.

The general lesson is narrow: remove weeds with truly spare labor when the tile
has future value, and interrupt a route only when the weed is blocking a
productive action now. "Clear every weed" was never the policy.


## 13. The fourth quadrant: a broad negative result

The south-east parcel costs **4,000 coins**. I tested three implementation
families rather than treating one bad schedule as decisive:

1. **Paid-slack parcel:** buy SE on days 14, 16, 18 or 20 and use only hands
   whose remaining route is `PASS` on compact 6-12 tile wheat/strawberry plots.
2. **Dedicated crew:** add one or two hands for 4-8 SE tiles.
3. **Seasonal setup crew:** hire an extra hand only when planting is required,
   then let ordinary paid slack water and harvest.

Expansion was also gated by score state: always, only when behind, only when
not ahead, or in response to the opponent's fourth parcel. As an external
check, three productive public Seb trajectories were included; they end near
9-10 cows, 11-13 sheep, four quadrants and 12 hands.

### 13.1 What survived the broad screen

Five seeds, both seats, 450 games: every new four-quadrant variant lost
**10-0 to C92**. The least-bad design was early compact wheat.

| Agent | Screen BT | Mean margin vs C92 |
| --- | ---: | ---: |
| C92 | 2039 | — |
| C89 | 1939 | — |
| C72 | 1900 | — |
| early six-tile wheat | **1724** | **-3,687** |
| catch-up-gated wheat | 1592 | -3,668 |
| day-16 eight-tile wheat | 1494 | -3,721 |
| day-18 strawberry | 521 | -4,643 |

The three fully productive Seb routes also lost 10-0 to C92, by mean margins
of **14,608**, **29,016** and **36,980**. The negative result is therefore not
just a flaw in the experimental scheduler.

### 13.2 Why expansion fails in this meta

- Reusable hands become idle too late: they can reach SE, but often cannot
  plant and water before the day refresh.
- Extra crew costs more than incremental output and can disrupt feed finance;
  one diagnostic cow died unfed at step 408.
- Unlocking SE exposes 25 more empty tiles to random weed spawns.
- More strawberry, wool and livestock deepen shared-market glut. Wheat is
  safer, but a small unfertilized block rarely repays land and travel.
- The 4,000-coin purchase looks like falling behind to a score-conditioned
  router. Suppressing that false signal helped, but did not make SE pay.

C93 freezes the least-bad six-tile wheat version. On fresh paired-seat seeds it
went **0-40** vs C92 (mean **-3,885**), **3-37** vs C72 (-3,077), and **3-37**
vs C89 (-3,072). In the final eleven-agent tournament it ranked eighth at
**24-36, BT 1523**; C92 again ranked first at **43-4, BT 1898**. C93 still beat
C45, C27 and C88 6-0 each, but lost to every current upper-tier agent.

This is why the selection target matters. C93's absolute bank is respectable,
but it loses close games consistently. Opponent-aware win-probability
maximization rejects the fourth quadrant even though "more productive land"
looks attractive in isolation.


## 14. Exact C92 artifact selected by the final gate

This cell embeds the frozen `c92_weed_route_repair` source, writes it to
`/kaggle/working/main.py`, packages `submission.tar.gz`, imports that generated
file, and runs a smoke game.

| Field | Value |
| --- | --- |
| Base | C91 future-use guarded idle cleanup |
| New behavior | repair a weed-blocked productive route action and resync at `PASS` |
| 100-game gate vs C91 | **22-6-72**, +446.6 mean margin |
| 100-game gate vs C90 | **22-6-72**, +388.1 mean margin |
| Ten-agent final | **rank 1, 37-4, BT 1876** |
| Exact `main.py` SHA-256 | `7b13e69371509fe53f1dbb7b769d73f6c82ff41db37df7a9a3a1879e82ed82f2` |
| Kaggle competition submission | **not submitted** |

### File-runner compatibility note

`kaggle-environments` executes a submitted Python file by selecting the last
newly bound callable in its namespace. A source file can therefore work when
imported as `module.agent` yet silently run a helper when supplied as a file
path. The packaged C92 ends with a fresh `kaggle_submission_agent` binding, and
the validation uses the exact file-path interface used for submissions. This
guard is part of the SHA-256 above.

Building and publishing this notebook version is deliberately separate from
submitting the generated archive to the competition.


### [CODE]import base64
import hashlib
import tarfile
import zlib
from pathlib import Path

WORK = Path("/kaggle/working")
if not WORK.exists():
    WORK = Path.cwd()

MAIN_PATH = WORK / "main.py"
ARCHIVE_PATH = WORK / "submission.tar.gz"

# Exact frozen C92 source. Compression only keeps the notebook readable.
_AGENT_B64_PARTS = [
    "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"
    "YS+5PMc5Z3MJilpN1Crb0gVdp66iN5drTOf2GsaMi6lCWKSj4+4yVJMys6kQSRbRhlk9e8tk7CIDb9dVy5ZIcye9so4WXtsCrCRu"
    "tS7pgtujRtThvhYPW+pTb9c/yvCzSDdFuUZpc6dw9mxQjIrVKmp9nxg7vYmsWnZEZiBuLh2mh2G4yeC7wqjUP9n58mF8KdWtEc7J"
    "ePLl3qZs8fPmTX1TJpIL9VSmp+aRerSokUw7WDt7kqVENHqpTzzToc3v4k9pFvckq6FOcrZ3drx7jlK7lMu1HBfntbTaEr0ychVj"
    "iYWvlfATKrl2R+28K+O7qBO5sfABxbI8OGrX41BFFd9ZiikD72Qvj6wHxsF41zhlJTp7y3YRX0yv1nP+ejm6pJqn4i4WjrXZOha6"
    "pNxETSF75rorkF8z6NTi8bsY67mRtjTigOktOaElDnN+b4oLh5ZOj8e+KI3lUdjuCw932UzS7Yrki+bNqHxeHm2p0lwIyoOSFKtj"
    "oYEamLZsmVHcjUkrZkNi46j3WHFsqcIAZRR/JJyyeiI0DuIZn98ypvqdTrmcDWePXoKR64lxfVtvKzOLEj8musk24M8WWbxurSKz"
    "PuedEhUZ5MbDCe/ueudBC25bsw71nA7ninY27mwSEl5nFo05kgjuq2dHa8fb5qfhZaz490E+6kvRxQHnTBUXAh9JVisjMmj17QjO"
    "1k2Wrm6Hq9/JbtzMflGNRlqWypINTpn1ftwr+5Ni+uKITpFdaldvdAl0FJ0Ju06GVlcHsrEKO31b2ceOd5dcsVQ+ZDrmGnvuqOgy"
    "WfJTgHFwonxk+7n0gsDyJGWViApY70JVzpRr16JnU92uETLTqeJMozuNOoLmUyE1mg2VmujPsGhleUktY5XNtdqb0vUmLjZj5QlT"
    "bGJxtM+X+97MuN5dZ3MHdz2+LO9inmawLufKMYRTE2vCTp22Lc/Kg1+tazVcXQUbEpNAk5ivx0wEn0imT/gUVeeqdNz7MJdNEsbm"
    "pq2O47NsdLIlW8N868iUFoc5YllniLJ7Eg7k8wvxCkL++mImNBez7j6HCRduP1gR2S268haaaMZZau1p88bq7pZyaVdPndixUc1N"
    "IfsxF/Kc7F2XjwmXRSZuS3CnEZ88dIKB1brhsgQvTt+4O2tP9/w4hLQzlrq0UgXSH/R3T6EKv8xYRi0Ec/jb8tzbPQVGsWpBcIxo"
    "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"
    "sHvMZxTgW8Mp8BOC9+U3cAWlRdagZo+WH5XrKK7TIwby3eMDfvUveWcjqCifzLIzP3XXP1K3r1gb15zeEj8p5hbqUtwVr2fI3wQU"
    "NQHPeVgW9Co+ttRKQVYk6xXw7b8g0CpeP9VS8s+xufuQ88t+dGcF3tmnC8A4KosWOTusNsffywomu27VroLn4rRH4sFFpXteCiIB"
    "25z+dARdFmG4tphqz3TrsfryMgN9cE2Lcmvutx322kdxOCLqx55u+OWooUx3sHRS6Fr7tnA0/yA1ZkAow5IaZmCtb77DSwUYpTXg"
    "YY5q66enEMfgcoZ792ZJ1x9nTJWV3X35Ik3h1JlG/nINEl7k/AR+aJL9xZoZ/rqc6/W6DNttQ5fOUp5pn4/Wt99L9Igeb6cdFD71"
    "ZCyIf7I3e1O2Jz6vP5b1bnVijzUT8i31Zi2hlqpJhjuCOpEvl+UL30hcB6UI2xz8crz92JalxxHkyhCbqHopBITUGOVdWHGj133P"
    "y+9pNEuD1rzW/3E+Jf6FqyX6V8uSMtVuKT7UvuXeud7w/CpfkrTl2QnDRaRRPudCOpn6bWiwOM9YykORDzjLSOop3JZs81JF+g2L"
    "w+96M5PU2bBRyNX2fnXeqJ7Iz4miTrUC+/F4DrMyvG77fX9w7io1/I+YXNjg+YcMVXl0M0ilT2qe61j9uy5Mjanri4pLfY/b1Igr"
    "35i/d+bNuaj0n+UrN1b7MHrQzV96WO/I9AUNZU8ROIM/y3ad76mLnk23WAAcTejN/BLdXrNlZIdUJ2dScCFVqrSTfvq3lXLyMs3p"
    "+J1Bk+XXUD0b1C4DJOm2V/xpE3jZ7fGq8nhSz3fN8NhYjW2CFGuwPO3Vavu8Iweg82w0V6P1g93i21ntellp3V1yoB6FmSosMj70"
    "dPEjzBr6bEG++KDQLToEe51Bom5xas9XRnSSnKEzdQA7+mqO97/jAFqMnw5+VB3h6bTSV81nt57ZozV+iI+cWWM59bWDB4dc9SRV"
    "2zLIPSYGseMtm/9MugjaGJ/p6QJc3BJ7/MqitnhfvukpOHextfuGa9vJOupk8k8dep771ub16WYcX/74sYpwRB1L+JyL9XXD3sj4"
    "czZLG8s5vxqp52aJXuF+2Twb2PZ1Ll5WC75t8zq5Nq7RdXEctFJwdOL6zbH7G2iTzSJx+kw0/9ZHdgNWcOdJULvsnbXgKTfMn7L6"
    "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"
    "QVOg"
]
_AGENT_B64 = "".join(_AGENT_B64_PARTS)
EXPECTED_MAIN_SHA256 = "7b13e69371509fe53f1dbb7b769d73f6c82ff41db37df7a9a3a1879e82ed82f2"
EXPECTED_MAIN_BYTES = 70317
BEST_LABEL = "c92_weed_route_repair"
BEST_PUBLIC_SCORE = "not submitted; selected by local opponent-aware gates"

raw = zlib.decompress(base64.b64decode(_AGENT_B64.encode("ascii")))
assert len(raw) == EXPECTED_MAIN_BYTES, (len(raw), EXPECTED_MAIN_BYTES)
digest = hashlib.sha256(raw).hexdigest()
assert digest == EXPECTED_MAIN_SHA256, (digest, EXPECTED_MAIN_SHA256)
assert b"def agent" in raw, "agent() missing from payload"

MAIN_PATH.write_bytes(raw)
compile(raw, str(MAIN_PATH), "exec")

with tarfile.open(ARCHIVE_PATH, "w:gz") as archive:
    archive.add(MAIN_PATH, arcname="main.py")
with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
    members = archive.getnames()
assert members == ["main.py"], members

from kaggle_environments import make

env = make(
    "kaggriculture",
    configuration={"episodeSteps": 720, "seed": 0},
    debug=False,
)
env.run([str(MAIN_PATH), "starter"])
status = [row["status"] for row in env.steps[-1]]
rewards = [row["reward"] for row in env.steps[-1]]
first_action = env.steps[1][0]["action"]
assert first_action.get("market"), first_action
assert rewards[0] > 3000, rewards

print(
    {
        "selected": BEST_LABEL,
        "ladder_publicScore_reference": BEST_PUBLIC_SCORE,
        "main_py": str(MAIN_PATH),
        "main_bytes": MAIN_PATH.stat().st_size,
        "main_sha256": digest,
        "submission": str(ARCHIVE_PATH),
        "submission_bytes": ARCHIVE_PATH.stat().st_size,
        "archive_members": members,
        "first_action": first_action,
        "smoke_vs_starter_status": status,
        "smoke_vs_starter_rewards": rewards,
        "note": "This cell only builds files. It does not submit them.",
    }
)


## 15. Live C92 losses: production was not the remaining problem

C92's public score reached **2836.8**, so I downloaded every
available public match rather than guessing from the score. The
captured set contained **103 games: 72 wins and 31 losses**.
The repeated failure modes were in the shared market, not in a
missing crop, animal or fourth parcel.

### 15.1 Opening feed denial

Four large losses shared one mechanism. The opponent bought
**14-19 wheat** before C92's slot-eight order to buy five wheat.
The higher shared price left enough cash for only four units.
C92 still attempted five feeds; one sheep remained unfed and
disappeared on day 2. Those four losses averaged **-13,606**.

Buying more wheat was not automatically better. Moving exactly
the existing five-unit order to slot zero worked; buying six
regressed against established agents. Buying 14 or 19 and
reselling the surplus was a profitable-looking exploit, but it
became sharply vulnerable to another public route family.

### 15.2 One-turn fertilizer preemption

Eleven losses shared the same field tape hash. Nearly identical
routes won when their market timing was ordinary, but lost when
the opponent sold fertilizer or wheat exactly one turn before
C92's batch. Production quantities were unchanged; order alone
reversed the matchup by roughly **5,300-5,700 coins**.

The safe response is a conservation rule: move part of an
already-planned sale forward, then subtract exactly the moved
quantity from the following turn. That protects ordering without
inventing more liquidation or changing field work.


## 16. C94: protect feed first, advance only fertilizer

I screened complete market-tape grafts, five/ six/ 14/ 19-unit
wheat openings, premium-product splits, wheat and fertilizer
splits, late-only timing, two-turn anticipation and gates based
on whether the opponent resembled our route. The experiments used
both seats and new seeds throughout.

| Candidate idea | What happened |
| --- | --- |
| Buy exactly five wheat first | Fixed every sampled feed-denial route |
| Buy six wheat first | Regressed to 0-4 against several established agents |
| Buy 14/19, resell surplus | Strong exploit but brittle against Kaito's route |
| Copy a full rival market tape | Large generalization failure |
| Split premium products | Did not address the observed counters |
| Predict two turns ahead | Fell to 2-2 against C92 |
| Clone-confidence gate | Suppressed useful moves without improving robustness |
| One-turn fertilizer split, cap ten | Best opponent-aware result |

The held-out validation used **900 games over six new seeds**.

| Variant | Record | Win rate |
| --- | ---: | ---: |
| five wheat first only | 173-7 | 96.1% |
| aggressive wheat + fertilizer split | 168-12 | 93.3% |
| wheat 10 + fertilizer 5 caps | 174-6 | 96.7% |
| **fertilizer only, cap 10** | **174-6** | **96.7%** |
| split only after turn 480 | 173-7 | 96.1% |

The tied finalists then played in the final tournament. The
fertilizer-only version beat the wheat+fertilizer version
**6-0**, despite a mean margin of only 27. That is exactly the
distinction this notebook targets: maximize the chance of
winning the matchup, not the size of an already-won bank.


## 17. Final tournament and Bradley-Terry

Eighteen agents played every other agent six times: three seeds,
both seats, **918 games and zero failures**. The field included
C70-C92 plus reconstructed public live strategies. Bradley-Terry
was fitted to head-to-head results rather than coin magnitude.

| Rank | Agent | W-L | Win rate | Bradley-Terry |
| ---: | --- | ---: | ---: | ---: |
| 1 | **C94 fertilizer-only** | **88-14** | **86.3%** | **1837** |
| 2 | live Huyimin reconstruction | 84-18 | 82.4% | 1798 |
| 3 | wheat+fertilizer capped | 82-20 | 80.4% | 1779 |
| 4 | live Kaito reconstruction | 76-26 | 74.5% | 1724 |
| 5 | five-wheat-first only | 75-27 | 73.5% | 1714 |
| 12-14 | C90 / C91 / C92 | 28-55 each | 33.7% | 1380 |

C94 beat C90, C91 and C92 **6-0 each** in this block. Across the
broad screen, tuning, held-out validation and final tournament,
the search ran **3,214 local games with zero failures**.

These are simulator results, not a leaderboard claim. The live
rivals are exact public action reconstructions and may not expose
every branch of their original policies. A Kaggle submission is
still the only test of the evolving public population.


## 18. Exact C94 artifact selected by the final gate

C94 keeps C92's crops, animals, weed repair, routing, hiring and
expansion schedule unchanged. It adds only two bounded market
changes:

1. move the existing purchase of exactly five wheat to the first
   market slot on turn zero;
2. when C92 will sell fertilizer next turn, sell at most ten
   units now and subtract the same amount from the next sale.

| Field | Value |
| --- | --- |
| Base | C92 productive-route weed repair |
| Held-out cross-play | **174-6**, 96.7% |
| Eighteen-agent final | **rank 1, 88-14, BT 1837** |
| Exact `main.py` SHA-256 | `7b0e5a7b9d18dc583f5789e50a54dca43561f6d08c1c616b4219bf50bcb8311f` |
| Kaggle competition submission | **not submitted** |

The next cell writes `main.py` and `submission.tar.gz` and tests
Kaggle's file-path loader. It contains no upload or competition
submission call.


### [CODE]import base64
import hashlib
import tarfile
import zlib
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

WORK = Path("/kaggle/working")
if not WORK.exists():
    WORK = Path.cwd()

MAIN_PATH = WORK / "main.py"
ARCHIVE_PATH = WORK / "submission.tar.gz"

# Exact frozen C94 source. Compression only keeps the notebook readable.
_AGENT_B64_PARTS = [
        "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"
"YS+5PMc5Z3MJilpN1Crb0gVdp66iN5drTOf2GsaMi6lCWKSj4+4yVJMys6kQSRbRhlk9e8tk7CIDb9dVy5ZIcye9so4WXtsCrCRu"
"tS7pgtujRtThvhYPW+pTb9c/yvCzSDdFuUZpc6dw9mxQjIrVKmp9nxg7vYmsWnZEZiBuLh2mh2G4yeC7wqjUP9n58mF8KdWtEc7J"
"ePLl3qZs8fPmTX1TJpIL9VSmp+aRerSokUw7WDt7kqVENHqpTzzToc3v4k9pFvckq6FOcrZ3drx7jlK7lMu1HBfntbTaEr0ychVj"
"iYWvlfATKrl2R+28K+O7qBO5sfABxbI8OGrX41BFFd9ZiikD72Qvj6wHxsF41zhlJTp7y3YRX0yv1nP+ejm6pJqn4i4WjrXZOha6"
"pNxETSF75rorkF8z6NTi8bsY67mRtjTigOktOaElDnN+b4oLh5ZOj8e+KI3lUdjuCw932UzS7Yrki+bNqHxeHm2p0lwIyoOSFKtj"
"oYEamLZsmVHcjUkrZkNi46j3WHFsqcIAZRR/JJyyeiI0DuIZn98ypvqdTrmcDWePXoKR64lxfVtvKzOLEj8musk24M8WWbxurSKz"
"PuedEhUZ5MbDCe/ueudBC25bsw71nA7ninY27mwSEl5nFo05kgjuq2dHa8fb5qfhZaz490E+6kvRxQHnTBUXAh9JVisjMmj17QjO"
"1k2Wrm6Hq9/JbtzMflGNRlqWypINTpn1ftwr+5Ni+uKITpFdaldvdAl0FJ0Ju06GVlcHsrEKO31b2ceOd5dcsVQ+ZDrmGnvuqOgy"
"WfJTgHFwonxk+7n0gsDyJGWViApY70JVzpRr16JnU92uETLTqeJMozuNOoLmUyE1mg2VmujPsGhleUktY5XNtdqb0vUmLjZj5QlT"
"bGJxtM+X+97MuN5dZ3MHdz2+LO9inmawLufKMYRTE2vCTp22Lc/Kg1+tazVcXQUbEpNAk5ivx0wEn0imT/gUVeeqdNz7MJdNEsbm"
"pq2O47NsdLIlW8N868iUFoc5YllniLJ7Eg7k8wvxCkL++mImNBez7j6HCRduP1gR2S268haaaMZZau1p88bq7pZyaVdPndixUc1N"
"IfsxF/Kc7F2XjwmXRSZuS3CnEZ88dIKB1brhsgQvTt+4O2tP9/w4hLQzlrq0UgXSH/R3T6EKv8xYRi0Ec/jb8tzbPQVGsWpBcIxo"
"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"
"sHvMZxTgW8Mp8BOC9+U3cAWlRdagZo+WH5XrKK7TIwby3eMDfvUveWcjqCifzLIzP3XXP1K3r1gb15zeEj8p5hbqUtwVr2fI3wQU"
"NQHPeVgW9Co+ttRKQVYk6xXw7b8g0CpeP9VS8s+xufuQ88t+dGcF3tmnC8A4KosWOTusNsffywomu27VroLn4rRH4sFFpXteCiIB"
"25z+dARdFmG4tphqz3TrsfryMgN9cE2Lcmvutx322kdxOCLqx55u+OWooUx3sHRS6Fr7tnA0/yA1ZkAow5IaZmCtb77DSwUYpTXg"
"YY5q66enEMfgcoZ792ZJ1x9nTJWV3X35Ik3h1JlG/nINEl7k/AR+aJL9xZoZ/rqc6/W6DNttQ5fOUp5pn4/Wt99L9Igeb6cdFD71"
"ZCyIf7I3e1O2Jz6vP5b1bnVijzUT8i31Zi2hlqpJhjuCOpEvl+UL30hcB6UI2xz8crz92JalxxHkyhCbqHopBITUGOVdWHGj133P"
"y+9pNEuD1rzW/3E+Jf6FqyX6V8uSMtVuKT7UvuXeud7w/CpfkrTl2QnDRaRRPudCOpn6bWiwOM9YykORDzjLSOop3JZs81JF+g2L"
"w+96M5PU2bBRyNX2fnXeqJ7Iz4miTrUC+/F4DrMyvG77fX9w7io1/I+YXNjg+YcMVXl0M0ilT2qe61j9uy5Mjanri4pLfY/b1Igr"
"35i/d+bNuaj0n+UrN1b7MHrQzV96WO/I9AUNZU8ROIM/y3ad76mLnk23WAAcTejN/BLdXrNlZIdUJ2dScCFVqrSTfvq3lXLyMs3p"
"+J1Bk+XXUD0b1C4DJOm2V/xpE3jZ7fGq8nhSz3fN8NhYjW2CFGuwPO3Vavu8Iweg82w0V6P1g93i21ntellp3V1yoB6FmSosMj70"
"dPEjzBr6bEG++KDQLToEe51Bom5xas9XRnSSnKEzdQA7+mqO97/jAFqMnw5+VB3h6bTSV81nt57ZozV+iI+cWWM59bWDB4dc9SRV"
"2zLIPSYGseMtm/9MugjaGJ/p6QJc3BJ7/MqitnhfvukpOHextfuGa9vJOupk8k8dep771ub16WYcX/74sYpwRB1L+JyL9XXD3sj4"
"czZLG8s5vxqp52aJXuF+2Twb2PZ1Ll5WC75t8zq5Nq7RdXEctFJwdOL6zbH7G2iTzSJx+kw0/9ZHdgNWcOdJULvsnbXgKTfMn7L6"
"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"
]
EXPECTED_MAIN_SHA256 = "7b0e5a7b9d18dc583f5789e50a54dca43561f6d08c1c616b4219bf50bcb8311f"
EXPECTED_MAIN_BYTES = 75078
BEST_LABEL = "c94_feed_first_fert_split"
BEST_PUBLIC_SCORE = "not submitted; local experiments only"

raw = zlib.decompress(base64.b64decode("".join(_AGENT_B64_PARTS)))
assert len(raw) == EXPECTED_MAIN_BYTES
digest = hashlib.sha256(raw).hexdigest()
assert digest == EXPECTED_MAIN_SHA256
compile(raw, str(MAIN_PATH), "exec")
MAIN_PATH.write_bytes(raw)

with tarfile.open(ARCHIVE_PATH, "w:gz") as archive:
    archive.add(MAIN_PATH, arcname="main.py")
with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
    members = archive.getnames()
assert members == ["main.py"]

selected_callable = get_last_callable(raw.decode("utf-8"), path=str(MAIN_PATH))
assert selected_callable.__name__ == "c94_submission_agent"

# Use the file path, matching Kaggle's submitted-file loading behavior.
env = make(
    "kaggriculture",
    configuration={"episodeSteps": 720, "seed": 4_600_000},
    debug=False,
)
env.run([str(MAIN_PATH), "starter"])
final = env.steps[-1]
statuses = [state.status for state in final]
rewards = [state.reward for state in final]
assert statuses == ["DONE", "DONE"]

print({
    "selected": BEST_LABEL,
    "public_score": BEST_PUBLIC_SCORE,
    "main_py": str(MAIN_PATH),
    "main_bytes": len(raw),
    "main_sha256": digest,
    "submission": str(ARCHIVE_PATH),
    "archive_members": members,
    "file_runner_callable": selected_callable.__name__,
    "smoke_status": statuses,
    "smoke_rewards": rewards,
    "note": "This cell only builds files. It does not submit them.",
})


### Preparing the archive without submitting it

Run all cells and check that the final output reports
`archive_members: ['main.py']`, file-runner callable
`c94_submission_agent`, SHA-256
`7b0e5a7b9d18dc583f5789e50a54dca43561f6d08c1c616b4219bf50bcb8311f`,
and smoke statuses of `DONE`.

This notebook remains public and does not call the Kaggle
competition submission API. The generated archive is prepared
for inspection only; no competition submission is made.


## 19. C95: adapt to the refreshed top-20 market rhythm

A new 100-replay refresh showed that the leading policies now
share almost the same public farm route. Their important
differences are sale timing and private inventory, so copying a
field layer or an isolated rival market tape is not coherent.

C95 keeps C94's route and feed-first opening. It pulls forward at
most **10 wheat and 5 fertilizer** from a sale already scheduled
for the next turn, then removes the same quantity from that later
sale. This changes timing without creating inventory or altering
total liquidation.

| Held-out test | C95 | C94 |
| --- | ---: | ---: |
| Refreshed top-20 medoids, 120 games | **112-8** | 111-9 |
| Win rate | **93.3%** | 92.5% |

Across eight additional seeds and both seats, C95 improved mean
margin against Kaito, Ueddy, JALKARNA and Efe by **72-94 coins**
each. C94 remains the safer general baseline; C95 is the selected
response to the current leaderboard population.

Exact `main.py` SHA-256: `489f5d197527f107027626cce79d850fd2ca90edd43d94384b849b6511e27bdb`.


### [CODE]import base64
import hashlib
import tarfile
import zlib
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

WORK = Path("/kaggle/working")
if not WORK.exists():
    WORK = Path.cwd()

MAIN_PATH = WORK / "main.py"
ARCHIVE_PATH = WORK / "submission.tar.gz"

# Exact frozen C95 source. Compression only keeps the notebook readable.
_C95_AGENT_B64_PARTS = [
        "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"
"YS+5PMc5Z3MJilpN1Crb0gVdp66iN5drTOf2GsaMi6lCWKSj4+4yVJMys6kQSRbRhlk9e8tk7CIDb9dVy5ZIcye9so4WXtsCrCRu"
"tS7pgtujRtThvhYPW+pTb9c/yvCzSDdFuUZpc6dw9mxQjIrVKmp9nxg7vYmsWnZEZiBuLh2mh2G4yeC7wqjUP9n58mF8KdWtEc7J"
"ePLl3qZs8fPmTX1TJpIL9VSmp+aRerSokUw7WDt7kqVENHqpTzzToc3v4k9pFvckq6FOcrZ3drx7jlK7lMu1HBfntbTaEr0ychVj"
"iYWvlfATKrl2R+28K+O7qBO5sfABxbI8OGrX41BFFd9ZiikD72Qvj6wHxsF41zhlJTp7y3YRX0yv1nP+ejm6pJqn4i4WjrXZOha6"
"pNxETSF75rorkF8z6NTi8bsY67mRtjTigOktOaElDnN+b4oLh5ZOj8e+KI3lUdjuCw932UzS7Yrki+bNqHxeHm2p0lwIyoOSFKtj"
"oYEamLZsmVHcjUkrZkNi46j3WHFsqcIAZRR/JJyyeiI0DuIZn98ypvqdTrmcDWePXoKR64lxfVtvKzOLEj8musk24M8WWbxurSKz"
"PuedEhUZ5MbDCe/ueudBC25bsw71nA7ninY27mwSEl5nFo05kgjuq2dHa8fb5qfhZaz490E+6kvRxQHnTBUXAh9JVisjMmj17QjO"
"1k2Wrm6Hq9/JbtzMflGNRlqWypINTpn1ftwr+5Ni+uKITpFdaldvdAl0FJ0Ju06GVlcHsrEKO31b2ceOd5dcsVQ+ZDrmGnvuqOgy"
"WfJTgHFwonxk+7n0gsDyJGWViApY70JVzpRr16JnU92uETLTqeJMozuNOoLmUyE1mg2VmujPsGhleUktY5XNtdqb0vUmLjZj5QlT"
"bGJxtM+X+97MuN5dZ3MHdz2+LO9inmawLufKMYRTE2vCTp22Lc/Kg1+tazVcXQUbEpNAk5ivx0wEn0imT/gUVeeqdNz7MJdNEsbm"
"pq2O47NsdLIlW8N868iUFoc5YllniLJ7Eg7k8wvxCkL++mImNBez7j6HCRduP1gR2S268haaaMZZau1p88bq7pZyaVdPndixUc1N"
"IfsxF/Kc7F2XjwmXRSZuS3CnEZ88dIKB1brhsgQvTt+4O2tP9/w4hLQzlrq0UgXSH/R3T6EKv8xYRi0Ec/jb8tzbPQVGsWpBcIxo"
"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"
"sHvMZxTgW8Mp8BOC9+U3cAWlRdagZo+WH5XrKK7TIwby3eMDfvUveWcjqCifzLIzP3XXP1K3r1gb15zeEj8p5hbqUtwVr2fI3wQU"
"NQHPeVgW9Co+ttRKQVYk6xXw7b8g0CpeP9VS8s+xufuQ88t+dGcF3tmnC8A4KosWOTusNsffywomu27VroLn4rRH4sFFpXteCiIB"
"25z+dARdFmG4tphqz3TrsfryMgN9cE2Lcmvutx322kdxOCLqx55u+OWooUx3sHRS6Fr7tnA0/yA1ZkAow5IaZmCtb77DSwUYpTXg"
"YY5q66enEMfgcoZ792ZJ1x9nTJWV3X35Ik3h1JlG/nINEl7k/AR+aJL9xZoZ/rqc6/W6DNttQ5fOUp5pn4/Wt99L9Igeb6cdFD71"
"ZCyIf7I3e1O2Jz6vP5b1bnVijzUT8i31Zi2hlqpJhjuCOpEvl+UL30hcB6UI2xz8crz92JalxxHkyhCbqHopBITUGOVdWHGj133P"
"y+9pNEuD1rzW/3E+Jf6FqyX6V8uSMtVuKT7UvuXeud7w/CpfkrTl2QnDRaRRPudCOpn6bWiwOM9YykORDzjLSOop3JZs81JF+g2L"
"w+96M5PU2bBRyNX2fnXeqJ7Iz4miTrUC+/F4DrMyvG77fX9w7io1/I+YXNjg+YcMVXl0M0ilT2qe61j9uy5Mjanri4pLfY/b1Igr"
"35i/d+bNuaj0n+UrN1b7MHrQzV96WO/I9AUNZU8ROIM/y3ad76mLnk23WAAcTejN/BLdXrNlZIdUJ2dScCFVqrSTfvq3lXLyMs3p"
"+J1Bk+XXUD0b1C4DJOm2V/xpE3jZ7fGq8nhSz3fN8NhYjW2CFGuwPO3Vavu8Iweg82w0V6P1g93i21ntellp3V1yoB6FmSosMj70"
"dPEjzBr6bEG++KDQLToEe51Bom5xas9XRnSSnKEzdQA7+mqO97/jAFqMnw5+VB3h6bTSV81nt57ZozV+iI+cWWM59bWDB4dc9SRV"
"2zLIPSYGseMtm/9MugjaGJ/p6QJc3BJ7/MqitnhfvukpOHextfuGa9vJOupk8k8dep771ub16WYcX/74sYpwRB1L+JyL9XXD3sj4"
"czZLG8s5vxqp52aJXuF+2Twb2PZ1Ll5WC75t8zq5Nq7RdXEctFJwdOL6zbH7G2iTzSJx+kw0/9ZHdgNWcOdJULvsnbXgKTfMn7L6"
"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"
]
EXPECTED_C95_SHA256 = "489f5d197527f107027626cce79d850fd2ca90edd43d94384b849b6511e27bdb"
EXPECTED_C95_BYTES = 75098
BEST_LABEL = "c95_top20_wheat_counter"

raw = zlib.decompress(base64.b64decode("".join(_C95_AGENT_B64_PARTS)))
assert len(raw) == EXPECTED_C95_BYTES
digest = hashlib.sha256(raw).hexdigest()
assert digest == EXPECTED_C95_SHA256
compile(raw, str(MAIN_PATH), "exec")
MAIN_PATH.write_bytes(raw)

with tarfile.open(ARCHIVE_PATH, "w:gz") as archive:
    archive.add(MAIN_PATH, arcname="main.py")
with tarfile.open(ARCHIVE_PATH, "r:gz") as archive:
    members = archive.getnames()
assert members == ["main.py"]

selected_callable = get_last_callable(raw.decode("utf-8"), path=str(MAIN_PATH))
assert selected_callable.__name__ == "c94_submission_agent"

env = make(
    "kaggriculture",
    configuration={"episodeSteps": 720, "seed": 18_590_000},
    debug=False,
)
env.run([str(MAIN_PATH), "starter"])
final = env.steps[-1]
statuses = [state.status for state in final]
rewards = [state.reward for state in final]
assert statuses == ["DONE", "DONE"]

print({
    "selected": BEST_LABEL,
    "main_bytes": len(raw),
    "main_sha256": digest,
    "submission": str(ARCHIVE_PATH),
    "archive_members": members,
    "file_runner_callable": selected_callable.__name__,
    "smoke_status": statuses,
    "smoke_rewards": rewards,
})


### C95 submission artifact

The preceding cell is intentionally last: it overwrites the
earlier C94 files with the exact C95 `main.py` and rebuilds
`submission.tar.gz`. The SHA assertion and file-path smoke test
must pass before this notebook version is submitted.
