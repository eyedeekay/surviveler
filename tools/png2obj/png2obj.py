# -*- coding: utf-8 -*-
"""
Main module to create a Wavefront obj file from a png one.

Involved steps:
    1 - convert a png to a walkable matrix;
    2 - find wall perimeters -> list of 2D edges;
    3 - extrude vertically the wall perimeters -> list of 3D faces;
    4 - export faces to obj.

Python-3 only due to the type hinting (and 'super') syntax.

Glossary (to try to make some clearness):
    * box - an element in the walkable matrix, with coordinates (x, y)
    * block - a non-walkable box
    * vertex - a 2/3D point in a 2/3D space (used to describe wall perimeters and meshes)
    * wall perimeter - a 2D closed planar (z=0) polygon which corresponds to the wall borders
        (from a "top" view perspective).
        If the wall is open, you have 1 perimeter for 1 wall.
        If the wall is closed, you have an internal wall perimeter and an external one.
        Each png or level may consists of several separated walls.
"""
from extruder import extrude_wall_perimeters
from wavefront import export_mesh
from PIL import Image
from collections import deque
from collections import namedtuple
from collections import Counter
from collections import OrderedDict
from typing import Dict  # noqa
from typing import Iterable
from typing import List
from typing import Mapping
from typing import NamedTuple
from typing import Set  # noqa
from typing import Tuple
import argparse
import os
import time
import triangle
import turtle

Pos = Tuple[int, int]
Versor2D = Tuple[int, int]
Vertex2D = Tuple[float, float]
Vector2D = Vertex2D
Vertex3D = Tuple[float, float, float]
Triangle2D = Tuple[Vertex2D, Vertex2D, Vertex2D]
Triangle3D = Tuple[Vertex3D, Vertex3D, Vertex3D]
WallPerimeter = List[Vertex2D]
WalkableMatrix = List[List[int]]
VertexBoxes = NamedTuple('NearBoxes',
    [
        ('upleft', Pos),
        ('upright', Pos),
        ('downright', Pos),
        ('downleft', Pos),
    ]
)


Box = namedtuple('Box', ['x', 'y'])
NearVertices = namedtuple('NearVertices', ['left', 'up', 'right', 'down'])


LEFT = (-1, 0)
UP = (0, -1)
RIGHT = (1, 0)
DOWN = (0, 1)
HERE = (0, 0)
STILL = (0, 0)
VERSOR_NAME = {
    LEFT: 'left', UP: 'up', RIGHT: 'right', DOWN: 'down', HERE: 'here'
}  # type: Dict[Vector2D, str]

# Angles for the turtle
ANGLES = {LEFT: 270, UP: 0, RIGHT: 90, DOWN: 180}  # type: Dict[Vertex2D, int]


# A vertex ha 4 neighbour boxes, and each box can be walkable or not (block).
# This map represents every case with relative "mouvement" possibility
# of a vertex to track the wall perimeter.

POSSIBLE_DIRECTIONS = {
    ((0, 0),
     (0, 0)): (),
    ((0, 0),
     (0, 1)): (RIGHT, DOWN),
    ((0, 0),
     (1, 0)): (LEFT, DOWN),
    ((0, 0),
     (1, 1)): (LEFT, RIGHT),
    ((0, 1),
     (0, 0)): (UP, RIGHT),
    ((0, 1),
     (0, 1)): (UP, DOWN),
    ((0, 1),
     (1, 0)): (LEFT, UP, RIGHT, DOWN),
    ((0, 1),
     (1, 1)): (LEFT, UP),
    ((1, 0),
     (0, 0)): (LEFT, UP),
    ((1, 0),
     (0, 1)): (LEFT, UP, RIGHT, DOWN),
    ((1, 0),
     (1, 0)): (UP, DOWN),
    ((1, 0),
     (1, 1)): (UP, RIGHT),
    ((1, 1),
     (0, 0)): (LEFT, RIGHT),
    ((1, 1),
     (0, 1)): (LEFT, DOWN),
    ((1, 1),
     (1, 0)): (RIGHT, DOWN),
    ((1, 1),
     (1, 1)): (),
}  # type: Dict[Tuple[Vector2D, Vector2D], Tuple[Vector2D, ...]]


