---
name: perfume-advisor
description: Recommends a perfume from the owner's personal collection based on weather, date, and occasion.
always: true
---

# Perfume Advisor — Collection & Selection Rules

This skill documents the owner's perfume collection and selection rules. The executable source of truth is `workspace/tools/perfume_tool.py` with data in `workspace/data/fragrances.json` and `workspace/data/ranking.json`.

For recommendation, history, stats, feedback, travel mode, and collection-management requests, call the deterministic tool through `exec`. Use this markdown as human-readable domain context only.

Always recommend ONLY from the collection below. Never suggest perfumes outside this list.
Always choose exactly one perfume by name. Never give a generic scent-family-only recommendation.
Always present temperatures in °C. Convert if needed.

## Strict Selection Algorithm Implemented By The Tool

### Step 0 — Check Recent Recommendations

Before selecting a perfume, the tool reads `workspace/memory/RECENT_PICKS.md` to check:
1. **What was recommended yesterday for the SAME city and SAME weather bucket**
2. **What was recommended yesterday** regardless of city or weather (global consecutive day rule)

### Step 1 — Determine Weather Bucket

From temperature and humidity:
- `Hot & dry`: `>25°C` and `<50%`
- `Hot & humid`: `>25°C` and `>=50%`
- `Mild`: `15-25°C`
- `Cool & dry`: `10-15°C` and `<60%`
- `Cold & dry`: `<10°C` and `<60%`
- `Cold & rainy`: `<15°C` and `>=60%`

### Step 2 — Infer Occasion

From the prompt or time:
- `office`, `work`, `meeting` → office
- `date`, `date night`, `dinner`, `party`, `night out` → evening
- Before 17:00 → daytime
- 17:00 or later → evening

### Step 3 — Build Candidate List

Filter to perfumes whose `Best Weather` matches the weather bucket, then apply the ranked priority list for the inferred occasion.

### Step 4 — Apply Rotation Rules

**Rule A — Same City + Same Weather Rotation:**
If the top-ranked perfume was recommended YESTERDAY for the SAME city AND SAME weather bucket, SKIP it and pick the NEXT perfume in the ranked list.

*Example: If "Sauvage" was picked yesterday for London (Mild), don't pick it today for London (Mild) — but it's OK for Sheffield (Mild).*

**Rule B — Global Consecutive Day Rule:**
Regardless of city or weather, if a perfume was recommended YESTERDAY (any city, any weather bucket), do NOT recommend it today. Skip to the next eligible perfume.

*Example: If "Sauvage" was picked yesterday for ANY city, don't pick it today for ANY city.*

**Rule C — Similar Scent Family Fallback:**
If both Rule A and Rule B eliminate the top candidates, prioritize perfumes with the **same scent family** as the skipped perfume(s). Similar families:
- Citrus group: Citrus Aquatic, Citrus Fruity Oriental, Citrus Aromatic
- Woody group: Woody Fresh, Aromatic Woody, Aquatic Woody, Oriental Woody, Fruity Woody, Amber Woody Vetiver
- Gourmand group: Amber Gourmand, Oriental Gourmand
- Fresh/Aquatic group: Fresh Aquatic, Marine Aromatic

### Step 5 — Select Final Perfume

Pick the first eligible perfume from the ranked list after applying all rotation rules.

### Step 6 — Log the Recommendation

After making a recommendation, the tool appends to `workspace/memory/RECENT_PICKS.md`:
```
| YYYY-MM-DD | [City Name] | [Weather Bucket] | [Occasion] | [Perfume Name] |
```

### Step 7 — Validation

If weather data is partial but enough to choose a bucket, make the recommendation.

---

## My Perfume Collection

| # | Name | Brand | Scent Family | Best Weather | Best Occasion |
|---|---|---|---|---|---|
| 1 | French Riviera | Mancera | Citrus Aquatic | Hot & dry, Hot & humid, Mild | Daytime, Casual, Summer |
| 2 | Le Beau | Jean Paul Gaultier | Fresh Aquatic | Hot & humid, Mild | Casual, Daytime, Beach |
| 3 | Le Male Elixir | Jean Paul Gaultier | Amber Gourmand | Cold & dry, Cold & rainy | Evening, Night out, Winter |
| 4 | Erba Pura | Xerjoff | Citrus Fruity Oriental | Mild, Hot & dry | Daytime, Casual, All seasons |
| 5 | Sauvage | Dior | Woody Fresh | Mild, Cool & dry | Versatile, Office, Casual |
| 6 | Born in Roma Uomo | Valentino | Aromatic Woody | Mild, Cool & dry | Office, Smart casual |
| 7 | Stronger With You Intensely | Emporio Armani | Oriental Gourmand | Cool & dry, Cold & dry | Evening, Date night, Autumn/Winter |
| 8 | Cool Water | Davidoff | Marine Aromatic | Hot & dry, Mild, Hot & humid | Daytime, Casual, Sport |
| 9 | Hawas for Him | Rasasi | Aquatic Woody | Mild, Hot & humid, Hot & dry | Casual, Daytime |
| 10 | Vulcan Feu | French Avenue | Oriental Woody | Mild, Cool & dry | Evening, Smart casual |
| 11 | Island Vanilla Dunes | Khadlaj | Oriental Gourmand | Cold & dry, Cold & rainy | Evening, Night out, Winter |
| 12 | Club de Nuit Intense Man | Armaf | Fruity Woody | Mild, Cool & dry | Evening, Office, Versatile |
| 13 | Imagination | Louis Vuitton | Citrus Aromatic | Mild, Hot & dry, Cool & dry | Daytime, Office, All seasons |
| 14 | Sultan Vetiver | Nishane | Amber Woody Vetiver | Cool & dry, Cold & dry, Cold & rainy | Evening, Formal, Autumn/Winter |

---

## Ranked Picks By Weather And Occasion

### Hot & dry
- Daytime: French Riviera, Imagination, Cool Water, Hawas for Him, Erba Pura
- Evening: Erba Pura, Imagination, Hawas for Him, French Riviera, Cool Water

### Hot & humid
- Daytime: French Riviera, Le Beau, Cool Water, Hawas for Him
- Evening: Le Beau, French Riviera, Hawas for Him, Cool Water

### Mild
- Daytime: Imagination, Sauvage, Born in Roma Uomo, French Riviera, Erba Pura
- Evening: Vulcan Feu, Club de Nuit Intense Man, Erba Pura, Born in Roma Uomo, Sauvage
- Office: Imagination, Born in Roma Uomo, Sauvage, Club de Nuit Intense Man

### Cool & dry
- Daytime: Imagination, Sauvage, Born in Roma Uomo, Sultan Vetiver
- Evening: Sultan Vetiver, Stronger With You Intensely, Vulcan Feu, Club de Nuit Intense Man, Sauvage
- Office: Imagination, Born in Roma Uomo, Sauvage, Club de Nuit Intense Man

### Cold & dry
- Daytime: Sultan Vetiver, Stronger With You Intensely, Le Male Elixir
- Evening: Le Male Elixir, Stronger With You Intensely, Island Vanilla Dunes, Sultan Vetiver

### Cold & rainy
- Daytime: Sultan Vetiver, Le Male Elixir, Island Vanilla Dunes
- Evening: Le Male Elixir, Island Vanilla Dunes, Sultan Vetiver

---

## Validation Guardrail

Before finalising your reply, verify:

1. The perfume name appears EXACTLY in the collection table above (entries #1–#14)
2. If it does NOT, pick the next entry from the ranked list
3. Never suggest perfumes outside the 14 entries
4. Always name a specific perfume — never respond with only a scent family
