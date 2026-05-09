# Future Plans

This document captures potential feature additions for `nano-tele`, based on the current codebase and runtime design.

## Current Baseline

The project already supports:

- Telegram + Nanobot gateway.
- Deterministic perfume recommendation logic.
- Weather-based bucket classification.
- Occasion inference.
- Same-day/history rotation.
- Feedback-aware ranking.
- Travel mode.
- Collection list/add/remove.
- Recommendation history and stats.
- Runtime prompt files for Nanobot.
- Unit tests for core deterministic behavior.

The best future additions should preserve the key project rules:

- Recommendations must stay deterministic where possible.
- Recommendations must remain collection-only.
- Weather data should not be invented.
- The Python tool should remain the canonical recommendation engine.

---

## Phase 1: High-Impact User Features

### 1. Explanation Mode

Add support for questions like:

```text
/why
why this one?
why did you choose Imagination?
```

Example response:

```text
I picked **Imagination** because:
• Weather: Mild, 18°C, 55% humidity
• Occasion: Office
• Match: clean citrus aromatic profile
• Rotation: avoided yesterday’s pick
• Feedback: you have rated it positively before
```

Implementation notes:

- Add a structured explanation object to recommendation results.
- Capture weather bucket, occasion, ranking position, feedback score, and rotation reason.
- Persist the latest explanation to `workspace/memory/LAST_PICK.json`.
- Update routing in `workspace/tools/perfume_tool.py` and `workspace/tools/perfume`.
- Add unit tests for explanation generation and last-pick persistence.

Priority: High  
Effort: Medium

### 2. Tomorrow Forecast Recommendation

Add support for:

```text
/tomorrow
/tomorrow office
what should I wear tomorrow in London?
```

Implementation notes:

- Extend weather lookup to support `day_offset=0 | 1`.
- Use Open-Meteo forecast data in the canonical Python tool.
- Pick representative forecast times by occasion:
  - Office: working hours.
  - Daytime: midday.
  - Evening/date: evening window.
- Add CLI support such as `recommend --day tomorrow`.
- Ensure shell wrapper behavior stays compatible.

Priority: High  
Effort: Medium

### 3. Recommendation Confidence Score

Add a small confidence indicator to recommendation output.

Example:

```text
🌤️ Sheffield: 18°C, partly cloudy, 55% humidity
💨 Wear **Imagination by Louis Vuitton** — clean citrus aromatic brightness.
Confidence: High
```

Confidence can consider:

- Live weather availability.
- Exact weather bucket match.
- Exact occasion match.
- Feedback score.
- Rotation constraints.
- Number of available ranked candidates.

Priority: High  
Effort: Low-Medium

### 4. Temporary Avoid/Skip Command

Add support for:

```text
avoid Sauvage today
don’t recommend Erba Pura today
skip Le Beau
```

Implementation notes:

- Store temporary exclusions in `workspace/data/preferences.json`.
- Expire exclusions automatically by date.
- Recommendation selection should skip excluded perfumes when alternatives exist.

Example storage:

```json
{
  "daily_exclusions": {
    "2026-05-09": ["Sauvage", "Erba Pura"]
  }
}
```

Priority: High  
Effort: Medium

---

## Phase 2: Personalization Features

### 5. Scent Strength, Projection, and Longevity

Add fragrance metadata such as:

```json
{
  "projection": "soft",
  "longevity": "long",
  "sweetness": 2,
  "freshness": 5,
  "formality": 4
}
```

This enables requests like:

```text
I want something subtle
give me something strong
office-safe only
beast mode tonight
```

Priority: Very High  
Effort: Medium-High

### 6. Expanded Occasions

Support richer occasions, initially mapped to existing categories:

- Gym.
- Wedding.
- Interview.
- Flight.
- Holiday.
- Beach.
- Formal event.
- Casual errands.
- Family gathering.

Implementation notes:

- Add occasion aliases first.
- Map new occasions to existing recommendation buckets.
- Add full ranking support later if needed.

Priority: Medium-High  
Effort: Low-Medium

### 7. User Preference Profile

Allow the user to express broader preferences:

```text
I prefer fresh scents
I dislike very sweet fragrances
I want less Sauvage
I like vetiver
```

Possible storage:

```json
{
  "profile": {
    "preferred_families": ["Citrus Aromatic", "Vetiver"],
    "disliked_families": ["Very Sweet"],
    "preferred_brands": ["Louis Vuitton", "Nishane"],
    "avoid_notes": ["vanilla", "oud"]
  }
}
```