RULES = {
    ((0, 0),
     (0, 0)): {STILL: STILL, UP: UP, LEFT: LEFT, RIGHT: RIGHT, DOWN: DOWN},  # XXX
    ((0, 0),
     (0, 1)): {STILL: RIGHT, UP: RIGHT, LEFT: DOWN},
    ((0, 0),
     (1, 0)): {STILL: DOWN, UP: LEFT, RIGHT: DOWN},
    ((0, 0),
     (1, 1)): {STILL: RIGHT, RIGHT: RIGHT, LEFT: LEFT},
    ((0, 1),
     (0, 0)): {STILL: UP, LEFT: UP, DOWN: RIGHT},
    ((0, 1),
     (0, 1)): {STILL: UP, UP: UP, DOWN: DOWN},
    ((0, 1),
     (1, 0)): {STILL: RIGHT, UP: RIGHT, LEFT: DOWN, RIGHT: UP, DOWN: LEFT},
    ((0, 1),
     (1, 1)): {STILL: UP, RIGHT: UP, DOWN: LEFT},
    ((1, 0),
     (0, 0)): {STILL: LEFT, RIGHT: UP, DOWN: LEFT},
    ((1, 0),
     (0, 1)): {STILL: RIGHT, UP: LEFT, DOWN: RIGHT, LEFT: UP, RIGHT: DOWN},
    ((1, 0),
     (1, 0)): {STILL: UP, UP: UP, DOWN: DOWN},
    ((1, 0),
     (1, 1)): {STILL: RIGHT, LEFT: UP, DOWN: RIGHT},
    ((1, 1),
     (0, 0)): {STILL: RIGHT, LEFT: LEFT, RIGHT: RIGHT},
    ((1, 1),
     (0, 1)): {STILL: LEFT, UP: LEFT, RIGHT: DOWN},
    ((1, 1),
     (1, 0)): {STILL: RIGHT, UP: RIGHT, LEFT: DOWN},
    ((1, 1),
     (1, 1)): {STILL: STILL, UP: STILL, DOWN: STILL, LEFT: STILL, RIGHT: STILL},  # XXX
}  # type: Dict[Tuple[Vector2D, Vector2D], Dict[Versor2D, Versor2D]]


def sum_vectors(v1: Vector2D, v2: Vector2D) -> Vector2D:
    """Sums 2 bi-dimensional vectors.

    >>> v1 = (-1, 2)
    >>> v2 = (3.0, -10)
    >>> sum_vectors(v1, v2)
    (2.0, -8)
    """
    return (v1[0] + v2[0], v1[1] + v2[1])


def remove_internal_edge_points(vertices: List[Vertex2D]) -> List[Vertex2D]:
    """
    Leaves only the points that are in the corners.

    >>> points = [(0, 0), (0, 1), (0, 2), (0, 3), (-1, 3), (-2, 3), (-3, 3)]
    >>> remove_internal_edge_points(points)
    [(0, 0), (0, 3), (-3, 3)]
    """
    ret = [vertices[0]]
    for i in range(1, len(vertices) - 1):
        # Make the diff of 3 current contiguous vertices
        dx1 = vertices[i][0] - vertices[i - 1][0]
        dy1 = vertices[i][1] - vertices[i - 1][1]
        dx2 = vertices[i + 1][0] - vertices[i][0]
        dy2 = vertices[i + 1][1] - vertices[i][1]
        # If the 2 diffs are not equal:
        if (dx1 != dx2) or (dy1 != dy2):
            # the 3 vertices don't form a line, so get the median one
            ret.append(vertices[i])

    ret.append(vertices[-1])
    return ret


