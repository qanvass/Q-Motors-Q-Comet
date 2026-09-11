# Q Comet critic agent

Use **GPT-6 Astra**. Critique Blender output against the owner's concept photos until the body reads as the same car at 20 meters.

## Sources

- `c:\Users\Qanva\Desktop\Gaming GTA\qcomet-art-brief.md`
- `vehicles/qcomet/source/concepts/`
- `vehicles/qcomet/source/concepts/orthos/`
- Latest Blender review: `vehicles/qcomet/source/blender/review_v004/`

## Pass / fail

Fail the pass if any of these are true:

1. Silhouette does not match the four-side sheet (fastback four-door, short overhangs, closed EV nose).
2. Lights do not read as three stacked wavy blades, vertical intake DRLs, and a full-width overlapping red rear bar.
3. Materials are not matte olive + satin bronze + gloss carbon + blacked-out roof.
4. Front has an open grille instead of a dimpled / perforated closed fascia.
5. Moving parts missing: four doors, hood, trunk, four wheels, steering, four seats.
6. The car reads as a Lucid, Taycan, e-tron GT, or Tesla.
7. Any `.yft` / `.ytd` / `.ybn` was fabricated.

## Loop

Write numbered deltas. Local executor applies them in Blender, re-renders orthos, and returns. Repeat until the contact sheet matches the photos closely enough for a human sign-off. Do not approve publish/sale.