Priority: High  
Effort: Medium

### 8. Bottle Usage Tracking

Track wear count and optional bottle level.

Commands could include:

```text
I wore Imagination today
set Imagination bottle to 70%
how much have I worn Sauvage?
```

Possible storage:

```json
{
  "bottles": {
    "Imagination": {
      "size_ml": 100,
      "remaining_percent": 72,
      "wear_count": 18
    }
  }
}
```

Priority: Medium  
Effort: Medium

---

## Phase 3: Better Recommendation Intelligence

### 9. Explicit Multi-Factor Scoring Engine

Replace implicit ranking adjustments with a transparent scoring model.

Candidate score factors could include:

- Base ranking position.
- Weather match.
- Occasion match.
- Feedback score.
- Preferred family bonus.
- Disliked family penalty.
- Yesterday/same-day repeat penalty.
- Recent same-family penalty.
- Too-strong-for-office penalty.
- Too-sweet-for-hot-weather penalty.

Suggested model:

```python
@dataclass
class CandidateScore:
    fragrance: Fragrance
    score: int
    reasons: list[str]
    penalties: list[str]
```

Priority: Very High  
Effort: High

### 10. Recent-Family Rotation

Avoid recommending similar scent families too often.

Example:

- Yesterday: Imagination, Citrus Aromatic.
- Today: prefer Sauvage or Born in Roma instead of another citrus aromatic if suitable.

Priority: Medium-High  
Effort: Medium

### 11. Seasonal Intelligence

Add seasonal weighting alongside weather.

Example behavior:

- Spring/summer: fresher, citrus, aquatic.
- Autumn/winter: amber, gourmand, woody.

Priority: Medium  
Effort: Low-Medium

### 12. Time-of-Day-Aware Intensity

Improve default picks based on time:

- Morning: fresh and clean.
- Afternoon: versatile.
- Evening: deeper or stronger.
- Late night: date/evening-leaning picks.

Priority: Medium  
Effort: Low

---

## Phase 4: Telegram UX Improvements

### 13. Help and Commands Route

Add `/help` or `/commands`.

Example output:

```text
Commands:
• /today — daytime pick
• /office — work-safe pick
• /evening — evening pick
• /date — date-night pick
• /tomorrow — forecast pick
• /history — recent picks
• /stats — wear stats
• /collection — saved fragrances
```

Priority: High  
Effort: Low

### 14. Better Collection Display

Group collection output by family, weather, or occasion.

Example:

```text
Fresh / Aquatic
• French Riviera — Mancera
• Le Beau — Jean Paul Gaultier
• Cool Water — Davidoff

Woody / Aromatic
• Sauvage — Dior
• Born in Roma Uomo — Valentino
```

Potential filters:

```text
show fresh scents
show office scents
show cold weather scents
show date scents
```

Priority: Medium-High  
Effort: Low-Medium

### 15. Recommendation Alternatives

Add support for:

```text
give me another option
alternative
second choice
```

Implementation notes:

- Store last recommendation context.
- Track which candidates have already been shown.
- Return the next ranked eligible candidate.

Possible storage:

```json
{
  "last_request": {
    "city": "Sheffield",
    "bucket": "Mild",
    "occasion": "Office",
    "shown": ["Imagination"]
  }
}
```

Priority: High  
Effort: Medium

### 16. Opt-In Morning Recommendation

Use heartbeat or cron to send a daily recommendation only when explicitly enabled.

Commands:

```text
enable morning scent
disable morning scent
```

Priority: Medium  
Effort: Medium

---

## Phase 5: Data Quality Features

### 17. Fragrance Schema Validation

Add a validation command:

```bash
sh workspace/tools/perfume validate
```

Validation should check:

- Required fields exist.
- Weather buckets are known.
- Occasions are valid.
- No duplicate fragrance names exist.
- Ranking references exist in collection.
- Every fragrance appears in at least one ranking or valid fallback path.

Priority: Very High  
Effort: Medium

### 18. Ranking Consistency Checker

Add checks to verify:

- Every name in `ranking.json` exists in `fragrances.json`.
- Every weather bucket is known.
- Every occasion is known.
- No fragrance is ranked for unsupported weather unless intentionally allowed.

Priority: Very High  
Effort: Low-Medium

### 19. Data Enrichment Fields

Add optional fields to fragrance entries:

