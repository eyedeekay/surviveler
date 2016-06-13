from core.events import MouseClickEvent
from events import subscriber
from matlib import Vec
from network import Message
from network import MessageField
from network import MessageType
from utils import to_world
import logging

LOG = logging.getLogger(__name__)


@subscriber(MouseClickEvent)
def handle_mouse_click(evt):
    if evt.state == MouseClickEvent.State.up and evt.context.player:
        LOG.debug('Action: {}'.format(evt))
        LOG.debug('Viewport pos: {},{}'.format(evt.x, evt.y))

        renderer_conf = evt.context.conf['Renderer']
        w = int(renderer_conf['width'])
        h = int(renderer_conf['height'])

        # Find the direction applying the modelview matrix to the facing
        # direction of the camera
        camera = evt.context.camera
        pos, ray = camera.trace_ray(evt.x, evt.y, w, h)

        # The normal vector for the y=0 plane
        norm = Vec(0, 1, 0)

        # And here finally we have the target of the click in world coordinates
        # More reference about the used math here:
        #  * http://antongerdelan.net/opengl/raycasting.html
        t = - (pos.dot(norm)) / ray.dot(norm)
        target = pos + (ray * t)
        world_pos = to_world(target.x, target.y, target.z)
        LOG.debug('World pos: {}'.format(world_pos))

        msg = Message(MessageType.move, {
            MessageField.x_pos: world_pos.x,
            MessageField.y_pos: world_pos.y,
        })

        evt.context.msg_queue.append(msg)
