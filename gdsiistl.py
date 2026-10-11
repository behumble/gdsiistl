#!/usr/bin/env python3
"""
This program converts a GDSII 2D layout file to multiple 3D STL files that can
be visualized in an external program (e.g., Blender).

USAGE:
    - run "gdsiistl draft-layers file.gds" to create an editable JSON draft
    - run "gdsiistl convert file.gds stack.json" to export STL files
OUTPUT:
    - the files file.gds_layername1.stl, file.gds_layername2.stl, ...

The program takes a path to a GDSII file. It reads shapes from
each layer of the GDSII file, converts them to polygon boundaries, then makes
a triangle mesh for each GDSII layer by extruding the polygons to given sizes.

All units, including the units of the exported file, are the GDSII file's
user units (often microns).
"""

import argparse
import json
import math
from pathlib import Path
import gdspy # open gds file
from stl import mesh # write stl file (python package name is "numpy-stl")
import numpy as np # fast math on lots of points
import triangle # triangulate polygons

parser = argparse.ArgumentParser(description='Convert GDSII layers into STL meshes')
commands = parser.add_subparsers(dest='command', required=True)
draft_parser = commands.add_parser('draft-layers', help='write an editable layerstack JSON from a GDSII file')
draft_parser.add_argument('gds', help='input GDSII file')
convert_parser = commands.add_parser('convert', help='convert selected GDSII layers to STL files')
convert_parser.add_argument('gds', help='input GDSII file')
convert_parser.add_argument('layerstack', help='JSON file with z ranges and output names')
args = parser.parse_args()
gdsii_file_path = args.gds

########## INPUT ##############################################################

# First, the input file is read using the gdspy library, which interprets the
# GDSII file and formats the data Python-style.
# See https://gdspy.readthedocs.io/en/stable/index.html for documentation.
# Second, the boundaries of each shape (polygon or path) are extracted for
# further processing.

print('Reading GDSII file {}...'.format(gdsii_file_path))
gdsii = gdspy.GdsLibrary()
gdsii.read_gds(gdsii_file_path, units='import')

print('Extracting polygons...')
layers = {} # geometry keyed by (GDSII layer, datatype)

cells = gdsii.top_level() # get all cells that aren't referenced by another
for cell in cells: # loop through cells to read paths and polygons

    # $$$CONTEXT_INFO$$$ is a separate, non-standard compliant cell added
    # optionally by KLayout to store extra information not needed here.
    # see https://www.klayout.de/forum/discussion/1026/very-
    # important-gds-exported-from-k-layout-not-working-on-cadence-at-foundry
    if cell.name == '$$$CONTEXT_INFO$$$':
        continue # skip this cell

    # Include paths and referenced cells while retaining layer and datatype.
    for spec, polygons in cell.get_polygons(by_spec=True).items():
        layers.setdefault(tuple(map(int, spec)), []).extend(
            (poly, None, False) for poly in polygons
        )

if not layers:
    parser.error('no polygon geometry found in the GDSII file')

if args.command == 'draft-layers':
    draft_path = Path(gdsii_file_path + '.layerstack.json')
    generated = {
        f'{layer}/{datatype}': {
            'zmin': index,
            'zmax': index + 1,
            'name': f'layer_{layer}_datatype_{datatype}',
        }
        for index, (layer, datatype) in enumerate(sorted(layers))
    }
    try:
        with draft_path.open('x', encoding='utf-8') as stack_file:
            json.dump(generated, stack_file, indent=2)
            stack_file.write('\n')
    except FileExistsError:
        parser.error(f'{draft_path} already exists; edit it or move it before drafting again')
    print(f'Created {draft_path}. Edit names if needed; z ranges are illustrative 1-unit steps.')
    print('For physical heights, edit zmin and zmax before converting.')
    print('Then run:')
    print(f'    gdsiistl convert {gdsii_file_path} {draft_path}')
    raise SystemExit(0)

stack_path = Path(args.layerstack)
print(f'Using layerstack {stack_path}...')
with stack_path.open(encoding='utf-8') as stack_file:
    configured = json.load(stack_file)
if not isinstance(configured, dict):
    parser.error('layerstack must be a JSON object keyed by "layer/datatype"')
if not configured:
    parser.error('layerstack must contain at least one layer/datatype entry')
layerstack = {}
output_names = set()
for key, entry in configured.items():
    try:
        layer, datatype = (int(part) for part in key.split('/'))
        zmin = float(entry['zmin'])
        zmax = float(entry['zmax'])
        name = entry['name']
    except (ValueError, TypeError, KeyError, AttributeError):
        parser.error(f'invalid layerstack entry {key!r}')
    if not (math.isfinite(zmin) and math.isfinite(zmax) and zmin < zmax):
        parser.error(f'invalid z range for {key!r}')
    if not isinstance(name, str) or not name or '/' in name or '\\' in name:
        parser.error(f'invalid output name for {key!r}')
    if name in output_names:
        parser.error(f'duplicate output name {name!r}')
    if (layer, datatype) not in layers:
        parser.error(f'layerstack entry {key!r} has no geometry in the GDSII file')
    if (layer, datatype) in layerstack:
        parser.error(f'duplicate layer/datatype entry {key!r}')
    layerstack[(layer, datatype)] = (zmin, zmax, name)
    output_names.add(name)