```json
{
  "notes": ["bergamot", "ambroxan", "vetiver"],
  "season": ["spring", "summer"],
  "projection": "moderate",
  "longevity": "long",
  "sweetness": 2,
  "freshness": 5,
  "formality": 3,
  "safe_blind_reach": true
}
```

Priority: High  
Effort: Medium

---

## Phase 6: Reliability and Engineering Improvements

### 20. Unify Weather Provider Behavior

Current behavior:

- `workspace/tools/perfume_tool.py` uses Open-Meteo.
- `workspace/tools/perfume` can use wttr.in as a lightweight runtime path/fallback.

Recommended direction:

- Keep Python as the canonical recommendation engine.
- Make the shell wrapper as thin as possible.
- Use wttr.in only as an emergency fallback.
- Document primary and fallback weather providers clearly.

Priority: High  
Effort: Medium

### 21. Weather Provider Abstraction

Introduce a provider interface:

```python
class WeatherProvider(Protocol):
    def get_weather(self, city: str, day: str) -> Weather:
        ...
```

Possible implementations:

- `OpenMeteoProvider`.
- `WttrProvider`.

Benefits:

- Easier testing.
- Clearer fallback behavior.
- Less duplicated shell/Python logic.

Priority: Medium-High  
Effort: High

### 22. Structured JSONL Event Log

Add structured event logging alongside Markdown logs.

Example events:

```json
{"type": "recommendation", "date": "2026-05-09", "city": "Sheffield", "perfume": "Imagination"}
{"type": "feedback", "date": "2026-05-09", "perfume": "Sauvage", "signal": "liked"}
{"type": "travel", "date": "2026-05-09", "city": "Dubai"}
```

File:

```text
workspace/memory/events.jsonl
```

Priority: Medium-High  
Effort: Medium

### 23. Better Test Coverage

Add tests for:

- `/stats` route.
- `/history` route.
- Feedback logging.
- Collection remove.
- Malformed JSON handling.
- Ranking reference validation.
- Travel clear.
- City extraction edge cases.
- Tomorrow forecast.
- Daily exclusions.
- Alternative recommendation.

Priority: Very High  
Effort: Medium

### 24. GitHub Actions CI

Add a workflow that runs:

```bash
python -m unittest discover -s tests
python -m py_compile main.py workspace/tools/perfume_tool.py
sh workspace/tools/perfume __diag
```

Priority: High  
Effort: Low

---

## Phase 7: Nice-to-Have Features

### 25. Scent Wardrobe Insights

Add a command such as:

```text
wardrobe analysis
```

Example output:

```text
Your collection leans fresh/aquatic and mild-weather friendly.

Strong areas:
• Mild daytime
• Hot humid casual
• Cold evening

Gaps:
• Formal office cold weather
• Rainy daytime subtle scent
• High-heat date scent
```

Priority: Medium  
Effort: Medium

### 26. What Should I Buy Next?

Keep this separate from daily recommendations so the bot still never recommends non-owned perfumes as wear suggestions.

Example:

```text
Your collection gap is a formal cold-weather office scent. Look for a dry woody iris or clean vetiver profile.
```

Priority: Low-Medium  
Effort: Medium

### 27. Layering Suggestions

Only suggest layering from owned fragrances.

Example:

```text
Try **Cool Water + Imagination** lightly: fresh marine base with citrus lift.
```

Safety rules:

- Avoid heavy layering in hot weather.
- Keep office layering subtle.
- Never suggest layering with fragrances outside the saved collection.

Priority: Low-Medium  
Effort: Medium

### 28. Travel Packing List

Add support for:

```text
I’m going to Dubai for 5 days
what should I pack?
```

Example output:

```text
Pack:
• French Riviera — hot daytime
• Le Beau — warm casual evenings
• Imagination — clean office/smart option
```

Priority: Medium  
Effort: Medium-High

---

## Recommended Implementation Order

1. Add `/help` command.
2. Add fragrance/ranking validation.
3. Add tomorrow recommendation.
4. Add explanation mode.
5. Add alternatives.
6. Add projection/longevity/sweetness metadata.
7. Refactor selection into explicit candidate scoring.
8. Unify weather provider behavior.
9. Add structured JSONL event logging.
10. Add GitHub Actions CI.

## Best Next Feature

The strongest next feature is an **explicit scoring engine with explanation mode**.

Why:

- It makes the bot feel smarter to the user.
- It keeps recommendation behavior deterministic and inspectable.
- It creates a foundation for preferences, alternatives, projection, seasonality, and wardrobe-gap analysis.
