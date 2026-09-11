# Q Comet v012 exterior review

## Deliverables

- Active Blender source: `vehicles/qcomet/source/blender/qcomet_body_v012.blend`.
- Incoming unsaved v011 session preserved in `qcomet_checkpoint_v011.blend`; the previous versioned source was not overwritten.
- Repeatable live recipe: `tools/blender/refine_qcomet_body_v012.py`.
- Cycles review recipe: `tools/blender/review_qcomet_body_v012.py`.
- Evidence directory: `vehicles/qcomet/source/blender/review_v012/`.

## Refinements

- Replaced floating octagons with 262 actual stadium-shaped pockets cut into `bumper_f`, across nine rows from 0.305 to 0.545 m. The fascia and pocket rims retain `Paint_Primary`; recessed floors use dark olive, not a black tile overlay.
- Applied the requested two-dimensional falloff, badge exclusion radius, 28 mm lattice, 14 mm alternating stagger, weighted 20/6.5 mm half-dimensions, and weighted maximum 7 mm inward depth.
- Added nine fine carbon lower-intake louvers, recessed backing, thin bronze upper mouth and splitter edge.
- Rebuilt three swept LED blades per headlamp and recessed outer DRL scoops. Warm-white emission is exactly 20.0. Large lamp apertures are real openings in the surrounding panels, not surfaces placed over the lights.
- Added continuous wavy `tail_bar_running` and `tail_bar_brake`, both at emission 25.0; the brake tier is wider/brighter red, with quarter branches. The ducktail sits immediately above the light channel.
- Sculpted a lobed carbon diffuser with six tapered strakes and thin bronze edges. Reduced the old reverse-light blocks to small inset lenses, unlit for the running/brake review; game-function wiring remains pending.
- Added recessed front-fender extraction ducts, horizontal bronze blades, flush bronze-edged door handles, and slim camera mirror pods with satin bronze caps.
- Preserved the directional turbine spokes and wheel centers at mirrored (+/-0.845, +/-1.50, 0.39) m. Removed legacy loose wheel vertices and closed wheel/badge boundaries; added correctly oriented original Q+ center caps.
- Retained the v011 shared curved canopy master and separate glass/body components, four doors and four seats.

## Important specification conflict

A full-width pill is 40 mm wide, exceeding the requested 28 mm column pitch. Fully populating that lattice would merge the pockets into long grooves. The recipe preserves the specified dimensions and lattice, but symmetrically omits overlapping candidates with a small ligament allowance. Fifty collision candidates are omitted; 262 pockets remain. This is a documented occupancy deviation, not an exact fully populated matrix.

## Verification

`geometry_validation.json` audits every visible, render-enabled vehicle mesh, including evaluated solidification. Hidden source archives, construction cutters and the studio floor are excluded.

- Zero non-manifold edges, loose vertices and zero-area faces in the active vehicle meshes.
- All 262 pocket-center depth probes agree with the weighted inward depth within 0.4 mm, and lie behind the original fascia.
- 440 front/rear sight probes verify that the blade and taillight centerlines are not covered by opaque panels.
- Emission values, locked wheel origins, and presence of four separate doors/seats are checked.
- The inherited canopy/cowl/deck master join error is zero; this is a master-surface continuity check, not an automotive Class-A surfacing certificate.
- The save function refuses to write v012 if its geometry, recess, emission, visibility or wheel gates fail.
- Source-image, art-brief and incoming Blender-file SHA-256 values are recorded in the validation evidence.

`contact_sheet.png` covers front/rear three-quarter, side, front, rear, top, front-detail, rear-detail and unlit-grille views. Individual PNGs retain higher resolution. `reference_comparison.png` places the supplied front/rear detail crops beside the new detail renders; these are qualitative, unregistered comparisons, not a pixel-error score.

## Rebuild

With this project checkout available and v011 or v012 open, execute the refinement recipe in Blender using `runpy.run_path(..., run_name='__main__')`. It resets modified panels from preserved v011 snapshots before rebuilding, keeps construction cutters hidden afterward, audits the result, embeds the recipe and saves v012. The installed Blender session uses the Manifold Boolean solver for large apertures and Exact for the fine dimple pockets.

Execute the review recipe separately for the nine Cycles renders. It restores emission after the unlit diagnostic and returns the viewport to MATERIAL preview. Save again after changing review-camera settings if those settings should persist.

## Limitations and human review

This is a source-guided exterior refinement of the provisional body package, **not a certified exact reconstruction of the concept illustrations**. The supplied perspective illustrations are not calibrated dimension sheets. Full-vehicle proportions, the cabin, tire detail, Class-A highlight quality, exact orthographic alignment and production topology still need human review. Closed topology does not prove absence of all self-intersections or validate game deformation.

No GTA binaries, rigging, collision, LODs, functional light mappings or FiveM gameplay evidence are claimed. Final dimensions and release/publication remain subject to owner approval and the human test checklist.
