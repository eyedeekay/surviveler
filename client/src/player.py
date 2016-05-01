from loaders import load_obj
from math import pi
from matlib import Mat4
from matlib import Vec3
from matlib import Y
from renderer import GeometryNode
from renderer import Mesh
from renderer import Shader


WHOLE_ANGLE = 2.0 * pi


class Player:
    """Game entity which represents a player."""

    def __init__(self):
        vertices, _, _, indices = load_obj('data/models/player.obj')

        mesh = Mesh(vertices, indices)
        shader = Shader.from_glsl(
            'data/shaders/simple.vert',
            'data/shaders/simple.frag')

        self._node = GeometryNode(mesh, shader)

        self.rot_angle = 0.0
        self.x = 0
        self.y = 0

    @property
    def node(self):
        """Scene node associated with player's entity."""
        return self._node

    def update(self, dt):
        """Update the player.

        This method computes player's game logic as a function of time.

        :param dt: Time delta from last update.
        :type dt: float
        """
        self.rot_angle += dt * pi
        if self.rot_angle >= WHOLE_ANGLE:
            self.rot_angle -= WHOLE_ANGLE

        self._node.transform = (
            Mat4.trans(Vec3(self.x, self.y, 0)) *
            Mat4.rot(Y, self.rot_angle))
