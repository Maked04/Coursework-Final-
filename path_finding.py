import pygame
from pygame.locals import *


# The grid class is used to store all tiles and it has methods for handling those tiles for example getting their
# neighbours and getting distances between tiles as it has the tiles stored in a matrix
class Grid:
    def __init__(self, size, map, w, h):
        # The size variable is for the size of each tile, they are square so no width and height needed
        self.size = size
        # The map is a 2d array of 1's and 0's where 1 represents a physical block which isn't traversable  and 0
        # is empty space so is traversable
        self.map = map
        # This is the width and height of the grid
        self.width, self.height = w, h
        # A 2d array of tile objects
        self.tiles = None
        # A method for resetting the tile objects
        self.reset_tiles()

    def point_to_grid(self, pos):
        # A point you may want to move to won't be the exact location of a tile so we need to find the tile that the
        # point exists in. We do this by taking the point then dividing by the size of a tile and then take the interger
        # of this which will effectively cut of the decimal places which gives us the index of the tile in one direction
        # we do this for the other axis to get the full index for the matrix of tiles
        x = int(pos[0] / self.size)
        y = int(pos[1] / self.size)
        # Return the tile that is at that index
        return self.tiles[y][x]

    def get_neighbours(self, tile):
        neighbours = []
        # The faster method would be to check a 3x3 area around the current tile but ignoring the tile as it's
        # not it's own neighbour, in the use of the path finding in the game however we don't want the moving
        # object to be able to move along diagonals as it will then appear to cut through physical blocks so we
        # only check the left, right, top and bottom from the tile so there's no diagonal movements, this makes the
        # algorithm slower but for our purpose it will be quick enough

        # Loop from -1 to 1 for the x and for the y as applying these values to the index of the current tile will
        # give a 3x3
        for x in range(-1, 2):
            for y in range(-1, 2):
                # Used if we want to include diagonal neighbours, the other statement will have to be an else for this
                #if x == 0 and y == 0:
                    #break
                if (x == -1 and y == 0) or  (x == 1 and y == 0) or  (x == 0 and y == -1) or  (x == 0 and y == 1):
                    checkX = tile.x + x
                    checkY = tile.y + y
                    # This if statement checks if the neighbour will be one that exists in the list of tiles by
                    # checking if it's outside the grid by using the grids height and width and tile size
                    if (0 <= checkX < (self.width/self.size)) and (0 <= checkY < (self.height/self.size)):
                        # If the neighbour exists in the grid then we index it in the tiles list and append the tile
                        # object to the list of neighbours
                        neighbours.append(self.tiles[checkY][checkX])
        return neighbours

    def get_distance(self, startTile, endTile):
        # Used for calculating the manhattan distance from one tile to another so we take in an end tile and start tile

        # manhattan distance is not a displacement so we don't care about direction so we take the absolute value
        # of the difference between the cords of the two tiles to remove negatives so it's just a magnitude
        x_change = abs(endTile.x - startTile.x)
        y_change = abs(endTile.y - startTile.y)

        # d_num = Number of tiles moved diagonally, v_num = Number of tiles moved vertically, h_num = Number of tiles moved horizontaly

        # If the x change is greater than the y change then we know we can have as many diagonal moves as there is
        # vertical and we will reach the correct vertical position and not overshoot the horizontal goal. We then
        # remove the number of diagonal moves from the x change as each diagonal move does a horizontal move and then
        # we know how many more horizontal moves to do. If x and y change were equal then we would still have y change
        # number of diagonals but x change is the same value as this so there wouldn't be any extra horizontal moves
        # so we still arrive at the desired location
        if x_change >= y_change:
            d_num = y_change
            y_num = 0
            h_num = x_change - d_num

        # There must be more y change betweeen the tiles than x change, in which case we want to have all horizontal
        # moves be accounted for with diagonal moves and we still won't overshoot the vertical goal. We then take how
        # many verticle moves were done by the diagonal moves and away from the desired y change and then we know
        # how many more y movements we need to do.
        else:
            d_num = x_change
            h_num = 0
            y_num = y_change - d_num

        # Each tile is represented as a square with side length 10 and diagonal 14, this square wouldn't actually
        # have a diagonal of 14 and it would instead be root 200 but the inaccuracy of it being 14 doesn't matter for
        # our application

        # We find the manhattan distance by multiplying the number of diagonal moves by 14 which is the diagonal length
        # per tile then add this to the product of horizontal and verticle moves added times 10 as they both have the
        # same length
        distance = (14 * d_num) + (10 * (y_num + h_num))
        return distance

    def reset_tiles(self):
        # Set the tiles to an empty list
        self.tiles = []
        # The map is a 2d array so we want to loop through the length of a row for the x index and the length
        # of the entire list which returns the length of a column for the y index
        for y in range(len(self.map)):
            # Add an empty list to the tiles list every time we move down a column
            self.tiles.append([])
            for x in range(len(self.map[0])):
                # If the number at the indexed location is a 1 then we know it's a solid block so we create a
                # tile that's not movaable and add it to our tiles list at the correct "column" which is indexed by
                # the y iterative variable
                if self.map[y][x] == 1:
                    self.tiles[y].append(Tile(False, (0, 0, 0), x, y, self.size))
                # If the number at the indexed location is a 0 then we know it's air so we create a
                # tile that's movable and add it to our tiles list at the correct "column" which is indexed by
                # the y iterative variable
                elif self.map[y][x] == 0:
                    self.tiles[y].append(Tile(True, (255, 255, 255), x, y, self.size))

