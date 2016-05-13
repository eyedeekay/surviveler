from events import subscriber
from game import Entity
from game.components import Movable
from game.components import Renderable
from game.events import EntityIdle
from game.events import EntityMove
from loaders import load_obj
from math import pi
from matlib import Mat4
from matlib import Vec3
from matlib import Z
from renderer import Mesh
from renderer import Shader
import logging


LOG = logging.getLogger(__name__)


WHOLE_ANGLE = 2.0 * pi


class Player(Entity):
    """Game entity which represents a player."""

    def __init__(self, parent_node):
        """Constructor.

        :param parent_node: The parent node in the scene graph
        :type parent_node: :class:`renderer.scene.AbstractSceneNode`
        """
        vertices, _, _, indices = load_obj('data/models/player.obj')
        mesh = Mesh(vertices, indices)
        shader = Shader.from_glsl(
            'data/shaders/simple.vert',
            'data/shaders/simple.frag')

        renderable = Renderable(parent_node, mesh, shader)
        renderable.node.params['color'] = Vec3(0.04, 0.67, 0.87)
        movable = Movable((0.0, 0.0))
        super(Player, self).__init__(renderable, movable)

        self.rot_angle = 0.0

    def update(self, dt):
        """Update the player.

        This method computes player's game logic as a function of time.

        :param dt: Time delta from last update.
        :type dt: float
        """
        self.rot_angle += dt * pi
        if self.rot_angle >= WHOLE_ANGLE:
            self.rot_angle -= WHOLE_ANGLE

        self[Movable].update(dt)
        x, y = self[Movable].position
        self[Renderable].transform = (
            Mat4.trans(Vec3(x, y, 0)) *
            Mat4.rot(Z, self.rot_angle))

        # FIXME: perform this in a better place
        from client import Client
        Client.get_instance().camera.translate(-Vec3(x, y, 0))


@subscriber(EntityIdle)
def update_player_position(evt):
    """Updates the player position

    Gets all the relevant data from the event.

    :param evt: The event instance
    :type evt: :class:`game.events.PlayerPositionUpdated`
    """
    LOG.debug('Event subscriber: {}'.format(evt))

    # FIXME: find a proper way to map server ids with internal ids
    player = evt.client.get_entity(0)
    player[Movable].position = evt.x, evt.y


@subscriber(EntityMove)
def move_received(evt):
    """Set the move action in the player entity.

    :param evt: The event instance
    :type evt: :class:`game.events.PlayerActionMove`
    """
    LOG.debug('Event subscriber: {}'.format(evt))

    # FIXME: find a proper way to map server ids with internal ids
    player = evt.client.get_entity(0)
    player[Movable].move(
        position=evt.position,
        destination=evt.destination,
        speed=evt.speed)
