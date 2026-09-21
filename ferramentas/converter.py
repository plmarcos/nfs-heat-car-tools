"""
Converte os OBJ extraidos do NFS Heat para FBX (e opcionalmente uma versao low-poly).

Uso:
  blender -b --python convert.py -- <pasta_raiz> [--lowpoly N]

  <pasta_raiz>  pasta com uma subpasta por carro (F:\\CarsNfSHeat)
  --lowpoly N   tambem gera <carro>_lowpoly.obj/.fbx com no maximo N triangulos
"""
import bpy, sys, os, glob

argv = sys.argv[sys.argv.index("--") + 1:]
root = argv[0]
lowpoly = 0
if "--lowpoly" in argv:
    lowpoly = int(argv[argv.index("--lowpoly") + 1])


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def tri_count():
    n = 0
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.data.calc_loop_triangles()
            n += len(o.data.loop_triangles)
    return n


def convert(obj_path, make_low):
    base = os.path.splitext(obj_path)[0]
    clear()
    try:
        bpy.ops.wm.obj_import(filepath=obj_path, forward_axis='Z', up_axis='Y')
    except Exception as e:
        print("IMPORT-FAIL %s : %s" % (obj_path, e))
        return None
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        print("EMPTY %s" % obj_path)
        return None
    tris = tri_count()

    bpy.ops.export_scene.fbx(filepath=base + ".fbx", apply_unit_scale=True,
                             use_mesh_modifiers=True, path_mode='COPY')

    low_tris = 0
    if make_low and lowpoly and tris > lowpoly:
        ratio = float(lowpoly) / float(tris)
        for o in meshes:
            m = o.modifiers.new("dec", 'DECIMATE')
            m.ratio = ratio
        # apply
        for o in meshes:
            bpy.context.view_layer.objects.active = o
            try:
                bpy.ops.object.modifier_apply(modifier="dec")
            except Exception:
                pass
        low_tris = tri_count()
        bpy.ops.wm.obj_export(filepath=base + "_lowpoly.obj", forward_axis='Z', up_axis='Y',
                              export_materials=True, export_uv=True)
        try:
            bpy.ops.export_scene.fbx(filepath=base + "_lowpoly.fbx", apply_unit_scale=True, path_mode='COPY')
        except Exception:
            pass

    return (os.path.basename(obj_path), len(meshes), tris, low_tris)


rows = []
cars = sorted([d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)])
print("CARS: %d" % len(cars))
for cdir in cars:
    name = os.path.basename(cdir)
    main = os.path.join(cdir, name + ".obj")
    if os.path.exists(main):
        r = convert(main, True)
        if r:
            rows.append((name,) + r[1:])
            print("CONV %-46s objects=%-3d tris=%-7d low=%d" % (name, r[1], r[2], r[3]))
    wheel = os.path.join(cdir, name + "_wheel.obj")
    if os.path.exists(wheel):
        convert(wheel, False)

print("DONE %d cars" % len(rows))
