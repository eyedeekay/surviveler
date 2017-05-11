# -*- coding: utf-8 -*-
"""
Module that handles the actual exporting in Wavefront .obj format.
"""
from collections import OrderedDict
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple

Vertex = Tuple[float, float, float]
Edge = Tuple[Vertex, Vertex]
Face = Tuple[Vertex, Vertex, Vertex, Vertex]
Mesh = List[Face]
ExportSettings = Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]

AXES = 'xyz'  # http://forum.wordreference.com/threads/axis-vs-axes.82527/
X_RIGHT, Y_FORWARD, Z_UP = 0, 1, 2
DEFAULT_EXPORT_SETTINGS = ('+x', '+z', '+y')


def parse_readable_export_settings(
        export_settings: Tuple[str, str, str]) -> ExportSettings:
    """
    See the doctest below:

    >>> parse_readable_export_settings(('+x', '-z', '+y'))
    ((0, 1), (2, -1), (1, 1))
    """
    ret = []  # type: List[Tuple[int, int]]
    sign_dic = {'-': -1, '+': 1}
    for s in export_settings:
        sign, axis = sign_dic[s[0]], AXES.index(s[1])
        ret.append((axis, sign))
    return ret[0], ret[1], ret[2]  # just to help mypy with returned tuple length


def export_vertex(
        vertex: Vertex, export_settings: ExportSettings) -> str:
    """
    Builds the Wavefront row of a vertex.

    >>> export_vertex((-7, 3, 5), export_settings=((0, 1), (1, 1), (2, 1)))
    'v -7.000000 3.000000 5.000000'
    >>> export_vertex((2, -1, 3), export_settings=((0, 1), (2, -1), (1, 1)))  # +x, -z, +y
    'v 2.000000 -3.000000 -1.000000'
    """
    # Tuple index must be an integer literal = mypy seems not support integer variables as indces for tuple
    right = vertex[export_settings[X_RIGHT][0]] * export_settings[X_RIGHT][1]  # type: ignore
    forward = vertex[export_settings[Y_FORWARD][0]] * export_settings[Y_FORWARD][1]  # type: ignore
    up = vertex[export_settings[Z_UP][0]] * export_settings[Z_UP][1]  # type: ignore
    return 'v ' + ' '.join(['{:.6f}'.format(component) for component in (right, forward, up)])


def export_face_indices(face_indices: Iterable[int], zero_index: bool=False) -> str:
    """Returns the Wavefront row representation of a face.

    NB: accepts indices and NOT vertices coordinates.

    >>> export_face_indices((1, 5, 6, 2))
    'f 1 5 6 2'
    """
    return 'f ' + ' '.join([str(vertex_index + zero_index) for vertex_index in face_indices])


def mesh2vertices(mesh: Mesh) -> Dict[Vertex, int]:
    """
    Extracts unique vertices from mesh faces.
    """
    ret = OrderedDict()  # type: Dict[Vertex, int]

    unique = set()
    for face in mesh:
        for vertex in face:
            unique.add(vertex)

    for i, vertex in enumerate(sorted(list(unique)), 1):
        ret[vertex] = i

    return ret


def export_mesh(
        mesh: List[Face],
        readable_export_settings: Tuple[str, str, str]=DEFAULT_EXPORT_SETTINGS) -> str:
    """
    Returns a Wavefront representation of a mesh (list of faces).
    """
    ret = []

    export_settings = parse_readable_export_settings(readable_export_settings)

    vertices_indices = mesh2vertices(mesh)
    for vertex in sorted(vertices_indices.keys()):
        ret.append(export_vertex(vertex, export_settings))

    for face in mesh:
        face_indices = tuple([vertices_indices[vertex] for vertex in face])
        ret.append(export_face_indices(face_indices))

    return '\n'.join(ret)


def create_wavefront(
        vertices: List[Vertex]=[],
        faces: List[Tuple[int, ...]]=[],
        zero_index: bool=False,
        triangulate_result: dict=None,
        readable_export_settings: Tuple[str, str, str]=DEFAULT_EXPORT_SETTINGS,
        dst: str=None) -> str:
    """
    Create a wavefront given a list of vertices and faces.
    Save to `dst` if given, else return a string.
    """

    ret_list = []
    errors = []
    unique_vertices = []  # type: List[Vertex]

    if triangulate_result:
        # Use `vertices` and `faces` from the result of triangulation
        # overwriting `vertices` and `faces` with `vertices` and `triangles`,
        # and setting `zero_index` to True.
        faces = triangulate_result['triangles']
        vertices = []
        for v in triangulate_result['vertices']:
            if len(v) == 3:
                vertices.append(v)
            elif len(v) == 2:
                vertices.append((v[0], v[1], 0.0))
            else:
                raise Exception('Invalid length vertex: {}'.format(v))

        zero_index = True

    export_settings = parse_readable_export_settings(readable_export_settings)

    # Export vertices
    for i, vertex in enumerate(vertices):
        print('Vertex {}: {}'.format(i, vertex))
        ret_list.append(export_vertex(vertex, export_settings=export_settings))
        if vertex in unique_vertices:
            print('WARNING: duplicated vertex {}: {}'.format(i, vertex))
        else:
            unique_vertices.append(vertex)

    # Export faces
    for i, face in enumerate(faces):
        print('Face {}: {}'.format(i, face))
        if 0 in face and not zero_index:
            msg = 'ERROR: face #{i}={face} is a 0-index face, but zero_index is {zero_index}'.format(i=i, face=face, zero_index=zero_index)
            print(msg)
            errors.append(face)
        ret_list.append(export_face_indices(face, zero_index=zero_index))

    assert not errors, '{} zero_index face errors occurred: {}'.format(len(errors), errors)

    ret = '\n'.join(ret_list)
    if dst:
        with open(dst, 'w') as fp:
            fp.write(ret)
    return ret
