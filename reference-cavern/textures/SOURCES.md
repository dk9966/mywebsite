# Surface assets

All source assets are CC0, downloaded from Poly Haven at 2K resolution for this scene.

- [Dark Rock](https://polyhaven.com/a/dark_rock), by Amal Kumar: color, roughness, OpenGL normal and displacement maps used for the reconstructed cavern masses.
- [Blue Metal Plate](https://polyhaven.com/a/blue_metal_plate), by Rob Tuytel: color, roughness and OpenGL normal maps used on manufactured surfaces.
- [Rock Face 01](https://polyhaven.com/a/rock_face_01), by Dario Barresi: a shared 20,174-triangle scanned bedrock module and its surface maps, embedded in existing cliffs and hanging formations. Original files are under `assets/rock_face_01`.
- [Rock 06](https://polyhaven.com/a/rock_06), by Rob Tuytel: retained as an earlier iteration source; replaced by Dark Rock in the current reconstructed masses.

The derived maps desaturate and grade the source colors for the cavern palette. Color calculations use linear light, then encode to sRGB. Roughness maps are stored as linear data. Metric UVs, normal maps, material maps and scanned volumes belong to coherent 3D surfaces. All active maps are packed in the Blender file. No camera-facing image planes or projected reference backdrops are used.