# Tiles need to have costs associated with them and have a boolean for whether they are a walkable tile, they also
# need a parent variable which will be assigned when we move to that tile and lock it in place.
class Tile:
    def __init__(self, walkable, c, x, y, size):
        # Bool for whether the tile is an obstacle or not
        self.walkable = walkable
        self.colour = c
        self.size = size
        self.x = x
        self.y = y
        self.rect = pygame.Rect(x*self.size, y*self.size, self.size, self.size)
        # G cost is distance from the starting tile
        self.gCost = None
        # H cost(heuristic) is the distance from end node
        self.hCost = None
        self.parent = None

    def get_fCost(self):
        # F cost is just g cost + h cost so rather than updating it whenever g or h cost changes we instead just have
        # a function that returns the addition of the true so it's always up to date
        return self.gCost + self.hCost


def find_path(startPos, endPos):
    # startPos and endPos are co-ordinates as this pathfinding is used for taking enemy and player locations and
    # finding a path so we must the co-ordinates to a tile which that co-ordinate exists in
    startTile = grid.point_to_grid(startPos)
    endTile = grid.point_to_grid(endPos)
    # For displaying the the path finding for testing we want the start and end tile to have different colours for
    # visual purposes
    startTile.colour = (0,255,0)
    endTile.colour = (255,0,0)
    # A set of tiles that are being evaluated
    openSet = []
    # A set of tiles that have been fully evaluated meaning there is no faster path to them
    closedSet = []

    # gCost of the starting tile is 0 as you don't have to move anywhere to get to it
    startTile.gCost = 0
    # At the startTile to the open list
    openSet.append(startTile)

    # We want to loop until there is no longer any tiles in the open set meaning all tiles have been evaluated or the
    # target tile has been found in which case it will handle the exiting of the while loop by returning
    while len(openSet) > 0:
        # The current tile is always the first element in the openSet as this acts as a queue for tiles to be evaluated.
        currentTile = openSet[0]
        for i in range(1, len(openSet)):
            # This if statement will check all tiles in the open list and see if it's f cost is either less than the
            # current tiles f cost or whether the tiles f cost is the same but the heuristic cost is less than the
            # current tiles and in both situations we want the new current tile to be this tile as in terms of our
            # costs it's better suited
            if openSet[i].get_fCost() < currentTile.get_fCost() or (openSet[i].get_fCost() == currentTile.get_fCost() and openSet[i].hCost < currentTile.hCost):
                currentTile = openSet[i]

        # For it to be the current tile it must have better costs than any other tile in the open set so there isn't
        # a quicker way of getting to it so it's removed from the open set and added to teh closed set as it's now
        # been evaluated
        openSet.remove(currentTile)
        closedSet.append(currentTile)

        # If the current Tile is the desired end tile then we no longer want to keep checking as we have found the
        # shortest path as the currentTile is always the current best so we can return the startTile and endTile
        # as endTiles parent will show were it came from to be able to retrace it
        if currentTile == endTile:
            return retrace_path(startTile, endTile)

        # We get all of the neighbours of the currentTile as we wan't to expand the frontier of search to continue
        # finding better costed tiles.
        neighbours = grid.get_neighbours(currentTile)
        # For every neighbour we first want to see if it's not walkable and whether it's in the closed set meaning it's
        # been evaluated, if either of these are true then we don't want to check this neighbour so we use continue
        # to move to the next iteration
        for neighbourTile in neighbours:
            if not neighbourTile.walkable or neighbourTile in closedSet:
                continue
            # Set the neighbours tiles colour so that visually we can see the path it's taking for testing
            neighbourTile.colour = (249, 215, 28)

            # The get distance method from the current tile to the neighbour plus the current tiles g cost will be the
            # new g cost for the neighbour if we move there. If the neighbour is either not already in the open set
            # or they are in the open set but this new calculated g cost is better than they're current g cost then
            # We want to set the neighbours g cost to this new value and also set it's heuristic cost by using the
            # get distance method from the itself to the end tile. We also want to know how we got to this tile so
            # we set it's parent to be the current tile as this tile was the current tiles neighbour.
            newMovementCostToNeighbour = currentTile.gCost + grid.get_distance(currentTile, neighbourTile)
            if neighbourTile not in openSet or newMovementCostToNeighbour < neighbourTile.gCost:
                neighbourTile.gCost = newMovementCostToNeighbour
                neighbourTile.hCost = grid.get_distance(neighbourTile, endTile)
                neighbourTile.parent = currentTile

                # If the neighbourTile wasn't in the open set then we add it to it as we have started to evaluate this
                # tile now as we have a path to it.
                if neighbourTile not in openSet:
                    openSet.append(neighbourTile)

    # In case we don't find a path to the endTile, lets say it was trapped by non walkable tiles or the player/enemy
    # position placed the start or end inside a non walkable tile then we wouldn't find the end so we can return the
    # path we have found so far which should make the player/enemy move closer to the other so that it's at least
    # not just standing still. We could alternatively return None so the user knows that the path wasn't found so they
    # won't update it at all to prevent the player/enemy from walking in a wrong direction due to the non-complete path.
    print("not found final")
    return backup_path(currentTile)

