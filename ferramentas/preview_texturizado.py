import bpy, sys, mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
obj_path, out_png = argv[0], argv[1]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Z', up_axis='Y')

objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
mn = [1e9] * 3; mx = [-1e9] * 3
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ mathutils.Vector(c)
        for i in range(3):
            mn[i] = min(mn[i], w[i]); mx[i] = max(mx[i], w[i])
ctr = [(mn[i] + mx[i]) / 2 for i in range(3)]
size = max(mx[i] - mn[i] for i in range(3))

textured = 0
for o in objs:
    for slot in o.material_slots:
        m = slot.material
        if m and m.use_nodes:
            if any(n.type == 'TEX_IMAGE' for n in m.node_tree.nodes):
                textured += 1
print("IMPORTED objects=%d size=%.3f materials_with_texture=%d" % (len(objs), size, textured))

cam_data = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
d = size * 1.7
cam.location = (ctr[0] + d * 0.62, ctr[1] + d * 0.38, ctr[2] + d * 0.70)
cam.rotation_euler = (mathutils.Vector(ctr) - cam.location).to_track_quat('-Z', 'Y').to_euler()
bpy.context.scene.camera = cam

for loc, e in [((4, 6, 4), 3000), ((-5, 3, -4), 1500), ((0, 7, 2), 1200)]:
    ld = bpy.data.lights.new("l", 'POINT'); ld.energy = e
    lo = bpy.data.objects.new("l", ld)
    lo.location = (ctr[0] + loc[0], ctr[1] + loc[1], ctr[2] + loc[2])
    bpy.context.scene.collection.objects.link(lo)

w = bpy.data.worlds.new("w"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.06, 0.06, 0.07, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
bpy.context.scene.world = w

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.render.resolution_x = 1000
sc.render.resolution_y = 640
sc.render.filepath = out_png
bpy.ops.render.render(write_still=True)
print("RENDERED " + out_png)
