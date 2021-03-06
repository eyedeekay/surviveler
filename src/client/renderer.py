from exceptions import ConfigError
from renderlib.core import renderer_clear
from renderlib.core import renderer_init
from renderlib.core import renderer_present
from renderlib.core import renderer_shutdown
import logging
import sdl2 as sdl


LOG = logging.getLogger(__name__)


class Renderer:
    """Renderer.

    This class provides methods for render system initialization, management and
    shutdown.
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
            gl_major, gl_minor = [
                int(v) for v in config.get('openglversion', '3.3').split('.')
            ]
        except (KeyError, TypeError, ValueError) as err:
            raise ConfigError(err)

        # create a SDL window
        self.win = sdl.SDL_CreateWindow(
            b'Surviveler',
            sdl.SDL_WINDOWPOS_CENTERED,
            sdl.SDL_WINDOWPOS_CENTERED,
            width,
            height,
            sdl.SDL_WINDOW_OPENGL)
        if self.win is None:
            raise RuntimeError('failed to create SDL window')

        # create an OpenGL context
        sdl.SDL_GL_SetAttribute(
            sdl.SDL_GL_CONTEXT_PROFILE_MASK,
            sdl.SDL_GL_CONTEXT_PROFILE_CORE)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MAJOR_VERSION, gl_major)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_CONTEXT_MINOR_VERSION, gl_minor)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DOUBLEBUFFER, 1)
        sdl.SDL_GL_SetAttribute(sdl.SDL_GL_DEPTH_SIZE, 24)
        self.ctx = sdl.SDL_GL_CreateContext(self.win)

        if self.ctx is None:
            sdl.SDL_DestroyWindow(self.win)
            raise RuntimeError('failed to initialize OpenGL context')

        # initialize renderer
        renderer_init()

        self._width = width
        self._height = height

        LOG.info('renderer initialized; created {}x{} window'.format(
            width, height
        ))

    def __del__(self):
        self.shutdown()

    @property
    def width(self):
        """Render window width."""
        return self._width

    @property
    def height(self):
        """Render window height."""
        return self._height

    def clear(self):
        """Clear buffers."""
        renderer_clear()

    def present(self):
        """Present updated buffers to screen."""
        renderer_present()
        sdl.SDL_GL_SwapWindow(self.win)

    def shutdown(self):
        """Shut down the renderer."""
        renderer_shutdown()
        sdl.SDL_GL_DeleteContext(self.ctx)
        self.ctx = None
        sdl.SDL_DestroyWindow(self.win)
        self.win = None
