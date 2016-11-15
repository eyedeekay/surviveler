"""The user interface package"""
from enum import Enum


class Anchor(dict):
    """Represents the sets of anchors of a specified item.
    """

    class AnchorType(Enum):
        """Type of anchors.
        """
        top = 'top'
        left = 'left'
        bottom = 'bottom'
        right = 'right'
        vcenter = 'vcenter'
        hcenter = 'hcenter'

    def __init__(self, **anchors):
        """Constructor.

        :param **anchors: The named anchor values
        :type **anchors: :class:`dict`
        """
        for a in Anchor.AnchorType:
            anc = anchors.get(a.name)
            if anc:
                target, t = anc.split('.')
                self[a] = (target, Anchor.AnchorType(t))

    @classmethod
    def fill(cls):
        """Factory for fill-anchor.

        This is just a shortcut for an anchor that completely fills the parent.

        :returns: The generated fill anchor
        :rtype: :class:`Anchor`
        """
        return cls(
            left='parent.left',
            right='parent.right',
            top='parent.top',
            bottom='parent.bottom')

    @classmethod
    def center(cls):
        """Factory for center-anchor.

        This is just a shortcut for an anchor that puts the item in the center
        of the parent.

        :returns: The generated center anchor
        :rtype: :class:`Anchor`
        """
        return cls(vcenter='parent.vcenter', hcenter='parent.vcenter')


class Margin(dict):
    """Represents the sets of margins of a specified item.
    """

    class MarginType(Enum):
        """Type of margins.
        """
        top = 'top'
        left = 'left'
        bottom = 'bottom'
        right = 'right'

    def __init__(self, **margins):
        """Constructor.

        :param **margins: The named margin values
        :type **margins: :class:`dict`
        """
        for m in Margin.MarginType:
            margin = margins.get(m.name)
            if margin:
                self[m] = margin

    @classmethod
    def null(cls):
        return cls.symmetric(0)

    @classmethod
    def symmetric(cls, x_axis, y_axis=None):
        y_axis = y_axis or x_axis
        return cls(left=x_axis, right=x_axis, top=y_axis, bottom=y_axis)


class UI:
    """Container of the whole UI.
    """

    def __init__(self):
        """Constructor.
        """
        self.ui = {}

    def push_item(self, data, parent, **overrides):
        """Creates a new item inspecting the resource and push it into the ui.

        :param data: The item data
        :type data: :class:`dict`

        :param parent: The parent item
        :type parent: :class:`type`

        :param **overrides: The overrides to apply to the item appearance
            definition.
        :type **overrides: :class:`dict`

        :returns: The id of the item
        :rtype: :class:`str`
        """
        # TODO: inspect for the proper type of the item and create it.
        pass

    def pop_item(self, item_id):
        """Pops the item identified by the provided id
        :param item_id: The item id
        :type item_id: :class:`ui.item.Item`
        """
        pass
