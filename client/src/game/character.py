from events import subscriber
from game import Entity
from game.components import Movable
from game.components import Renderable
from game.events import CharacterJoin
from game.events import CharacterLeave
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


class Character(Entity):
    """Game entity which represents a character."""

    def __init__(self, name, parent_node):
        """Constructor.

        :param name: Character's name.
        :type name: str

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
        super(Character, self).__init__(renderable, movable)

        self.name = name
        self.rot_angle = 0.0

    def destroy(self):
        """Removes itself from the scene.
        """
        LOG.debug('Destroying character {}'.format(self.e_id))
        node = self[Renderable].node
        node.parent.remove_child(node)

    def update(self, dt):
        """Update the character.

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


@subscriber(CharacterJoin)
def add_character(evt):
    """Add a character in the game.

    Gets all the relevant data from the event.

    :param evt: The event instance
    :type evt: :class:`game.events.CharacterJoin`
    """
    LOG.debug('Event subscriber: {}'.format(evt))
    context = evt.context
    # Only instantiate the new character if it does not exist
    if not context.resolve_entity(evt.srv_id):
        player = Character(evt.name, context.scene.root)
        context.entities[player.e_id] = player
        context.server_entities_map[evt.srv_id] = player.e_id


@subscriber(CharacterLeave)
def remove_character(evt):
    """Remove a character from the game.

    Gets all the relevant data from the event.

    :param evt: The event instance
    :type evt: :class:`game.events.CharacterLeave`
    """
    LOG.debug('Event subscriber: {}'.format(evt))
    context = evt.context
    if evt.srv_id in context.server_entities_map:
        e_id = context.server_entities_map.pop(evt.srv_id)
        character = context.entities.pop(e_id)
        character.destroy()


@subscriber(EntityIdle)
def character_set_position(evt):
    """Updates the character position

    Gets all the relevant data from the event.

    :param evt: The event instance
    :type evt: :class:`game.events.EntityIdle`
    """
    LOG.debug('Event subscriber: {}'.format(evt))
    entity = evt.context.resolve_entity(evt.srv_id)
    if entity:
        entity[Movable].position = evt.x, evt.y


@subscriber(EntityMove)
def character_set_movement(evt):
    """Set the move action in the character entity.

    :param evt: The event instance
    :type evt: :class:`game.events.EntityMove`
    """
    LOG.debug('Event subscriber: {}'.format(evt))
    entity = evt.context.resolve_entity(evt.srv_id)
    if entity:
        entity[Movable].move(
            position=evt.position,
            destination=evt.destination,
            speed=evt.speed)
