# Kart sprites from a 3D model

Turns a glTF model into a character mod that replaces one racer. Used for the
Spectrum 3847 2026 robot in `mods/spectrum3847-robot/`.

Needs Blender 4.3 or newer with numpy, and Node with pnpm if the model is
Draco compressed (Onshape exports are).

```sh
cd tools/kart_sprites
pnpm install
node undraco.mjs robot.gltf robot.glb

# 289 driving frames x 4 wheel copies, plus 32 spin-out frames
blender -b ../../docs/MK64_Spaghetti_Adjusted_Kart_Setup.blend -S Kart -P render_kart.py -- \
    --model robot.glb --char mario --yaw 180 --out ../../mods/spectrum3847-robot

# character select faces, placement icon, name plate
blender -b -P menu_assets.py -- --model robot.glb --char mario --name SPECTRUM \
    --color 3c0064 --out ../../mods/spectrum3847-robot
```

`--yaw` turns the model so its front points along +Y in the kart setup file,
where frame 0 is the view from behind. `menu_assets.py` expects the front
along -Y, which is how Onshape exports it, so it needs no yaw for this robot.

The name plate font only has the letters in SPECTRUM. Add glyphs to `FONT`
for other names.

To play, copy the mod folder into `mods/` next to the game, or zip its
contents into a `.o2r`:

```sh
cd mods/spectrum3847-robot && zip -qr ../spectrum3847-robot.o2r .
```
