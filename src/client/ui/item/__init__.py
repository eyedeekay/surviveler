"""The base item module"""

from .binding import Binding
from abc import ABCMeta
from abc import abstractmethod
from collections import OrderedDict
from functools import partial


class Item(metaclass=ABCMeta):
    """The basic item class.

    All the user interface items will inherit this abstract item class.
    """

    def __init__(self, parent, **kwargs):
        """Constructor.

        :param parent: The parent item
        :type parent: :class:`Item`

        Keyword Arguments:
            * position (:class:`..point.Point`): The item position relative to
                the parent
            * width (:class:`int`): The item width
            * height (:class:`int`): The item height
            * anchor (:class:`..Anchor`): The item anchor override
            * margin (:class:`..Margin`): The item margin override
        """
        self.parent = parent
        self.children = OrderedDict()

        # Geometry properties
        self._position = kwargs.get('position')
        self._width = kwargs.get('width')
        self._height = kwargs.get('height')
        self._anchor = kwargs.get('anchor')
        self._margin = kwargs.get('margin')

    def __getattribute__(self, name):
        """Override of the standard __getattribute__ method.

        This override is needed for runtime property binding.

        This method is used to check if the required item conform to the
        Descriptor protocol and in case use it to get the actual value.

        :param name: The name of the attribute
        :type name: :class:`str`
        """
        value = super().__getattribute__(name)
        if hasattr(value, '__get__'):
            value = value.__get__(self, self.__class__)
        return value

    def __setattr__(self, name, value):
        """Override of the standard __setattr__ method.

        This override is needed for runtime property binding.

        This method is used to check if the required item conform to the
        Descriptor protocol and in case use it to set the new value.

        :param name: The name of the attribute
        :type name: :class:`str`

        :param value: The new value for the bound property
        :type value: type of the bound property
        """
        try:
            obj = super().__getattribute__(name)
        except AttributeError:
            pass
        else:
            if hasattr(obj, '__set__'):
                return obj.__set__(self, value)
        return super().__setattr__(name, value)

    @property
    def position(self):
        """TODO: add documentation
        """
        if self._position is not None:
            return self._position + self.parent.position
        elif self._anchor:
            raise NotImplementedError
        else:
            return self.parent.position

    @property
    def width(self):
        """TODO: add documentation
        """
        if self._width is not None:
            return self._width
        elif self._anchor:
            raise NotImplementedError
        else:
            return 0

    @property
    def height(self):
        """TODO: add documentation
        """
        if self._height is not None:
            return self._height
        elif self._anchor:
            raise NotImplementedError
        else:
            return 0

    @property
    def anchor(self):
        """TODO: add documentation
        """
        return self._anchor

    @property
    def margin(self):
        """TODO: add documentation
        """
        return self._margin

    def get_child(self, ref):
        """Get a child by reference.

        :param ref: The name that identifies internally the child
        :type ref: :class:`str`

        :returns: The item referred by ref
        :rtype: :class:`ui.item.Item`
        """
        return self.children[ref]

    def get_sibling(self, item):
        """Get a sibling.

        In case there are no siblings, the parent itself is returned.

        :param item: The item that are referring to the sibling.
        :type item: :class:`ui.item.Item`

        :returns: The sibling item (or the parent in case of no siblings)
        :rtype: :class:`ui.item.Item`
        """
        sibling = self
        for ref, child in self.children.items():
            if child == item:
                return sibling
            sibling = child

    def add_child(self, ref, item, **properties):
        """Attaches a child to the item, and binds the properties.

        :param ref: The name that identifies internally the child
        :type ref: :class:`str`

        :param item: The actual item to be added as child
        :type item: :class:`ui.item.Item`

        :param **properties: A mapping of the properties to be bound
        :type **properties: :class:`dict`
        """
        self.children[ref] = item

        for binding, prop in properties.items():
            getter = partial(getattr, self.children[ref], prop)
            setter = partial(setattr, self.children[ref], prop)
            print(binding, prop, repr(getter()))
            setattr(self, binding, Binding(getter, setter))

    @abstractmethod
    def update(self, dt):
        """Item update method.

        This method should be implemented by subclasses of Item. It describes
        the behavior the class should have during updates.

        :param dt: The time delta since last update (in seconds)
        :type dt: :class:`float`
        """
        pass