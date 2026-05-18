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

class ShaderBackground:
    def __init__(self, width, height, frag_shader_path, ctx=None):
        self.width = width
        self.height = height
        self.start_time = time.time()

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
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
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
        self.fbo.use()

    def render(self, camera=(0.0, 0.0)):
        """Rend le shader avec un décalage de caméra."""
        self.fbo.use()
        self.fbo.clear()
        if "u_time" in self.prog:
            self.prog["u_time"] = time.time() - self.start_time
        if "u_resolution" in self.prog:
            self.prog["u_resolution"] = (self.width, self.height)
        if "u_camera" in self.prog:
            self.prog["u_camera"] = camera

        self.vao.render(moderngl.TRIANGLE_STRIP)
        data = self.fbo.read(components=3)
        image = pygame.image.frombuffer(data, (self.width, self.height), "RGB")
        return pygame.transform.flip(image, False, True)

    def resize(self, width, height):
        self.width = width
        self.height = height
        self.fbo.release()
        self.fbo = self.ctx.simple_framebuffer((width, height))
        self.fbo.use()
