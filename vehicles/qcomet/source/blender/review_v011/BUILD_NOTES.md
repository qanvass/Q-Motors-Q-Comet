# Q Comet v011 canopy and body surfacing

## Source and preservation

- Inspected the active `qcomet_body_v010.blend` through Blender MCP on port 9876.
- Saved the incoming scene as `../qcomet_checkpoint_v010.blend` before editing.
- Saved the revised scene as `../qcomet_body_v011.blend`; the original v010 file was not overwritten.
- Superseded geometry is also retained in the hidden `QCOMET_V010_SURFACING_ARCHIVE` collection. The checkpoint is the authoritative original, including its original materials.
- Geometry is authored locally from the supplied Q Comet illustrations. No external vehicle geometry, textures, badges, handling, or sounds were imported.

## Surfacing changes

- Replaced overlapping greenhouse shells with a shared cubic longitudinal crown and curved transverse section. Windshield, darker panoramic roof, rear glass, four door panes, and two fixed quarter panes remain separate objects.
- Removed the opaque duplicate greenhouse that interfered with cabin visibility. Added black A/B/C pillars, roof-edge strips, thin belt seals, and fixed-quarter dividers.
- Moved the cowl and crown rearward after the side-reference comparison, retaining the original wheel centers and roof-height package.
- Rebuilt four independent door skins, four fender/quarter skins, a tapered sculpted bonnet, boot, shoulder surfaces, and curved front/rear fascias. There is no duplicate full outer body underneath the doors.
- Added wheel-well returns and shaped side skirts. Re-fitted the existing light blades, badges, mirror stalks, vent trim, and door cards to the revised surfaces.
- Preserved the original wheel/seat/interior placeholders rather than importing replacements. Recess-like lower-fascia dimples are separate geometry over a closed EV face, not an open grille.

## Validation and evidence

- `geometry_validation.json`: bilateral surface symmetry passes at 0.1 mm tolerance; generated panels have no zero-area faces or nonmanifold edges after Solidify.
- The analytical canopy/cowl and canopy/deck boundaries coincide. Separate seal and panel gaps remain intentional; this is not a claim that all panels are welded together.
- Four named door objects and four named seat placeholders remain present; wheel centers are unchanged.
- Seat-head placeholder clearance to the canopy is approximately 234 mm front and 258 mm rear. These are placeholder measurements, not occupant certification.
- Nine static driver sightline probes pass through the windshield without hitting opaque geometry. A real first-person gameplay test remains required.
- Six Cycles review images cover front/rear three-quarter, side, front, rear, and top views. Studio lights and floor are isolated in `QCOMET_V011_REVIEW_STUDIO` and are not vehicle parts.
- The supplied sheets are concept illustrations, not calibrated CAD. Visual comparison supports the curved black canopy, olive body, bronze accents, four-door EV layout, and revised silhouette; no exact multiview pixel-fit or Class-A continuity certification is claimed.

## Remaining gates

This is an exterior surfacing review source, not a finished v1 or game-ready vehicle. Owner dimension approval, production topology/UVs, detailed cabin and wheels, hinge/door-jamb engineering, functional seat/door setup, light-function validation, Sollumz hierarchy, collision, LODs, metadata, and clean-server evidence remain outstanding. Retained legacy badges/DRL/tail strips still have open boundary edges, listed separately in the audit.

No `.yft`, `.ytd`, `.ybn`, or other GTA binaries were fabricated or exported. Do not publish or sell until a human completes the required checklist.

## Reproduction

Run `tools/blender/refine_qcomet_body_v011.py` with `runpy.run_path(..., run_name='qcomet_recipe')` in an open v010/v011 Q Comet scene. Call `main('canopy')`, `main('body')`, and `main('details')` in order, or `main('all')`. Call `save_work()` explicitly when ready to save v011.

`tools/blender/review_qcomet_body_v011.py` provides `setup()`, `audit()`, and `render_view(name)`. Review renders use CPU Cycles with 24 samples and denoising; they are inspection images, not final listing media.