def remove_contiguous_values(lst: List[Tuple[float, float]]) -> None:
    """
    >>> lst = [1, 2, 8, 8, 8, 0, 0, 5]
    >>> remove_contiguous_values(lst)
    >>> lst
    [1, 2, 8, 0, 5]
    """
    i = 0
    while i < len(lst) - 1:
        if lst[i] == lst[i + 1]:
            del lst[i]
        else:
            i += 1


def normalized_perimeter(wall_perimeter: WallPerimeter) -> WallPerimeter:
    """
    Normalizes the wall perimeter to make it start from its topleft.

    >>> normalized_perimeter([(1, 0), (1, 1), (0, 1), (0, 0), (1, 0)])
    [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]
    """
    minimum = min(wall_perimeter)
    deq = deque(wall_perimeter)  # use deque just to use the rotate (circular shift)
    while deq[0] != minimum:
        deq.rotate(1)
    # The last item must be equal to the first by convention.
    deq.append(deq[0])
    ret = list(deq)
    # Remove contiguous duplicates, preserving order.
    remove_contiguous_values(ret)
    return ret


def matrix2holes(matrix: List[List[int]]) -> List[Vertex2D]:
    ret = []
    for y, row in enumerate(matrix):
        for x, walkable in enumerate(row):
            if walkable:
                ret.append((x + 0.5, y + 0.5))
    return ret


def list_to_index_map(the_list: list) -> OrderedDict:
    ret = OrderedDict()
    assert len(set(the_list)) == len(the_list), 'Error: the list contains duplicated elements'
    for i, element in enumerate(the_list):
        ret[element] = i
    return ret


def wall_perimeters_to_unique_vertices(wall_perimeters: List[WallPerimeter]) -> List[Vertex2D]:
    """
    >>> ret = wall_perimeters_to_unique_vertices([[(0, 0), (3, 0)], [(0, 1), (3, 0)]])
    >>> len(ret)
    3
    >>> ret[0]
    (0, 0)
    >>> ret[1]
    (3, 0)
    >>> ret[2]
    (0, 1)
    """
    ret = []
    for wall in wall_perimeters:
        for vertex in wall:
            if not vertex in ret:
                ret.append(vertex)
    return ret


def triangulate_walls(wall_perimeters: List[WallPerimeter], holes: List[Vertex2D]) -> List[Triangle2D]:
    """
    Creates the top horizontal surface of the walls.
    """
    ret = []

    # Fill the horizontal wall surfaces at the set `height`.
    unique_vertices = wall_perimeters_to_unique_vertices(wall_perimeters)
    vertices_indices = list_to_index_map(unique_vertices)
    segments = []
    v_segments = []
    i = 0

    for wall in wall_perimeters:
        assert wall[0] == wall[-1], 'The wall must be closed'

        # create wall segments, mapped to unique vertices
        for i in range(len(wall) - 1):
            va = wall[i]
            vb = wall[i + 1]
            v_segments.append((va, vb))
            segments.append((vertices_indices[va], vertices_indices[vb]))

    # check that match walls
    i = 0
    for iw, wall in enumerate(wall_perimeters):
        for ie in range(len(wall) -1):
            wall_vertex0 = wall[ie]
            wall_vertex1 = wall[ie + 1]
            wall_edge = wall_vertex0, wall_vertex1

            segment = segments[i]
            va = unique_vertices[segment[0]]
            vb = unique_vertices[segment[1]]
            va_vb = va, vb
            assert va_vb == wall_edge, '{} != {}'.format(va_vb, wall_edge)

            i += 1

    dic = dict(vertices=unique_vertices, segments=segments)
    if holes:
        dic['holes'] = holes  # otherwise triangulate might crash

    if not dic['vertices']:
        return []

    # <DEBUGGIBNG triangle.triangulate (export input parameters)>
    import pickle
    with open('dic.pkl', 'wb') as fp:
        pickle.dump(dic, fp)
    import pprint
    with open('dic.py', 'w') as fp:
        s = pprint.pformat(dic)
        fp.write('dic = {}'.format(s))
    # </ DEBUGGING>

    # ========= CALL THE C TRIANGLE LIBRARY ==========
    tri = triangle.triangulate(dic, 'pc')
    # ================================================

    # Now just convert triangles indices in triangles vertices
    for triangle_indices in tri['triangles']:
        face = []
        for vertex_index in triangle_indices:
            vertex = tri['vertices'][vertex_index]
            assert len(vertex) == 2, 'Expected a Vertex2D. Got: {}'.format(vertex)
            vertex = (vertex[0], vertex[1])
            face.append(vertex)
        ret.append((face[0], face[1], face[2]))
    return ret


