"""Render a glTF model into SpaghettiKart kart sprites.

blender -b MK64_Spaghetti_Adjusted_Kart_Setup.blend -S Kart -P render_kart.py -- \
    --model robot.glb --out mod/ [--char mario] [--frames 0,20,100] [--yaw 0] [--res 64]
"""
import argparse
import math
import os
import shutil
import sys

import bpy
from mathutils import Vector

TEMPLATE_COLLECTIONS = ("Setup Files + Kart", "Example Character")
# Its bounds reach far below the wheels.
LOOSE_BOUNDS = {"Kart"}
# Driving frames have one copy per wheel animation step; the rest are spin-out frames.
WHEEL_FRAMES = 289
WHEELS = 4


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--char", default="mario")
    p.add_argument("--frames", help="comma separated; default is the whole scene range")
    p.add_argument("--yaw", type=float, default=0.0, help="degrees to turn the model so it faces forward")
    p.add_argument("--res", type=int, default=64)
    p.add_argument("--fit", type=float, default=1.0, help="model size relative to the original kart and driver")
    p.add_argument("--exposure", type=float, default=0.0)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--threads", type=int, default=3)
    return p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def world_bbox(objects):
    pts = [o.matrix_world @ Vector(c) for o in objects for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def main():
    args = parse_args()
    scene = bpy.data.scenes["Kart"]
    scene.frame_set(0)

    template = [o for name in TEMPLATE_COLLECTIONS for o in bpy.data.collections[name].all_objects
                if o.type == "MESH" and not o.hide_render and o.name not in LOOSE_BOUNDS]
    target_lo, target_hi = world_bbox(template)
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = True

    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=args.model)
    imported = [o for o in bpy.data.objects if o not in before]

    pivot = bpy.data.objects.new("Model", None)
    scene.collection.objects.link(pivot)
    for o in imported:
        if o.parent is None:
            o.parent = pivot
    pivot.rotation_euler.z = math.radians(args.yaw)
    bpy.context.view_layer.update()

    meshes = [o for o in imported if o.type == "MESH"]
    lo, hi = world_bbox(meshes)
    size, target = hi - lo, target_hi - target_lo
    scale = args.fit * min(target.x / size.x, target.y / size.y, target.z / size.z)
    pivot.scale = (scale, scale, scale)
    bpy.context.view_layer.update()

    lo, hi = world_bbox(meshes)
    center = (lo + hi) / 2
    target_center = (target_lo + target_hi) / 2
    pivot.location += Vector((target_center.x - center.x, target_center.y - center.y, target_lo.z - lo.z))
    bpy.context.view_layer.update()

    kart_root = bpy.data.objects["Kart Root"]
    world = pivot.matrix_world.copy()
    pivot.parent = kart_root
    pivot.matrix_world = world
    print("FIT scale", round(scale, 4), "model size", tuple(round(v, 3) for v in size), "target", tuple(round(v, 3) for v in target))

    scene.view_settings.exposure = args.exposure
    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = False
    r.resolution_x = r.resolution_y = args.res
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.threads_mode = "FIXED"
    r.threads = args.threads

    frames = ([int(f) for f in args.frames.split(",")] if args.frames
              else range(scene.frame_start, scene.frame_end + 1))
    kart = f"{args.char}_kart"
    folder = os.path.join(args.out, "textures", "karts", kart)
    for f in frames:
        scene.frame_set(f)
        name = os.path.join(folder, f"{kart}_frame{f:03d}")
        r.filepath = f"{name}_wheel0.png" if f < WHEEL_FRAMES else f"{name}.png"
        bpy.ops.render.render(write_still=True)
        if f < WHEEL_FRAMES:
            for w in range(1, WHEELS):
                shutil.copyfile(r.filepath, f"{name}_wheel{w}.png")
        print("FRAME", f, flush=True)


main()
