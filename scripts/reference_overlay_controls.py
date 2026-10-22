bl_info = {
    "name": "Reference Overlay Controls",
    "author": "Daniel",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport header",
    "description": "Adjust camera reference opacity directly in the viewport",
    "category": "3D View",
}

import bpy


def draw_reference_overlay(self, context):
    space = context.space_data
    if not space or space.type != 'VIEW_3D':
        return
    camera = space.camera if space.use_local_camera else context.scene.camera
    if not camera or camera.type != 'CAMERA':
        return
    backgrounds = camera.data.background_images
    if not backgrounds:
        return
    row = self.layout.row(align=True)
    row.prop(camera.data, 'show_background_images', text='', icon='IMAGE_REFERENCE')
    for index, background in enumerate(backgrounds):
        controls = row.row(align=True)
        controls.enabled = camera.data.show_background_images
        controls.prop(background, 'show_background_image', text='',
                      icon='HIDE_OFF' if background.show_background_image else 'HIDE_ON')
        slider = controls.row(align=True)
        slider.enabled = background.show_background_image
        slider.ui_units_x = 7
        label = 'Ref Opacity' if len(backgrounds) == 1 else f'Ref {index + 1}'
        slider.prop(background, 'alpha', text=label, slider=True)
    self.layout.separator()


class VIEW3D_PT_reference_overlay(bpy.types.Panel):
    bl_label = 'Reference Overlay'
    bl_idname = 'VIEW3D_PT_reference_overlay'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'View'

    def draw(self, context):
        layout = self.layout
        space = context.space_data
        camera = space.camera if space.use_local_camera else context.scene.camera
        if not camera or camera.type != 'CAMERA' or not camera.data.background_images:
            layout.label(text='No reference on the current camera')
            return
        layout.prop(camera.data, 'show_background_images', text='Show Reference')
        for background in camera.data.background_images:
            column = layout.column()
            column.enabled = camera.data.show_background_images
            column.prop(background, 'show_background_image',
                        text=background.image.name if background.image else 'Reference')
            row = column.row()
            row.enabled = background.show_background_image
            row.prop(background, 'alpha', text='Opacity', slider=True)


def register():
    bpy.utils.register_class(VIEW3D_PT_reference_overlay)
    bpy.types.VIEW3D_HT_header.prepend(draw_reference_overlay)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_reference_overlay)
    bpy.utils.unregister_class(VIEW3D_PT_reference_overlay)


if __name__ == '__main__':
    register()
