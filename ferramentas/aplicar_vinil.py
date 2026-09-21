"""
Aplica um vinil de fabrica na lataria de um carro e renderiza.

  blender -b --python aplicar_vinil.py -- <carro.obj> <vinil_d.png> <saida.png> [cor_base_hex]

O vinil entra como textura de cor nos materiais de pintura (M_CarPaint_Max e afins),
sobre a cor solida escolhida — que e como o jogo faz: a cor e procedural, o vinil vai por cima.
Onde o vinil e transparente aparece a cor; onde tem arte, aparece a arte.
"""
import bpy, sys, os, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
obj_path, livery_path, out_png = argv[0], argv[1], argv[2]
base_hex = argv[3] if len(argv) > 3 else "1d2b4d"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple((int(h[i:i + 2], 16) / 255.0) ** 2.2 for i in (0, 2, 4)) + (1.0,)


BASE = hex_rgb(base_hex)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Z', up_axis='Y')
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']

img = bpy.data.images.load(livery_path)
img.colorspace_settings.name = 'sRGB'

PAINT_HINTS = ("carpaint", "paint")
n_paint = 0
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nt = m.node_tree
    bsdf = next((x for x in nt.nodes if x.type == 'BSDF_PRINCIPLED'), None)
    if not bsdf:
        continue
    name = m.name.lower()
    is_paint = any(h in name for h in PAINT_HINTS)
    has_tex = any(x.type == 'TEX_IMAGE' for x in nt.nodes)

    if is_paint:
        n_paint += 1
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-700, 200)
        # mistura: cor solida embaixo, vinil por cima usando o alfa do proprio vinil
        mix = nt.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = 'MIX'
        mix.location = (-350, 200)
        mix.inputs[1].default_value = BASE
        nt.links.new(tex.outputs["Color"], mix.inputs[2])
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.16
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.55
    elif not has_tex:
        if "glass" in name:
            bsdf.inputs["Base Color"].default_value = (0.04, 0.05, 0.06, 1)
        elif "chrome" in name or "nickel" in name:
            bsdf.inputs["Base Color"].default_value = (0.62, 0.64, 0.68, 1)
            bsdf.inputs["Roughness"].default_value = 0.12
            if "Metallic" in bsdf.inputs:
                bsdf.inputs["Metallic"].default_value = 1.0
        else:
            bsdf.inputs["Base Color"].default_value = (0.045, 0.045, 0.05, 1)
            bsdf.inputs["Roughness"].default_value = 0.5

print("materiais de pintura com vinil: %d" % n_paint)

for o in objs:
    for p in o.data.polygons:
        p.use_smooth = True

mn = [1e9] * 3; mx = [-1e9] * 3
for o in objs:
    for c in o.bound_box:
        v = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], v[i]); mx[i] = max(mx[i], v[i])
ctr = [(mn[i] + mx[i]) / 2 for i in range(3)]
size = max(mx[i] - mn[i] for i in range(3))

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
d = size * 1.5
cam.location = (ctr[0] + d * 0.80, ctr[1] + d * 0.30, ctr[2] + d * 0.58)
cam.rotation_euler = (mathutils.Vector(ctr) - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam

for loc, e, sz in (((4, 6, 4), 3400, 7), ((-6, 3, -5), 1400, 9), ((-2, 5, 6), 1000, 6)):
    ld = bpy.data.lights.new("l", 'AREA'); ld.energy = e; ld.size = sz
    lo = bpy.data.objects.new("l", ld)
    lo.location = (ctr[0] + loc[0], ctr[1] + loc[1], ctr[2] + loc[2])
    lo.rotation_euler = (mathutils.Vector(ctr) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.collection.objects.link(lo)

w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.052, 0.06, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
bpy.context.scene.world = w

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 1100
sc.render.resolution_y = 700
sc.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("RENDERED " + out_png)