def backup_path(current_tile):
    # We take the current_tile which is the last tile that was being evaluated and find the parent of it and then
    # then the parent of that tile and so on and add these tiles to the path list. We then reverse this list
    # so that it goes from the start tile onwards
    path = []
    tile = current_tile
    while tile.parent is not None:
        path.append(tile.parent)
        tile = tile.parent
    path.reverse()
    return path

def retrace_path(startTile, endTile):
    # We have found the destination so the currentTile will be the endTile. We then setup a while loop expression
    # where we continue to loop while the current tile does not equal the start tile. We then add the current tile to
    # the path list and then make the new current tile the parent of the current tile. This will loop until the current
    # tile is the start tile in which case it won't have a parent and we now have the complete path to follow but we
    # have to reverse it as it's currently going from end to start. Using pythons built in list reverse method to do
    # this and then we can reverse it.
    path_list = []
    currentTile = endTile

    while currentTile != startTile:
        path_list.append(currentTile)
        currentTile = currentTile.parent

    path_list.append(startTile)
    path_list.reverse()

    return path_list

def rle_to_list(rle_map):
    normal_list = []
    for y in range(0, len(rle_map)):
        normal_list.append([])
        for x in range(0, len(rle_map[y]), 3):
            count = (int(rle_map[y][x])*10)+int(rle_map[y][x+1])
            for i in range(count):
                normal_list[y].append(int(rle_map[y][x+2]))
    return normal_list
# We wan't the grid for pathfinding to be based on the game map so we read in the game map file and convert the file
# into a 2d array of tiles where 0 is a walkable block and 1 is a non walkable block.
map_grid = open("map.txt", "r").read().splitlines()
block_type_map = rle_to_list(map_grid)
'''
tile_type_map = []

for y in range(len(map_grid)):
    tile_type_map.append([])
    for x in range(len(map_grid[0])):
        tile_type_map[y].append(int(map_grid[y][x]))
'''
# This width and height needs to match the width and height of the game portion of the game window
width, height = 1000, 650
# Create a grid using a tile size of 25, the map that's been loaded and the width and height
grid = Grid(25, block_type_map, width, height)

# Below is a script for visually testing whether the path finding is working correctly. We have a fixed player location
# and then when you clock on the window it will find the shortest path between the player and the location of the click
# and then colour the start tile red, end tile green, the path blue and explored tiles as yellow. This section of code
# is commented out as it's not to be used for the actual game and just for testing the path finding.

'''
pygame.init()
win = pygame.display.set_mode((width, height), HWSURFACE | DOUBLEBUF | RESIZABLE)


running = True


playerX = 50
playerY = 450

# fails at 575, 475
def run_pathfinding(px, py, ex, ey):
    tile_path_list = find_path([px, py], [ex, ey])
    for tile in tile_path_list:
        tile.colour = (0,0,255)

    tile_path_list[-1].colour = (0,255,0)
    tile_path_list[0].colour = (255,0,0)


while running:
    win.fill((0, 255, 0))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONUP:
            pos = pygame.mouse.get_pos()
            grid.reset_tiles()
            run_pathfinding(playerX, playerY, pos[0], pos[1])

    for x in range(len(grid.tiles[0])):
        for y in range(len(grid.tiles)):
            pygame.draw.rect(win, grid.tiles[y][x].colour, grid.tiles[y][x].rect)

    pygame.display.update()
'''