class BlocksMap(dict):
    """
    Class to perform operation on a blocks map, a dict of non-walkable boxes
    (not exactly a walkable matrix).

    TODO: Use a walkable matrix instead, eventually.
    """
    def __init__(self, data: Mapping, map_size: Tuple[int, int], box_size: int=1) -> None:
        super().__init__(data)
        self.map = data
        self.map_size = map_size
        self.box_size = box_size

    def get_grid_vertices(self) -> Iterable[Vertex2D]:
        """Returns an iterator for all map virtual "grid" vertices,
        so regardless they are part of a wall or not.
        """
        width, height = self.map_size
        for bx in range(width):
            for by in range(height):
                x = bx * self.box_size
                y = by * self.box_size
                yield (x, y)

    def map_vertex(self, xy: Vertex2D) -> Pos:
        """Given a vertex position, returns the map box whose the
        vertex is the top-left one.
        """
        x, y = xy
        return int(x / self.box_size), int(y / self.box_size)

    def vertex2boxes(self, xy: Vertex2D) -> VertexBoxes:
        """Returns the 4 neighbour map boxes (white or not)
        which share the same given vertex.
        """
        bx, by = self.map_vertex(xy)
        return VertexBoxes(upleft=(bx - 1, by - 1), upright=(bx, by - 1), downleft=(bx - 1, by), downright=(bx, by))

    def boxes2block_matrix(self, boxes: VertexBoxes) -> Tuple[Pos, Pos]:
        """Given 4 vertex boxes, returns a 2x2 tuple with walkable/non-walkable info.
        """
        return ((self.map.get(boxes.upleft, 0), self.map.get(boxes.upright, 0)), (self.map.get(boxes.downleft, 0), self.map.get(boxes.downright, 0)))

    def build(self, debug: bool=False) -> List[List[Vertex2D]]:
        """Main method (edge detection): builds the list of wall perimeters.
        """
        ret = []  # type: List[WallPerimeter]

        if debug:
            turtle.mode('logo')
            turtle.speed(9)
            drawsize = int(300 / (1 + max(map(max, self.map)))) if self.map else 0  # type: ignore

        if not self.map:
            return []

        tracked_vertices = Counter()  # type: Dict[Vertex2D, int]

        for iv, vertex in enumerate(self.get_grid_vertices()):
            v_boxes = self.vertex2boxes(vertex)
            blocks_matrix = self.boxes2block_matrix(v_boxes)
            versors = POSSIBLE_DIRECTIONS[blocks_matrix]
            n_versors = len(versors)
            if n_versors == 0:
                # not a border verdex
                # inside 4 blocks or 4 empty cells
                continue

            n_passes = tracked_vertices[vertex]
            if n_versors == 4:
                # should pass by here exactly 2 times
                if n_passes > 1:
                    continue

            elif n_passes > 0:
                continue

            # start new wall perimeter from this disjointed block
            wall_perimeter = []

            first_vertex = vertex
            old_versor = (0, 0)  # like a `None` but supporting the array sum
            versor = old_versor
            wall_perimeter.append(vertex)
            wall_vertex = vertex

            if debug:
                turtle.penup()
                turtle.setpos(wall_vertex[0] * drawsize, -wall_vertex[1] * drawsize)
                turtle.pendown()

            while True:
                v_boxes = self.vertex2boxes(wall_vertex)
                blocks_matrix = self.boxes2block_matrix(v_boxes)
                versors = POSSIBLE_DIRECTIONS[blocks_matrix]
                tracked_vertices[wall_vertex] += (1 if len(versors) == 4 else 2)

                versor_next = RULES[blocks_matrix][versor]
                v_next = sum_vectors(wall_vertex, versor_next)

                wall_perimeter.append(v_next)

                old_versor = versor
                versor = versor_next
                wall_vertex = wall_perimeter[-1]

                if debug:
                    turtle.setheading(ANGLES[versor_next])
                    turtle.fd(drawsize)

                if wall_vertex == first_vertex:
                    break

            wall_perimeter = remove_internal_edge_points(wall_perimeter)
            wall_perimeter = normalized_perimeter(wall_perimeter)
            ret.append(wall_perimeter)

        ret.sort()
        return ret


