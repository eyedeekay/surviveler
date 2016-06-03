from OpenGL.GL import GL_BACK
from OpenGL.GL import GL_BLEND
from OpenGL.GL import GL_COLOR_BUFFER_BIT
from OpenGL.GL import GL_CULL_FACE
from OpenGL.GL import GL_CW
from OpenGL.GL import GL_DEPTH_BUFFER_BIT
from OpenGL.GL import GL_DEPTH_TEST
from OpenGL.GL import GL_ONE_MINUS_SRC_ALPHA
from OpenGL.GL import GL_SHADING_LANGUAGE_VERSION
from OpenGL.GL import GL_SRC_ALPHA
from OpenGL.GL import GL_VERSION
from OpenGL.GL import glBlendFunc
from OpenGL.GL import glClear
from OpenGL.GL import glClearColor
from OpenGL.GL import glCullFace
from OpenGL.GL import glEnable
from OpenGL.GL import glFlush
from OpenGL.GL import glFrontFace
from OpenGL.GL import glGetString
from contextlib import ExitStack
from exceptions import ConfigError
from exceptions import OpenGLError
from exceptions import SDLError
from utils import as_utf8
import logging
import sdl2 as sdl


LOG = logging.getLogger(__name__)


class RenderOp:
    """Single render operation.

    This class incapsulates the context of rendering a single mesh, with its
    shader and shader parameters, textures, etc.

    The renderer internally can reorder rendering operations for better
    efficiency and less OpenGL context switches.
    """

    def __init__(self, shader, shader_params, mesh, textures=None):
        """Constructor.

        :param shader: Shader to use for rendering.
        :type shader: :class:`renderer.shader.Shader`

        :param shader_params: Shader parameters to submit to the shader.
        :type shader_params: mapping

        :param mesh: Mesh to render.
        :type mesh: :class:`renderer.mesh.Mesh`

        :param textures: List of textures to make active and use during
            rendering.
        :type textures: list of :class:`renderer.texture.Texture` or `None`
        """
        self.mesh = mesh
        self.shader = shader
        self.shader_params = shader_params
        self.textures = textures or []


class Renderer:
    """An OpenGL rendering context.

    A renderer abstracts OS-specific details like window creation and OpenGL
    context set up.
    """

    def __init__(self, config):
        """Constructor.

        Instantiates a window and sets up an OpenGL context for it, which is
        immediately made active, using the given configuration data.

        :param config: Renderer-specific configuration.
        :type config: mapping-like interface.
        """
        try:
            width = int(config['width'])
            height = int(config['height'])
            depth = int(config.get('depth', 24))
            gl_major, gl_minor = [
                int(v) for v in config.get('openglversion', '3.3').split('.')
            ]
        except (KeyError, TypeError, ValueError) as err:
            raise ConfigError(err)

        # window creation
        self.window = sdl.SDL_CreateWindow(
            b"Surviveler",
            sdl.SDL_WINDOWPOS_CENTERED,
            sdl.SDL_WINDOWPOS_CENTERED,
            width,
            height,
            sdl.SDL_WINDOW_OPENGL)
        if self.window is None:
            raise SDLError('Unable to create a {}x{}x{} window'.format(
                width, height, depth))

        # OpenGL 3.3 core profile context initialization
        sdl.SDL_GL_SetAttribute(
            sdl.SDL_GL_CONTEXT_PROFILE_MASK,
            sdl.SDL_GL_CONTEXT_PROFILE_CORE)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MAJOR_VERSION, gl_major)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MINOR_VERSION, gl_minor)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DOUBLEBUFFER, 1)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DEPTH_SIZE, depth)

        self.gl_ctx = sdl.SDL_GL_CreateContext(self.window)
        if self.gl_ctx is None:
            raise OpenGLError('Unable to create OpenGL {}.{} context'.format(
                gl_major, gl_minor))

        LOG.info('OpenGL version: {}'.format(as_utf8(glGetString(GL_VERSION))))
        LOG.info('GLSL version: {}'.format(
            as_utf8(glGetString(GL_SHADING_LANGUAGE_VERSION))))

        self._width = width
        self._height = height
        self.gl_setup(width, height)
        self.render_queue = []

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def gl_setup(self, width, height):
        """Private."""
        # cut out invisible faces
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

        # flip the winding order
        glFrontFace(GL_CW)

        # enable depth buffer
        glEnable(GL_DEPTH_TEST)

        # enable alpha-blending
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # clear to black
        glClearColor(1, 1, 1, 1)

    def clear(self):
        """Clear buffers."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def add_render_op(self, op):
        """Add a rendering operation to rendering queue.

        :param op: Rendering operation to perform.
        :type op: :class:`renderer.renderer.RenderOp`
        """
        self.render_queue.append(op)

    def present(self):
        """Present updated buffers to screen."""

        def sort_key(op):
            return (op.shader.prog, op.mesh.vao)

        for op in sorted(self.render_queue, key=sort_key):
            # perform actual rendering
            with ExitStack() as stack:
                for tex_unit, tex in enumerate(op.textures):
                    stack.enter_context(tex.use(tex_unit))

                for p, v in op.shader_params.items():
                    op.shader[p] = v

                op.shader.use()
                op.mesh.render()

        self.render_queue.clear()

        glFlush()
        sdl.SDL_GL_SwapWindow(self.window)

    def shutdown(self):
        """Shuts down the renderer.

        Destroys the OpenGL context and the window associated with the renderer.
        """
        sdl.SDL_GL_DeleteContext(self.gl_ctx)
        sdl.SDL_DestroyWindow(self.window)
