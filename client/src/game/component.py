from abc import ABC
from abc import abstractmethod
from renderer import GeometryNode


class Component(ABC):
    """Base class for all components"""

    @abstractmethod
    def __init__(self):
        pass


class Renderable(Component):
    """Renderable component.

    Creates a new node on the scene graph and exposes the transform property of
    the node.
    """

    def __init__(self, parent_node, mesh, shader):
        """Constructor.

        :param parent_node: Parent node of the new game node.
        :type parent_node: :class:`renderer.scene.AbstractSceneNode`

        :param mesh: The mesh.
        :type mesh: :class:`renderer.Mesh`

        :param shader: The shader program.
        :type shader: :class:`renderer.Shader`
        """
        self.entity = None
        self.node = GeometryNode(mesh, shader)
        parent_node.add_child(self.node)

    @property
    def transform(self):
        return self.node.transform

    @transform.setter
    def transform(self, value):
        self.node.transform = value