def mat2map(matrix: WalkableMatrix) -> BlocksMap:
    """Creates a blocks map from a walkable matrix.
    """
    ret = {}
    for y, row in enumerate(matrix):
        for x, walkable in enumerate(row):
            if not walkable:
                ret[(x, y)] = 1
    return BlocksMap(ret, map_size=(x + 1, y + 1))


def load_png(filepath: str) -> WalkableMatrix:
    """Builds a walkable matrix from an image.
    """
    ret = []
    img = Image.open(filepath)
    for y in range(img.height):
        row = []
        for x in range(img.width):
            pixel = img.getpixel((x, y))
            if img.mode == 'P':
                walkable = int(pixel > 0)
            else:
                if img.mode == 'RGBA':
                    alpha = pixel[3]
                    walkable = alpha == 0 or pixel[:3] == (255, 255, 255)
                else:
                    walkable = pixel[:3] == (255, 255, 255)
            row.append(int(walkable))
        ret.append(row)
    return ret


def matrix2obj(matrix, dst, height=1):
    blocks_map = mat2map(matrix)
    print('Detecting edges...')
    t0 = time.time()
    wall_perimeters = sorted(blocks_map.build(debug=turtle))
    print('{:.2f} s'.format(time.time() - t0))

    mesh = extrude_wall_perimeters(wall_perimeters, height)
    print(mesh)

    print('Triangulation...')
    t0 = time.time()
    horizontal_faces = []  # type: List[Triangle3D]
    holes = matrix2holes(matrix)

    horizontal_faces = []
    for face2D in triangulate_walls(wall_perimeters, holes):
        h_face = []
        for v2D in face2D:
            h_face.append((v2D[0], v2D[1], height))
        horizontal_faces.append((h_face[0], h_face[1], h_face[2]))
    mesh.extend(horizontal_faces)
    print('{:.2f} s'.format(time.time() - t0))

    print('Exporting mesh to Wavefront...')
    t0 = time.time()
    with open(dst, 'w') as fp:
        fp.write(export_mesh(mesh))
    print('{:.2f} s'.format(time.time() - t0))
    obj_size = os.path.getsize(dst)
    print('{} created ({:,} byte).'.format(dst, obj_size))
    return obj_size


def png2obj(filepath: str, height: float=3, turtle: bool=False) -> int:
    """Main function which takes an image filepath and creates
    a mesh (detecting edges an extruding them vertically)
    exporting it in a wavefront obj format.

    Returns the size, in byte, of the obj created.
    """
    print('Loading {}...'.format(filepath))
    t0 = time.time()
    matrix = load_png(filepath)
    print('{:.2f} s'.format(time.time() - t0))

    dst = filepath[:-4] + '.obj'
    return matrix2obj(matrix, dst, height)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='png2obj: creates a 3D-level Wavefront obj from a png')
    parser.add_argument('src', help='the source png file path')
    parser.add_argument('--height', default=3.0, type=float,
                        help='vertical extrusion amount [default=%(default)s]')
    parser.add_argument('--turtle', type=bool, default=False, help='show steps graphically for debugging')
    args = parser.parse_args()
    png2obj(args.src, args.height, turtle=args.turtle)
