import bpy, sys, math, os

argv = sys.argv[sys.argv.index("--") + 1:]
obj_path, out_png = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)

# Blender 4.5 uses wm.obj_import
bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Z', up_axis='Y')

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if not objs:
    print("NO MESH IMPORTED"); sys.exit(1)

mn = [1e9] * 3; mx = [-1e9] * 3
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ __import__('mathutils').Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = [(mn[i] + mx[i]) / 2 for i in range(3)]
size = max(mx[i] - mn[i] for i in range(3))
print("IMPORTED objects=%d  size=%.3f  center=%s" % (len(objs), size, [round(c, 2) for c in ctr]))

# simple grey material so shape reads clearly
mat = bpy.data.materials.new("grey")
mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]
bsdf.inputs["Base Color"].default_value = (0.55, 0.57, 0.6, 1)
bsdf.inputs["Roughness"].default_value = 0.35
for o in objs:
    o.data.materials.clear(); o.data.materials.append(mat)

# camera 3/4 front
cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
d = size * 1.9
cam.location = (ctr[0] + d * 0.72, ctr[1] + d * 0.42, ctr[2] + d * 0.62)
import mathutils
direction = mathutils.Vector(ctr) - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam

# lights
for loc, e in [((4, 6, 4), 2500), ((-5, 3, -4), 1200), ((0, 8, 0), 800)]:
    ld = bpy.data.lights.new("l", 'POINT'); ld.energy = e
    lo = bpy.data.objects.new("l", ld); lo.location = (ctr[0] + loc[0], ctr[1] + loc[1], ctr[2] + loc[2])
    bpy.context.scene.collection.objects.link(lo)

w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1)
bpy.context.scene.world = w

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 1000
sc.render.resolution_y = 640
sc.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("RENDERED " + out_png)
