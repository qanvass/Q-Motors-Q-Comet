# Q Comet production status

## Completed

- Original concept set received
- Public name, manufacturer, Q+ badge, and spawn name locked
- Exterior, cabin, wheel, and lighting directions documented
- Game-oriented interior selected
- First-pass dimensions proposed
- Automated Blender blockout script created
- v002 proportion blockout saved (`qcomet_blockout_v002.blend`)
- First detailed body pass saved as `qcomet_body_v003.blend` (v001/v002 not overwritten)
- Concept photos placed as tracing planes; critic agent started
- v010 inspected through Blender MCP on port 9876 and preserved as `qcomet_checkpoint_v010.blend`
- v011 canopy/body surfacing review saved as `qcomet_body_v011.blend`, with separate panes/panels, six review views, and geometry/sightline evidence in `source/blender/review_v011/`
- v012 exterior refinement saved through MCP port 9876, with genuine pill recesses, slatted intake, swept LEDs, continuous rear light tiers, diffuser/bronze details, and closed active vehicle meshes; see `docs/qcomet-v012-review.md`
- v013 full vehicle rig milestone saved as `qcomet_vehicle_v013.blend` (M1 cabin + M2 hinges + M3 hierarchy, doors, hood, trunk, 4 wheels, 4 seats, steering)
- v015 native Sollumz fragment milestone saved as `qcomet_sollumz_v015.blend` (24 bones, 21 collision bounds, 6 windows, in-memory export passed, no binary assets fabricated)
- v016 production UV pass saved as `qcomet_sollumz_v016.blend` (dash text UVMap 0/1, glass UVMap 2 per-pane 0..1 unwrap, 0 Sollumz warnings)
- v017 rear rebuild saved as `qcomet_rear_v017.blend` matching official concept photo:
  - Sculpted 3-blade flowing LED light bar with pinched center ribbon and ruby emission
  - 3D metallic bronze Q+ emblem in shallow trunk lid recess
  - Aerodynamic ducktail spoiler lip overhanging taillight channel
  - Bumper character shelf crease, ultrasonic parking sensors, corner vertical extraction ducts, and outer vertical red reflector strips
  - Gloss carbon diffuser with stepped bronze accent trim, 4 vertical aero strakes with bronze accents, and dual horizontal red reflectors
  - Updated Sollumz export meshes (`exp_*`) and convex collision hulls (`col_boot`, `col_bumper_r`)
  - Render evidence and validation report in `vehicles/qcomet/source/blender/review_v017/`

## In progress

- Human review of the v017 rear rebuild against target concept photo (`target_rear_concept.png`)
- Production body UV unwrapping and PBR texture map baking (replacing proxy projections)
- Door, bonnet, and boot hinge sweep certification

## Next / Not started

- Handling tuning and metadata (`vehicles.meta`, `handling.meta`, `carcols.meta`)
- Clean-server FiveM spawn test and driving validation
- Delivery package and listing media (no binaries written until human test checklist passes; `game_ready = false`)
