import moderngl
import numpy as np
import pygame
import time
import sys, os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ShaderEffect:
    def __init__(self, width, height, frag_shader_path, ctx=None):
        self.width = width
        self.height = height
        self.start_time = time.time()
        self.trigger_time = 0

        if ctx:
            self.ctx = ctx
        else:
            self.ctx = moderngl.create_standalone_context()

        with open(resource_path(frag_shader_path), "r") as f:
            frag_src = f.read()

        self.prog = self.ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_vert;
                out vec2 v_uv;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                    v_uv = (in_vert + 1.0) / 2.0;
                }
            """,
            fragment_shader=frag_src
        )

        self.vbo = self.ctx.buffer(np.array([
            -1.0, -1.0,
             1.0, -1.0,
            -1.0,  1.0,
             1.0,  1.0,
        ], dtype='f4').tobytes())

        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert')
        self.fbo = self.ctx.simple_framebuffer((width, height))
        
        # Texture pour l'entrée
        self.texture = None
        self.trigger_time = -10.0
        self.trigger_pos = (0.5, 0.5)

    def trigger(self, pos=(0.5, 0.5), current_time=None):
        """Déclenche l'effet à une position spécifique (UV: 0.0 à 1.0)."""
        if current_time is None:
            self.trigger_time = time.time() - self.start_time
        else:
            self.trigger_time = current_time
        self.trigger_pos = pos

    def render(self, surface, current_time=None):
        """Applique le shader sur la surface donnée."""
        if current_time is None:
            current_time = time.time() - self.start_time
            
        # On s'assure que le contexte est bien celui-ci
        self.fbo.use()
        
        # Mise à jour des uniforms spécifiques
        if "u_trigger_time" in self.prog:
            self.prog["u_trigger_time"] = self.trigger_time
        if "u_pos" in self.prog:
            self.prog["u_pos"] = self.trigger_pos

        # Mise à jour de la texture d'entrée
        # True pour le flip vertical car ModernGL a (0,0) en bas à gauche
        surf_data = pygame.image.tostring(surface, "RGB", True) 
        
        if not self.texture or self.texture.size != surface.get_size():
            if self.texture:
                self.texture.release()
            self.texture = self.ctx.texture(surface.get_size(), 3, surf_data)
        else:
            self.texture.write(surf_data)
        
        self.texture.use(0)
        
        if "u_texture" in self.prog:
            self.prog["u_texture"] = 0
            
        self.fbo.clear()
        
        if "u_time" in self.prog:
            self.prog["u_time"] = current_time
        if "u_resolution" in self.prog:
            self.prog["u_resolution"] = (self.width, self.height)

        self.vao.render(moderngl.TRIANGLE_STRIP)
        
        data = self.fbo.read(components=3)
        image = pygame.image.frombuffer(data, (self.width, self.height), "RGB")
        
        # On re-flip pour Pygame
        return pygame.transform.flip(image, False, True)

    def resize(self, width, height):
        self.width = width
        self.height = height
        if self.fbo:
            self.fbo.release()
        self.fbo = self.ctx.simple_framebuffer((width, height))
