#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from scipy.spatial import Delaunay
import numpy as np
import math
import sys

def check_alpha_disk(alpha, v0, v1, points):
    if alpha == 0.0:
        # y = mx + c, boundary of half plane
        x0, y0 = points[v0]
        x1, y1 = points[v1]

        if x1 - x0 == 0: # degenerate case of half plane
            # Check half plane x <= x0
            spanning_half_plane_left = True
            for (i, point) in enumerate(points):
                if i == v0 or i == v1:
                    continue
                if point[0] > x0:
                    spanning_half_plane_left = False


                    break;
            if spanning_half_plane_left:
                return True

            # Check half plane x >= x0
            spanning_half_plane_right = True
            for (i, point) in enumerate(points):
                if i == v0 or i == v1:
                    continue
                if point[0] < x0:
                    spanning_half_plane_right = False
                    break;
            if spanning_half_plane_right:
                return True
            else:
                return False
        else:
            m = (y1 - y0) / (x1 - x0)
            c = y0 - m * x0

            # Check the half plane y >= mx+c
            spanning_half_plane_above = True
            for (i, point) in enumerate(points):
                if i == v0 or i == v1:
                    continue
                if point[1] < m*point[0] + c:
                    spanning_half_plane_above = False
                    break;
            if spanning_half_plane_above:
                return True

            # Check the half plane y <= mx+c
            spanning_half_plane_below = True
            for (i, point) in enumerate(points):
                if i == v0 or i == v1:
                    continue
                if point[1] > m*point[0] + c:
                    spanning_half_plane_below = False
                    break;

            if spanning_half_plane_below:
                return True
            else:
                return False
    elif alpha > 0:
        def normalize(v):
            norm = np.linalg.norm(v)
            if norm == 0:
                return v
            else:
                return v / norm

        # find the centres of the spanning disks to check
        dv = points[v1] - points[v0]
        if (1 / alpha)**2 < (np.linalg.norm(dv)/2)**2:
            return False
        perp_offset = math.sqrt((1 / alpha)**2 - (np.linalg.norm(dv)/2)**2)
        dv_perp = perp_offset * normalize(np.array([-dv[1], dv[0]]))
        disk_1 = (points[v0] + points[v1])/2 + dv_perp
        disk_2 = (points[v0] + points[v1])/2 - dv_perp

        r2 = (1 / alpha)**2
        epsilon = 1e-5
        # check if disks are spanning the set of points
        spanning_disk_1 = True
        for (i, point) in enumerate(points):
            if i == v0 or i == v1:
                continue
            if sum((point - disk_1)**2) < r2 - epsilon:
                spanning_disk_1 = False
                break;
        if spanning_disk_1:
            return True

        spanning_disk_2 = True
        for (i, point) in enumerate(points):
            if i == v0 or i == v1:
                continue
            if sum((point - disk_2)**2) < r2 - epsilon:
                spanning_disk_2 = False
                break;
        if spanning_disk_2:
            return True
        else:
            return False

    elif alpha < 0:
        pass

def alpha_shape_brute(alpha, points):
    edges = []
    points = np.array(points)
    for v_i in range(len(points)):
        for v_j in range(v_i):
            if v_i == v_j:
                continue
            if check_alpha_disk(alpha, v_i, v_j, points):
                edges.append([v_i, v_j])
    return np.array(edges)

def draw(edges, points, alpha = None):
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    points = np.array(points)
    edge_points = []
    for edge in edges:
        edge_points.append([points[edge[0]], points[edge[1]]])
    lines = LineCollection(edge_points)
    plt.figure()
    plt.title('Alpha={} Delaunay triangulation'.format(alpha))
    plt.gca().add_collection(lines)
    plt.plot(points[:,0], points[:,1], 'o')
    plt.show()

