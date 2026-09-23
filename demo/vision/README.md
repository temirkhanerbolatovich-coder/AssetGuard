# Vision demo images

1. Upload `room-305-baseline.png` for a new room and save the resulting scan as baseline.
2. Upload `room-305-warning.png` for the same room.
3. The second image has no printer. The comparison should include `printer: expected 1, detected 0` and the scan status should be `WARNING`.

The images were generated specifically for this repository as a photorealistic, uncluttered computer classroom. The warning image was produced as a constrained edit of the baseline image: remove only the white printer from the left side table and preserve the rest of the scene.

Grounding DINO is a zero-shot model. Other object counts can vary with the model version and threshold; the stable demo assertion is the missing printer and the resulting warning workflow.
