# Q Comet — Vehicle Art Brief

**Status:** concept locked from current sheets. Not a FiveM asset yet.  
**Internal ID / spawn name:** `qcomet`  
**Public name:** Q Comet  
**Manufacturer:** Q Motors  
**Badge:** original **Q+** mark only. Do not print “Quasar,” real automaker names, or NoPixel marks on the car, UI, or listing.  
**Class:** premium civilian electric sedan (four-door fastback)  
**Gameplay role:** executive / business RP car. Faster than an economy sedan, slower than a dedicated sports car. Stable at city speeds. Predictable brakes.

Source sheets in this folder. `q comet cabin dash.png` and `q comet cabin view and driver view.png` are the same image — keep one.

---

## Design lock

Matte olive / moss-green body. Satin bronze / copper trim. Gloss carbon on splitter, side skirts, fender vents, and rear diffuser. Blacked-out roof and pillars. Flush door handles. Slim camera-style mirrors. No open grille — closed EV fascia with a dimpled / perforated lower intake. Panoramic glass roof. Tan leather cabin with olive bolsters.

Keep the silhouette original. Do not land on a recognizable Lucid, Taycan, e-tron GT, or Tesla surfacing. If a pass still reads as a real car, revise headlights, grille texture, window graphic, or rear light bar before modeling continues.

---

## Parts list (separate meshes)

**Body:** chassis, hood, four doors, trunk, front bumper / splitter, rear bumper / diffuser, side skirts, fender vent inners, mirrors, glass (windshield, roof, side, rear), badges.

**Running gear:** four wheels, four tires, visible calipers, steering wheel.

**Lights (geometry + emissive):** headlight blades, vertical intake DRLs, full-width rear bar, indicators, brake, reverse. Interior: cluster, center icons, passenger Q+, thin dash ambient strip.

**Cabin:** four seats, dash glass bar, center console (rotary + cupholders + armrest), door cards, pedals, steering column.

Moving parts that must open and pivot correctly: doors, hood, trunk, wheels / steering, steering wheel.

---

## Materials

| Area | Treatment |
|---|---|
| Body | Paintable matte factory paint. Hero color: olive. Also ship a few neutrals plus 1–2 expressive colors. |
| Aero / vents | Carbon weave, not paintable. |
| Trim / badge / wheel face | Satin bronze. |
| Glass | Clear cabin glass, darker roof tint, light-smoked lamp lenses. |
| Tires | Standard performance rubber, readable tread, not a photo texture dump. |
| Interior | Tan leather, olive bolsters and dash top, dark mesh door insert, bronze thin trim, black glass screens. |

Do not 4K every map. Highest resolution on paint, lights, dash, seats, wheels. Combine materials where it does not hurt the read.

---

## Lights

Use the on/off sheet as the signature. Game version should read the same at 20 meters, not copy every CGI filament.

| Function | From the sheets | Game behavior |
|---|---|---|
| Headlights | Three stacked wavy white blades | Low / high beam |
| Front DRL / accent | Vertical strips in the outer intakes | On with lights |
| Indicators | Not isolated yet — assign a segment of the front blades and rear bar | Front + rear + mirror if budget allows |
| Taillights | Overlapping wavy red bar | Running lights |
| Brake | Same bar, brighter / fuller | Brake |
| Reverse | Not shown — add small white inners in the diffuser | Reverse |
| Interior | Cluster, four icons, passenger Q+, dash strip | Emissive, not a live NUI OS |

No custom phone OS, navigation sim, or animated infotainment unless a later product explicitly funds it. Static / simple emissive dash only for v1.

---

## Interior budget (game version)

Build the **game-oriented** cabin from the driver/cabin sheet, not the first cinematic dash.

**Keep:** full-width black glass bar; speed / P / battery cluster; four large icons; passenger Q+; two-spoke flat-bottom wheel with Q+ hub; one rotary; two cupholders; split armrest; tan/olive seats with embossed Q+ headrests; warm dash strip; metal pedals.

**Cut or simplify:** marble/gold console, sparkle wallpaper, dense button farms, speaker jewelry, cinematic city reflections as texture, anything that only reads in a 4K still.

Four usable seats. Driver view must be clean: wheel, cluster, road. Rear passengers need a believable card and seat back, not a hole.

---

## Remaining reference shots (block modeling until these exist)

1. Open door, hood, and trunk (hinge side visible).
2. Rear-seat view and a seat-only turnaround.
3. Undercarriage / floor (smooth EV skate is fine).
4. Flat Q+ badge on transparent background (front, rear, wheel cap, steering hub).
5. Dimension sheet: length, width, height, wheelbase, track, wheel diameter.
6. Light-function overlay: which strip is DRL vs beam vs indicator vs brake vs reverse.
7. One damage / dirt callout (what breaks, what dirt sits on).

Optional but useful: night beauty, rain, and a second paint color so materials get tested before export.

---

## FiveM v1 target

Working spawn `qcomet`. Four doors, hood, trunk, four seats, rotating wheels, steering, paint, glass, the light set above, collision, and LODs. Original handling later — do not copy a paid or proprietary vehicle.

This brief is the handoff into Blender / Sollumz. PNGs in this folder are not the product.
