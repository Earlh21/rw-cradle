from Level import Point, Level, Tile
from typing import Callable, List
import math
import numpy as np

def __bounce(
    level: Level, 
    start: Point, 
    vel: np.array, 
    max_length, wall_func: Callable[[Tile], bool] = lambda p: p.is_wall()):

    pos = np.array([float(start.x), float(start.y)])

    prev_point = start

    for i in range(int(max_length)):
        prev_point = Point(int(pos[0]), int(pos[1]))
        pos += vel
        p = Point(int(pos[0]), int(pos[1]))

        # Just stop if current point is in a wall
        if wall_func(level.tiles[p.x][p.y]):
            return False, prev_point, None

        # Also stop if the next point is out of bounds
        next_point = Point(int(pos[0] + vel[0]), int(pos[1] + vel[1]))
        if not level.is_point_in_bounds(next_point):
            return False, Point(int(pos[0]), int(pos[1])), None

        # If the next point is in a wall, check for a bounce
        if wall_func(level.tiles[next_point.x][next_point.y]):
            bounce_horizontal = False
            bounce_vertical = False

            # For each axis, check the direction that the line is moving in
            if vel[0] > 0 and level.is_point_in_bounds(Point(p.x + 1, p.y)) and wall_func(level.tiles[p.x + 1][p.y]):
                bounce_horizontal = True

            if vel[0] < 0 and level.is_point_in_bounds(Point(p.x - 1, p.y)) and wall_func(level.tiles[p.x - 1][p.y]):
                bounce_horizontal = True
            
            if vel[1] > 0 and level.is_point_in_bounds(Point(p.x, p.y + 1)) and wall_func(level.tiles[p.x][p.y + 1]):
                bounce_vertical = True

            if vel[1] < 0 and level.is_point_in_bounds(Point(p.x, p.y - 1)) and wall_func(level.tiles[p.x][p.y - 1]):
                bounce_vertical = True
            
            if bounce_horizontal:
                vel[0] = -vel[0]
            
            if bounce_vertical:
                vel[1] = -vel[1]
            
            if bounce_horizontal or bounce_vertical:
                return True, p, vel
    
    return False, Point(int(pos[0]), int(pos[1])), vel


def get_bouncing_line_endpoints(
    level: Level,
    start: Point,
    angle: float,
    max_length: float,
    wall_func: Callable[[Tile], bool] = lambda p: p.is_wall()) -> List[Point]:
    """
    Finds the endpoints of a bouncing line through the given level. A new endpoint is found every time the line bounces.
    
    wall_func: takes a tile and returns whether it should be bounced off of.
    """
    endpoints = [start]

    length_left = max_length
    vel = np.array([math.cos(angle), math.sin(angle)])

    current = start

    while length_left > 0:
        continue_line, end_point, vel = __bounce(level, current, vel, length_left, wall_func)

        if not continue_line:
            endpoints.append(end_point)
            length_left = 0
        else:
            endpoints.append(end_point)

            length_left -= math.sqrt((end_point.x - current.x) ** 2 + (end_point.y - current.y) ** 2)
            # Remove a bit of length to avoid any infinite loops, just in case
            length_left -= 0.5

            current = end_point

    return endpoints

def get_bouncing_line(
    level: Level,
    start: Point,
    angle: float,
    max_length: float,
    repeat_tiles: bool = False,
    wall_func: Callable[[Tile], bool] = lambda p: p.is_wall()) -> List[Point]:
    """
    Returns the points of a bouncing line through the given level.

    repeat_tiles: whether to repeat tiles if the line passes through more than once.
    wall_func: takes a tile and returns whether it should be bounced off of.
    """
    tiles = []
    endpoints = get_bouncing_line_endpoints(level, start, angle, max_length, wall_func)

    for i in range(len(endpoints) - 1):
        tiles.extend(level.get_points_in_line(endpoints[i], endpoints[i + 1]))

    if not repeat_tiles:
        # Can't use list(set()) because it doesn't preserve order
        no_dupes = []
        [no_dupes.append(t) for t in tiles if t not in no_dupes]
        return no_dupes
    
    return tiles

def get_perp_point(source, dest, length, direction):
    dx = dest.x - source.x
    dy = dest.y - source.y

    longer_len = max(abs(dy), abs(dx))
    dx /= longer_len
    dy /= longer_len

    return Point(round(source.x + dy * length * direction), round(source.y - dx * length * direction))

def has_adjacent_wall(level, x, y):
    for point in level.get_adjacent_points(Point(x, y), filter_walkable = False):
        if level.tiles[point.x][point.y].is_wall():
            return True
    return False

def has_adjacent_chasm(level, x, y):
    for point in level.get_adjacent_points(Point(x, y), filter_walkable = False):
        tile = level.tiles[point.x][point.y]
        if tile.is_chasm:
            return True
    return False