print('Layerstack:')
for spec, (zmin, zmax, name) in layerstack.items():
    print(f'    {spec[0]}/{spec[1]}: {zmin:g}..{zmax:g} ({name})')

"""
At this point, "layers" is a Python dictionary structured as follows:

layers = {
   (0, 0) : [ ([[x1, y1], [x2, y2], ...], None, False), ... ]
   (1, 0) : [ ... ]
   (2, 0) : [ ... ]
   ...
}

Each dictionary key is a GDSII (layer, datatype) pair, and the value of the
dictionary at that key (if it exists; keys were only created for layers with
geometry) is a list of polygons in that GDSII layer. Each polygon is a 3-tuple
whose first element is a list of points (2-element lists with x and y
coordinates), second element is None (for the moment; this will be used later),
and third element is False (whether the polygon is clockwise; will be updated).
"""

########## TRIANGULATION ######################################################

# An STL file is a list of triangles, so the polygons need to be filled with
# triangles. This is a surprisingly hard algorithmic problem, especially since
# there are few limits on what shapes GDSII file polygons can be. So we use the
# Python triangle library (documentation is at https://rufat.be/triangle/),
# which is a Python interface to a fast and well-written C library also called
# triangle (with documentation at https://www.cs.cmu.edu/~quake/triangle.html).

print('Triangulating polygons...')

num_triangles = {} # will store the number of triangles for each layer

# loop through all layers
for layer_number in sorted(layers):
    polygons = layers[layer_number]

    # but skip layer if it won't be exported
    if not layer_number in layerstack.keys():
        continue

    num_triangles[layer_number] = 0

    # loop through polygons in layer
    for index, (polygon, _, _) in enumerate(polygons):

        num_polygon_points = len(polygon)

        # determine whether polygon points are CW or CCW
        area = 0
        for i, v1 in enumerate(polygon): # loop through vertices
            v2 = polygon[(i+1) % num_polygon_points]
            area += (v2[0]-v1[0])*(v2[1]+v1[1]) # integrate area
        clockwise = area > 0

        # GDSII implements holes in polygons by making the polygon edge
        # wrap into the hole and back out along the same line. However,
        # this confuses the triangulation library, which fills the holes
        # with extra triangles. Avoid this by moving each edge back a
        # very small amount so that no two edges of the same polygon overlap.
        delta = 0.01 # inset each vertex by this much (smaller has broken one file)
        points_i = polygon # get list of points
        points_j = np.roll(points_i, -1, axis=0) # shift by 1
        points_k = np.roll(points_i, 1, axis=0) # shift by -1
        # calculate normals for each edge of each vertex (in parallel, for speed)
        normal_ij = np.stack((points_j[:, 1]-points_i[:, 1],
                              points_i[:, 0]-points_j[:, 0]), axis=1)
        normal_ik = np.stack((points_i[:, 1]-points_k[:, 1],
                              points_k[:, 0]-points_i[:, 0]), axis=1)
        length_ij = np.linalg.norm(normal_ij, axis=1)
        length_ik = np.linalg.norm(normal_ik, axis=1)
        normal_ij /= np.stack((length_ij, length_ij), axis=1)
        normal_ik /= np.stack((length_ik, length_ik), axis=1)
        if clockwise:
            normal_ij = -1*normal_ij
            normal_ik = -1*normal_ik
        # move each vertex inward along its two edge normals
        polygon = points_i - delta*normal_ij - delta*normal_ik

        # In an extreme case of the above, the polygon edge doubles back on
        # itself on the same line, resulting in a zero-width segment. I've
        # seen this happen, e.g., with a capital "N"-shaped hole, where
        # the hole split line cuts out the "N" shape but splits apart to
        # form the triangle cutout in one side of the shape. In any case,
        # simply moving the polygon edges isn't enough to deal with this;
        # we'll additionally mark points just outside of each edge, between
        # the original edge and the delta-shifted edge, as outside the polygon.
        # These parts will be removed from the triangulation, and this solves
        # just this case with no adverse affects elsewhere.
        hole_delta = 0.001 # small fraction of delta
        holes = 0.5*(points_j+points_i) - hole_delta*delta*normal_ij
        # HOWEVER: sometimes this causes a segmentation fault in the triangle
        # library. I've observed this as a result of certain various polygons.
        # Frustratingly, the fault can be bypassed by *rotating the polygons*
        # by like 30 degrees (exact angle seems to depend on delta values) or
        # moving one specific edge outward a bit. I have absolutely no idea
        # what is wrong. In the interest of stability over full functionality,
        # this is disabled. TODO: figure out why this happens and fix it.
        use_holes = False

        # triangulate: compute triangles to fill polygon
        point_array = np.arange(num_polygon_points)
        edges = np.transpose(np.stack((point_array, np.roll(point_array, 1))))
        if use_holes:
            triangles = triangle.triangulate(dict(vertices=polygon,
                                                  segments=edges,
                                                  holes=holes), opts='p')
        else:
            triangles = triangle.triangulate(dict(vertices=polygon,
                                                  segments=edges), opts='p')

        if not 'triangles' in triangles.keys():
            triangles['triangles'] = []

        # each line segment will make two triangles (for a rectangle), and the polygon
        # triangulation will be copied on the top and bottom of the layer.
        num_triangles[layer_number] += num_polygon_points*2 + \
                                       len(triangles['triangles'])*2
        polygons[index] = (polygon, triangles, clockwise)

