"""Render SpaghettiKart menu art for a glTF model.

blender -b -P menu_assets.py -- --model robot.glb --char mario --name SPECTRUM --color 3c0064 --out mod/
"""
import argparse
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

FONT = {  # 5x7, rows top to bottom
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
}
FACE_FRAMES = 17


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--char", default="mario")
    p.add_argument("--name", required=True)
    p.add_argument("--color", default="3c0064", help="portrait background, hex RGB")
    p.add_argument("--yaw", type=float, default=0.0, help="degrees to turn the model so its front faces -Y")
    p.add_argument("--out", required=True)
    return p.parse_args(sys.argv[sys.argv.index("--") + 1:])


def setup_scene(model, yaw):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.import_scene.gltf(filepath=model)
    meshes = [o for o in scene.objects if o.type == "MESH"]

    pivot = bpy.data.objects.new("Model", None)
    scene.collection.objects.link(pivot)
    for o in scene.objects:
        if o.parent is None and o is not pivot:
            o.parent = pivot
    pivot.rotation_euler.z = math.radians(yaw)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    center = sum(pts, Vector()) / len(pts)
    radius = max((p - center).length for p in pts)
    for o in pivot.children:
        o.location -= center
    turntable = bpy.data.objects.new("Turntable", None)
    scene.collection.objects.link(turntable)
    pivot.parent = turntable

    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    direction = Vector((-0.55, -1.0, 0.45)).normalized()
    cam.location = direction * radius * 4
    cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    cam.data.clip_end = radius * 10
    scene.camera = cam

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-30))
    scene.collection.objects.link(sun)
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.35, 0.35, 0.35)

    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 128
    scene.cycles.use_denoising = False
    scene.view_settings.view_transform = "Standard"
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.threads_mode = "FIXED"
    r.threads = 2
    return scene, cam, turntable, radius


def render(scene, path, size):
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def load(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(img)
    return px


def save(px, path):
    h, w = px.shape[:2]
    img = bpy.data.images.new("out", w, h, alpha=True)
    img.pixels = px[::-1].ravel().tolist()
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def portrait(sprite, color):
    rgb = np.array([int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)
    out = np.empty_like(sprite)
    out[..., :3] = rgb
    out[..., 3] = 1
    out[[0, -1], :, :3] = out[:, [0, -1], :3] = rgb * 0.5
    a = sprite[..., 3:4]
    out[..., :3] = sprite[..., :3] * a + out[..., :3] * (1 - a)
    return out


def name_plate(text):
    """64x12 gray bar matching the stock plates."""
    w, h = 64, 12
    gray = np.empty((h, w), dtype=np.float32)
    gray[:] = np.linspace(0x78, 0xB0, w)
    gray[0], gray[-1] = 0xF8, 0x40
    gray[:, 0], gray[:, -1] = 0xD0, 0x68
    out = np.ones((h, w, 4), dtype=np.float32)
    out[..., :3] = (gray / 255)[..., None]
    x = (w - (len(text) * 6 - 1)) // 2
    for ch in text:
        for dy, row in enumerate(FONT[ch]):
            for dx, bit in enumerate(row):
                if bit == "1":
                    out[2 + dy, x + dx, :3] = 0x30 / 255
        x += 6
    return out


def main():
    args = parse_args()
    out = args.out.rstrip("/")
    faces = f"{out}/textures/player_selection"
    os.makedirs(faces, exist_ok=True)
    os.makedirs(f"{out}/textures/common_data", exist_ok=True)
    os.makedirs(f"{out}/textures/texture_tkmk00", exist_ok=True)

    scene, cam, turntable, radius = setup_scene(args.model, args.yaw)
    cam.data.ortho_scale = radius * 1.7
    for i in range(FACE_FRAMES):
        turntable.rotation_euler.z = math.radians(360 * i / (FACE_FRAMES - 1))
        render(scene, f"{faces}/{args.char}_face_{i:02d}.png", 64)
        print("FACE", i, flush=True)

    turntable.rotation_euler.z = 0
    cam.data.ortho_scale = radius * 1.5
    tmp = f"{out}/.portrait_sprite.png"
    render(scene, tmp, 32)
    save(portrait(load(tmp), args.color), f"{out}/textures/common_data/common_texture_portrait_{args.char}.png")
    os.remove(tmp)

    save(name_plate(args.name), f"{out}/textures/texture_tkmk00/texture_name_{args.char}.png")
    print("DONE", flush=True)


main()
