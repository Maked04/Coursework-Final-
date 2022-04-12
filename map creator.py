import pygame
from custom_widgets import Button

# Setup a window with a width and height that'ss the size of what you want the game to be
clock = pygame.time.Clock()
pygame.font.init()
width = 1000
height = 650
# Set tile size
size = 25
win = pygame.display.set_mode((width, height))
pygame.display.set_caption("Map maker")

myfont = pygame.font.SysFont('Comic Sans MS', 10)

def redraw_window(win,button_map_list):
    # Fill the background with a colour then display all of the buttons on top of it
    win.fill((25, 50, 255))
    for button_row in button_map_list:
        for button in button_row:
            button.draw_button(win)

created_map_list = []
button_map_list = []

# Loop which runs for the number of tiles in a column by taking height divided by tile size
for y in range(int(height/size)):
    created_map_list.append([])
    button_map_list.append([])
    # Loop which runs for the number of tiles in a row by taking width divided by tile size
    for x in range(int(width / size)):
        # All tiles around the edge should by default be a block so create a button in that position but set it's
        # clicked variable to true and add it to the button map list in the correct position
        # Add one to created map list to represent it's a block tile
        if x == 0 or y == 0 or y == (int(height/size)-1) or x == (int(width/size)-1):
            created_map_list[y].append(1)
            button = Button((x * size), (y * size), size, size, (0, 0, 0), (0, 0, 255), (255, 0, 0), "B", None, 16)
            button.clicked = True
            button_map_list[y].append(button)
        # Any tile that's not on the edge we create a button which will have a clicked variable of false
        # Add a 0 to the created map list to represent it's an air tile
        else:
            created_map_list[y].append(0)
            button_map_list[y].append(Button((x * size), (y * size), size, size, (0, 0, 0), (0,0,255), (255, 0, 0), "B", None, 16))


running = True
mode = None
button_down = False
while running:
    clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            button_down = True
            if event.button == 3:
                mode = "Set to air"
            elif event.button == 1:
                mode = "Set to block"
        if event.type == pygame.MOUSEBUTTONUP:
            button_down = False

    if button_down:
        pos = pygame.mouse.get_pos()
        # If the mouse is clicked then get the position and test if any of the buttons were clicked.
        for button_row in button_map_list:
            for button in button_row:
                y = button_map_list.index(button_row)
                x = button_row.index(button)
                if button.check_if_clicked(pos):
                    if mode is not None:
                        if mode == "Set to air":
                            created_map_list[y][x] = 0
                            button.clicked = False
                        elif mode == "Set to block":
                            created_map_list[y][x] = 1
                            button.clicked = True


    # Call the redraw method
    redraw_window(win, button_map_list)

    pygame.display.update()

# Each button which corresponds to a tile is stored in a matrix, we want to take this matrix and chop it into
# rows and then perform rle compression on each row to attempt to compress it before storing it too the file
def list_to_rle(array_2d):
    rle_map = []
    for row in array_2d:
        # Each row starts as an empty string
        rle_string = ""
        count = 1
        # Loop through all tiles in the matrix map
        for i in range(0, len(row)-1):
            # Compare whether the current tile and the next tile are the same
            if row[i] == row[i+1]:
                # If they are then we want to add to the count of this "run"
                count += 1
            else:
                # If the next tile isn't the same as the current tile then the "run" ends at the current tile
                # so we want to add this run with it's associated count and type to the list
                if count < 10:
                    # Our RLE is always stored as a 3 so if the count is a single digit then we want to add a 0 in front
                    # to not change the number but keep it in the format. If we stored the type as a character for
                    # example then we could avoid doing this and instead just add the count then the character and when
                    # decompressing you can still return to the original as the character tells you where the end of
                    # each run is. This would decrease the file size but as this is not necessary so i've left it "type"
                    # as digits.

                    rle_string += "0" + str(count) + str(row[i])
                else:
                    rle_string += str(count) + str(row[i])
                # If the type has changed then the run has ended so we need to reset the count back down to 1
                count = 1
        # As we can't compare the last tile to the one in front as it doesnt exist we just manually do the rle for the
        # last tile by adding on the count and type as usual
        if count < 10:
            rle_string += "0" + str(count) + str(row[-1])
        else:
            rle_string += str(count) + str(row[-1])
        # For each row we add it the rle map and then once we've done all rows we return the rle map
        rle_map.append(rle_string)
    return rle_map

# Call the function which converts the map matrix into a list of rows which are in an rle format

rle_map = list_to_rle(created_map_list)
f = open("map.txt", "w")
for row in rle_map:
    # After each row in the rle map we write a new line in the file to show it's a new row
    f.write(str(row)+"\n")
f.close()