"""
At this point, "layers" is as follows:

layers = {
   (0, 0) : [ ([[x1, y1], [x2, y2], ...],
          {'vertices': [[x1, y1], ...], 'triangles': [[0, 1, 2], ...], ...},
          clockwise), ... ]
   (1, 0) : [ ... ]
   (2, 0) : [ ... ]
   ...
}

Each dictionary key is a GDSII (layer, datatype) pair, and the value of the
dictionary at that key (if it exists; keys were only created for layers with
geometry) is a list of polygons in that GDSII layer. Each polygon has 3 parts:
First, a list of vertices, as before. Second, a dictionary with triangulation
information: the 'vertices' element contains vertex information stored the
same way as the main polygon vertices, and the 'triangles' element is a list
of which vertices correspond to which triangle (in counterclockwise order).
Third and finally, a boolean value that indicates whether the polygon was
defined clockwise (so that the STL triangles are oriented correctly).
"""

########## EXTRUSION ##########################################################

# Finally, now that we have polygon boundaries and triangulations, we can
# write it to an STL file. To make this fast (given there could be tens of
# thousands of triangles), we use the numpy-stl library, which uses numpy
# for somewhat accelerated vector math. See the documentation at
# (https://numpy-stl.readthedocs.io/en/latest/)

print('Extruding polygons and writing to files...')

# loop through all layers
for layer in sorted(layers):

    # but skip layer if it won't be exported
    if not layer in layerstack.keys():
        continue

    # Make a list of triangles.
    # This data contains vertex xyz position data as follows:
    # layer_mesh_data['vectors'] = [ [[x1,y1,z1], [x2,y2,z1], [x3,y3,z3]], ...]
    layer_mesh_data = np.zeros(num_triangles[layer], dtype=mesh.Mesh.dtype)

    layer_pointer = 0
    for index, (polygon, triangles, clockwise) in enumerate(layers[layer]):

        # The numpy-stl library expects counterclockwise triangles. That is,
        # one side of each triangle is the outside surface of the STL file
        # object (assuming a watertight volume), and the other side is the
        # inside surface. If looking at a triangle from the outside, the
        # vertices should be in counterclockwise order. Failure to do so may
        # cause certain STL file display programs to not display the
        # triangles correctly (e.g., the backward triangles will be invisible).

        zmin, zmax, layername = layerstack[layer]

        # make a list of triangles around the polygon boundary
        points_i = polygon # list of 2D vertices
        if clockwise: # order polygon 2D vertices counter-clockwise
            points_i = np.flip(polygon, axis=0)
        points_i_min = np.insert(points_i, 2, zmin, axis=1) # bottom left
        points_i_max = np.insert(points_i, 2, zmax, axis=1) # top left
        points_j_min = np.roll(points_i_min, -1, axis=0) # bottom right
        points_j_max = np.roll(points_i_max, -1, axis=0) # top right
        rights = np.stack((points_i_min, points_j_min, points_j_max), axis=1)
        lefts = np.stack((points_j_max, points_i_max, points_i_min), axis=1)

        # make a list of polygon interior (face) triangles
        vs = triangles['vertices']
        ts = triangles['triangles']
        if len(ts) > 0:
            face_tris = np.take(vs, ts, axis=0)
            top = np.insert(face_tris, 2, zmax, axis=2) # list of top triangles
            bottom = np.insert(face_tris, 2, zmin, axis=2) # list of bottom ~
            bottom = np.flip(bottom, axis=1) # reverse vertex order to make CCW
            faces = np.concatenate((lefts, rights, top, bottom), axis=0)
        else: # didn't generate any triangles! (degenerate edge case)
            faces = np.concatenate((lefts, rights), axis=0)

        # add side and face triangles to layer mesh
        layer_mesh_data['vectors'][layer_pointer:(layer_pointer+len(faces))] = faces
        layer_pointer += len(faces)

    # save layer to STL file
    filename = gdsii_file_path + '_{}.stl'.format(layername)
    print('    ({}/{}, {}) to {}'.format(*layer, layername, filename))
    layer_mesh_object = mesh.Mesh(layer_mesh_data, remove_empty_areas=False)
    layer_mesh_object.save(filename)

print('Done.')