def sort_perimeter(edges):
    """
    From a list of edges, output a list of vertex indices
    """
    lookup_table = {}

    def add_edge(edge):
        if edge[0] in lookup_table:
            lookup_table[edge[0]].append(edge)
        else:
            lookup_table[edge[0]] = [edge]
        if edge[1] in lookup_table:
            lookup_table[edge[1]].append(edge)
        else:
            lookup_table[edge[1]] = [edge]

    def del_edge(edge):
        lookup_table[edge[0]].remove(edge)
        lookup_table[edge[1]].remove(edge)

    start_point = None
    for edge in edges:
        add_edge(edge)
        start_point = edge[0]

    current_point = start_point
    result = []
    while True:
        edge = lookup_table[current_point][0]
        result.append(edge)

        if edge[1] == current_point:
            current_point = edge[0]
        else:
            current_point = edge[1]
        del_edge(edge)

        if current_point == start_point:
            break;


    # check the winding of the path
    winding = 0
    last_point = result[-1]

    i = 0
    while i < len(result):
        if result[i-1] == result[i]:
            result.pop(i)
            continue
        else:
            last_point = result[i-1]
            point = result[i]
            winding += (point[0] - last_point[0]) * (point[1] + last_point[1])
            i += 1

    if winding > 0:
        # force anticlockwise winding
        result.reverse()

    return result


def alpha_shape(alpha, points):
    """
    Returns (triangles, perimeter)
    triangles: the triangles use to construct the alpha shape
    perimeter: the perimeter of the alpha shape in the anticlockwise direction

    based of code from
    https://sgillies.net/2012/10/13/the-fading-shape-of-alpha.html
    """
    triangles = set()
    alpha_shape_edges = {}

    points = np.array(points)
    triangulation = Delaunay(points)

    def add_triangle(i, j, k):
        def add_edges(i, j):
            if (i, j) in alpha_shape_edges:
                alpha_shape_edges[(i, j)] += 1
            else:
                alpha_shape_edges[(i, j)] = 1

        tri = tuple(sorted((i, j, k)))
        add_edges(tri[0], tri[1])
        add_edges(tri[1], tri[2])
        add_edges(tri[0], tri[2])
        if tri in triangles:
            # already added
            return
        triangles.add(tri)

    epsilon = 1e-6

    # loop over triangles:
    # ia, ib, ic = indices of corner points of the triangle
    for ia, ib, ic in triangulation.vertices:
        pa = points[ia]
        pb = points[ib]
        pc = points[ic]

        # Lengths of sides of triangle
        a_2 = (pa[0]-pb[0])**2 + (pa[1]-pb[1])**2
        b_2 = (pb[0]-pc[0])**2 + (pb[1]-pc[1])**2
        c_2 = (pc[0]-pa[0])**2 + (pc[1]-pa[1])**2

        # derived from Herons formula
        area_squared_times_16 = \
            4 * (a_2*b_2 + a_2*c_2 + b_2*c_2) - (a_2 + b_2 + c_2)**2

        circum_r_2 = a_2*b_2*c_2 / (area_squared_times_16 + epsilon)

        # Here's the radius filter.
        if circum_r_2 < (1.0/alpha)**2:
            add_triangle(ia, ib, ic)


    # Find the perimeter using the edge list. Edges on the perimeter will be
    # added to the list only once
    perimeter = []
    for edge in alpha_shape_edges:
        if alpha_shape_edges[edge] == 1:
            perimeter.append(list(edge))

    perimeter = sort_perimeter(perimeter)

    # draw_tris(triangles, points, perimeter, alpha=alpha)
    return triangles, perimeter


def draw_tris(triangles, points, perimeter, alpha = None):
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    points = np.array(points)

    edge_points = []
    for tri in triangles:
        edge_points.append([points[tri[0]], points[tri[1]]])
        edge_points.append([points[tri[1]], points[tri[2]]])
        edge_points.append([points[tri[2]], points[tri[0]]])
    lines = LineCollection(edge_points)

    perimeter_edges = []
    for edge in perimeter:
        perimeter_edges.append([points[edge[0]], points[edge[1]]])
    perimeter_edges = np.array(perimeter_edges)
    perimeter_lines = LineCollection(perimeter_edges, colors='r')
    # help(LineCollection, color='red')
    # perimeter = np.array(perimeter)

    plt.figure()
    plt.title('Alpha={} Delaunay triangulation'.format(alpha))
    plt.gca().add_collection(lines)
    plt.gca().add_collection(perimeter_lines)
    plt.plot(points[:,0], points[:,1], 'o')
    plt.show()


if __name__ == '__main__':
    points = np.random.rand(100, 2)
    # # points = np.loadtxt("points.txt")

    # edges = alpha_shape_brute(alpha, points)
    # # print(edges)

    # draw(edges, points)

    alpha = 9.002

    _, perimeter = alpha_shape(alpha, points)
