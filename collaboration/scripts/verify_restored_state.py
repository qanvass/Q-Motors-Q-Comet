import bpy

print("FILE", bpy.data.filepath)
print("DIRTY", bpy.data.is_dirty)
print("OBJECTS", len(bpy.context.scene.objects))
print("TMP", [obj.name for obj in bpy.data.objects if obj.name.startswith("COLLAB_TMP_")])
print("CAMERA", bpy.context.scene.camera.name if bpy.context.scene.camera else None)
print("ENGINE", bpy.context.scene.render.engine)
