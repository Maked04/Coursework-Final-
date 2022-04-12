import socket
import select
import pickle
import random
import pygame
from pygame.locals import *
import time
import os
from menus import Menu

# Iniiate the pygame font library and setup different font's for use on different bit's of text. Titles will use a
# bigger font to make them stand out.
pygame.font.init()
normalFont = pygame.font.SysFont('sitkasmallsitkatextitalicsitkasubheadingitalicsitkaheadingitalicsitkadisplayitalicsitkabanneritalic', 18)
subTitleFont = pygame.font.SysFont('bookmanoldstyle', 20)
titleFont = pygame.font.SysFont('bookmanoldstyle', 30)
endGameFont = pygame.font.SysFont('bookmanoldstyle', 100)

# The Client object is used for the ease of sharing data from server updates to
# game updates
class Client:
    def __init__(self, server):
        self.server = server

        # format = {num:PlayerObject, num:PlayerObject etc}
        self.clients = {}
        self.running = True
        self.player_name = None
        self.round_ended = False
        self.player_num = None
        self.ready = False  # This is for when the server has told us the game's ready by sending us the start info
        self.readied_up = False  # Set to true when the clients clicked the ready up button, this doesn't mean they
        # will go straight into the game so shouldn't start the game screen from running
        self.consumables = []
        self.jump_reset_num = 5
        self.time_space_pressed = 0
        # Bomb exploding particles have red orange and yellow colours
        self.particle_colours = [(253,160,68), (253,172,1), (255,113,17), (242,92,101), (192,34,12), (216,54,7),
                                 (255,239,125), (255,255,60), (245,218,27)]
        self.smoke_colour = [(102,102,102), (65,65,65), (130,130,130), (160,160,160)]
        self.particles = []  # format [position, velocity, life_left, colour]
        self.air_timer = 0
        self.moveL = False
        self.moveR = False
        self.crouch = False
        self.send_cooldown = 0
        self.loop_count = 0
        self.current_loop_count = 0
        self.time_left = None
        self.game_length = 20
        self.current_tagged = None  # Stores the current tagged player so we don't try to update the tagged player if
        # it hasn't changed

        # Pygame setup
        self.fps = 60
        self.clock = pygame.time.Clock()
        pygame.font.init()
        self.width = 1000
        self.height = 700
        # When the window is shown it will be be at 25 pixels down and to the right from the left corner of the
        # devices actual display
        os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (25, 25)
        self.screen = pygame.display.set_mode((self.width, self.height), HWSURFACE | DOUBLEBUF | RESIZABLE)
        self.win = self.screen.copy()

        self.bomb_img = pygame.transform.scale(pygame.image.load("images/bomb.png").convert_alpha(), (75,75))
        self.dirt_block = pygame.image.load("images/dirt_block.png")
        self.grass_block = pygame.image.load("images/grass_block.png")
        self.sky = pygame.transform.scale(pygame.image.load("images/sky_background.png"), (self.width,self.height))
        self.lobby_menu_background = pygame.transform.scale(pygame.image.load("images/explosion_background2.png"),
                                                            (self.width, self.height))
        # Consumable images
        self.jump_boost_icon = pygame.image.load("images/jump_boost.png")
        self.speed_boost_icon = pygame.image.load("images/speed_boost.png")
        self.slowness_icon = pygame.image.load("images/slowness_boost.png")
        # Player images
        self.tagged_img = pygame.image.load("images/TaggedPlayer.png")
        self.player_img = pygame.image.load("images/NormalPlayer.png")
        self.tagged_crouched_img = pygame.image.load("images/TaggedCrouched.png")
        self.player_crouched_img = pygame.image.load("images/NormalCrouched.png")
        pygame.display.set_caption("Client")

        # Variables for the menus
        self.text_x, self.text_y = 50, 50
        self.font_size = 16
        self.in_lobby_menu = True
        self.in_lobby = False
        self.lobby_menu = None
        self.lobby = None
        self.create_menus()
        self.tile_type_map = None
        # create block rects
        # create block map will populate the block rect and block images lists
        self.block_Rects = []
        self.block_imgs = []
        self.size = 25

    def create_map(self, rle_map):
        # Converts rle into a 2d array which is used to store the map
        self.tile_type_map = []
        for y in range(0, len(rle_map)):
            self.tile_type_map.append([])
            for x in range(0, len(rle_map[y]), 3):
                # The map is stored in rle where we take each row of the map and if there is a set of air tiles
                # in a row then we represent it as the number of them in a row and then a number to represent their type
                # We do this for each row so that its in a compressed format. For example 13 air tiles and 3 block tiles
                # would be 130 where 0 is an air tile and 031 where 1 is a block tile. We therefore need to run through
                # each section of 3 and work out the count and then add that many of the specified tile type to the
                # 2d array at it's row to get the normal tile format
                count = (int(rle_map[y][x]) * 10) + int(rle_map[y][x + 1])
                for i in range(count):
                    self.tile_type_map[y].append(int(rle_map[y][x + 2]))

        # Once a new tile map is created we need to create a new block map for this, the block map is for the rectangles
        # and images of each block for displaying and testing collision
        self.create_block_map()

    def create_menus(self):
        self.font_size = 16
        # Create a menu object for the lobby menu, using it's method to add a title with image next to it and
        # one entry for entering the username and one button for joining the lobby
        self.lobby_menu = Menu((255, 215, 50), "lobby menu", self.screen, self.lobby_menu_background)
        self.lobby_menu.add_image("bomb image", 550,225, self.bomb_img)
        self.lobby_menu.add_text("menu title", titleFont, "Bomb Tag", (0, 0, 0), 375, 250)
        self.lobby_menu.add_button("join lobby", 415, 400, 130, 50, (255, 255, 255), (255, 255, 255), (0, 0, 0),
                              "Join lobby", None, self.font_size, 5, (0, 0, 0))
        self.lobby_menu.add_entry("enter name", 415, 350, 130, 30, (0, 0, 0), self.font_size, 2.5, (0, 0, 0))

        # Creating another menu object for the lobby with a title, two buttons for readying up or leaving the lobby
        # and a text box with a title of "Players list: " and all players in the lobby will be displayed in the text box
        self.lobby = Menu((255, 120, 120), "lobby", self.screen, self.lobby_menu_background)
        self.lobby.add_text("lobby title", titleFont, "Lobby", (0, 0, 0), 425, 200)
        self.lobby.add_button("ready button", 300, 300, 150, 50, (255, 255, 255), (255, 255, 255), (0, 0, 0),"Click to Ready Up",
                         "readied up", self.font_size, 5, (0,0,0))
        self.lobby.add_button("leave button", 500, 300, 150, 50, (255, 255, 255), (255, 255, 255), (0, 0, 0), "Leave lobby", None,
                         self.font_size, 5, (0,0,0))
        self.lobby.add_box("player list box", 25, 25, 150, 600, (255,255,255), (0, 0, 0), 5)
        self.lobby.add_text("players list", subTitleFont, "Players list: ", (0, 0, 0),  self.text_x, self.text_y)
        # We want the next player name to be displayed 50 pixels underneath the title so add 50 pixels onto the y
        # variable for text
        self.text_y += 75

    def client_loop(self):
        # If the server sends a message closing the connection or the client closes the window then we set running to
        # false so we no longer run the update or game loop
        if self.running:
            while True:
                # Call one after the other as the update loop will be altering data that the game loop needs to use
                # so if they were running asynchronously this would cause errors and data corruption
                self.update_loop()
                self.game_loop()

    def redraw_game_window(self):
        # If tagged player is found then we display bomb particles from that players location
        tagged_player = None
        # We want to display the time left in the top left so create a text surface with the time_left variable which
        # is constantly being updated by the server and blit (draw) it to the corner of the screen
        text = subTitleFont.render("Time left: "+str(self.time_left), False, (255,0,0))
        self.win.blit(text, (10,10))

        # The server will update the client with all of the current consumables, we take the type and check whether it's
        # "Speed", "Jump" or "Slow" and display the correct image for this type of consumable at the co-ordinates the
        # server has given us from it's pygame rect which has a x and y value.
        for consumable_details in self.consumables:
            if consumable_details[0] == "Speed":
                self.win.blit(self.speed_boost_icon, (consumable_details[1].x, consumable_details[1].y))
                # pygame.draw.rect(self.win, (0, 0, 255), consumable_details[1])
            elif consumable_details[0] == "Jump":
                self.win.blit(self.jump_boost_icon, (consumable_details[1].x, consumable_details[1].y))
                # pygame.draw.rect(self.win, (0, 255, 0), consumable_details[1])
            elif consumable_details[0] == "Slow":
                self.win.blit(self.slowness_icon, (consumable_details[1].x, consumable_details[1].y))
                #(220, 220, 220)
                #pygame.draw.rect(self.win, (255,0,0), consumable_details[1])
        for client_object in self.clients:
            # For every client we want to call the draw and display name method on all of them which will handle
            # which image and name to display.
            p = self.clients[client_object]
            if p.bool_dict["tagged"]:
                tagged_player = p
            p.draw(self.win)
            p.display_name(self.win)

        # Time left is None before the game starts so we only want to execute the statement if we have an integer value
        # for the timer left and check if we have a tagged_player which we always should have but stops errors if
        # we run this before we've received the start game information.
        if self.time_left is not None and tagged_player is not None:
            # Game length is 100 seconds so we take away the time left from this and divide it by 10 and this number
            # as an int is how many times we will run the for loop so how many particles we will add per frame. As time
            # left decreases the number of particles being added per frame will increase to give the affect of the bomb
            # getting closer to exploding.
            for i in range(int((self.game_length - int(self.time_left)) / 10)+1):
                # Particles are just a list of values to represent their x, y, x velocity, y velocity and the particles
                # colour. The velocity's are random and the colour is a random pick of a set of colours.
                self.particles.append(
                    [[tagged_player.rect.x, tagged_player.rect.y],
                     [(random.randint(0, 20) / 10 - 1), (random.randint(0, 20) / 10 - 1)],
                     5,
                     self.particle_colours[random.randint(0, len(self.particle_colours)-1)]])

        #for i in range(10):
            #self.particles.append([[random.randint(0,self.width), 50], [(random.randint(0, 20) / 10 - 1), (10)], 10, (255,255,255)])

        # To prevent data corruption from trying to alter the list during iteration we use sorted and enumerate to loop
        # through effectively a copy so that we're not looping through the list were going to alter
        for i, v in sorted(enumerate(self.particles), reverse=True):
            particle = v
            particle[0][0] += particle[1][0]  # Apply the particles x velocity to it's x location
            particle[0][1] += particle[1][1]  # Apply the particles y velocity to it's y location
            particle[1][1] += 0.05  # Increase the particles y velocity, the value for this is the "gravity" as it
            # accelerates the particle down
            particle[2] -= 0.1 # Reduce the "life" integer of the particle which is used for it's radius when drawing
            # and used to tell whether the particle is "dead" so should be removed from the list of particles
            if particle[2] < 0:  # If particles life is less than 0 then remove it from the list of particles
                self.particles.pop(i)
            # Draw a circle using the pygame draw circle with the particles colour at it's x and y position which
            # starts as the tagged players x and y so we add 25 pixels to the x co-ordinate so it displays on the right
            # side of the player as this is where the bomb images sparks should be from. We use the particles life left
            # for the circles radius.
            else:
                pygame.draw.circle(self.win, particle[3], (int(particle[0][0]+25), int(particle[0][1])),
                                   int(particle[2]))

    def create_block_map(self):
        # We want a list of all blocks pygame rect objects in a list for testing collisions and we also want another
        # list with the images and cords to display to represent these blocks
        # format is [[dirtImg, x, y], [grassImg, x, y]]
        for x in range(0, len(self.tile_type_map[0])):
            for y in range(0, len(self.tile_type_map)):
                if self.tile_type_map[y][x] == 1:
                    # If the tile in the block type map is a 1 then it should be a collide able block, x and y in the
                    # loop are indexes so we must times them by the size of the tile to get the actual co-ordinates. We
                    # add 2 tile heights to all y cords to account for the top border
                    pos = (x * self.size), ((2 * self.size) + (y * self.size))
                    dirt = False
                    # There is two different types of block, a grass and dirt block. If we find a tile that should be a
                    # block then we check if the tile above should also be a block and if so we add a dirt tile and
                    # otherwise we add a grass block so the grass blocks will always be on top of a stack of dirt blocks
                    if y > 0:
                        # Test if the tile above the block we have found is also a block tile and if it is then we add
                        # a dirt image to the block images list at the position calculated before
                        if self.tile_type_map[y - 1][x] == 1:
                            dirt = True
                            self.block_imgs.append([self.dirt_block, pos[0], pos[1]])
                    # If there wasn't a block above the block we found then we want to add a grass block to the list of
                    # blocks
                    if not dirt:
                        self.block_imgs.append([self.grass_block, pos[0], pos[1]])
                    # Finally we add the rect object for the block, this is not dependant on whether it's dirt or grass
                    self.block_Rects.append(pygame.Rect(pos[0], pos[1], self.size, self.size))

    def collision_test(self, player_rect, block_rects):
        # Takes a players rect object and a list of block rect objects as parameters and loops through the list of
        # blocks and uses the colliderect method to test if the player rect overlaps with each block rect and if it does
        # the it's added to the hit list which is returned after testing all blocks
        hit_list = []
        for block in block_rects:
            if player_rect.colliderect(block):
                hit_list.append(block)
        return hit_list

    def move(self, rect, movement, blocks):
        # The method for handling collisions is to apply the x-movement and then test collisions and correct for them
        # and then apply the y-movement and then test collisions again and correct for them. This allows a player to
        # interact with a block to the side and above or below and handles the collision correctly. Based on the
        # direction of the movement we can determine whether the player collided with the top, bottom, left or right
        # of the block and this list of collision types can be used to adjust player velocities.
        collision_types = {'top': False, 'bottom': False, 'right': False, 'left': False}
        # Apply the x movement to the rect
        rect.x += movement[0]
        # Call the collision test method to return all the blocks that have now been hit due to this movement
        hit_list = self.collision_test(rect, blocks)
        for block in hit_list:
            if movement[0] > 0:
                # If x-movement is greater than 0 then they were moving to the right so must have collided with the
                # left of the block so we wan't the players rect's x cord to be the x cord of the left of the block,
                # rect.right = block.left does this for us
                rect.right = block.left
                # The player has hit something on the right so set the right collision type to true
                collision_types['right'] = True
            elif movement[0] < 0:
                # If x-movement is less than 0 then they were moving to the left so must have collided with the
                # right of the block so we wan't the players rect's x cord to be the x cord of the right of the block,
                # rect.left = block.right does this for us
                rect.left = block.right
                # The player has hit something on the left so set the left collision type to true
                collision_types['left'] = True
        # Apply the y-movement to players y co-ordinate
        rect.y += movement[1]
        # Test collisions with all blocks with this new location
        hit_list = self.collision_test(rect, blocks)
        for block in hit_list:
            # Pygame screen goes from 0,0 as top left so adding to this y is moving down and taking from y pos is moving
            # up
            if movement[1] > 0:
                # If y-movement is greater than 0 then they were moving down so must have collided with the
                # top of the block so we wan't the players rect's y cord to be the y cord of the top of the block,
                # rect.bottom = block.top does this for us
                rect.bottom = block.top
                # The player has hit something on the bottom so set the bottom collision type to true
                collision_types['bottom'] = True
            elif movement[1] < 0:
                # If y-movement is less than 0 then they were moving up so must have collided with the
                # bottom of the block so we wan't the players rect's y cord to be the y cord of the bottom of the block,
                # rect.top = block.bottom does this for us
                rect.top = block.bottom
                # The player has hit something on the top so set the top collision type to true
                collision_types['top'] = True
        # Return the players new rect once the movements have been applied and corrected for due to collisions, we also
        # return the collision types so velocities can be accounted for. An example of this would be if you've had a
        # bottom collision then you would want the players y velocity to be 0 so they stop moving down
        return rect, collision_types


    def game_loop(self):
        # clock tick will compute how many milliseconds have passed since the previous call. We use this to keep
        # movements constant by having the magnitude of a movement be proportional to the time taken between frames. This
        # is done so that movement speed isn't based on the framerate.
        dt = self.clock.tick(self.fps)/1000
        # Enter if statement if were still running and if ready is false meaning we're not in the game
        if not self.ready and self.running is True:
            # Lobby menu(lobby picker)
            # If in_lobby_menu is true then we want to use this menus loop method to display it. We also check if
            # widgets have changed state so this event can be used outside of the menu
            if self.in_lobby_menu:
                # "Game quit" is returned from the Menu event loop if the client has pressed the exit button so outside
                # of the menu we need to know this so that we can tell the server that we've left
                if self.lobby_menu.event_loop() == "Game quit":
                    self.server.send(pickle.dumps(["Player left", self.player_num]))
                    # Any time the client clicks the exit button on a window we wan't to stop the application from
                    # running
                    self.running = False
                # If the client has clicked the join lobby button then that buttons clicked variable will be true so
                # we test this and if it's true then first set that variable to false as it can be re-used if we go
                # back to the lobby menu
                if self.lobby_menu.b_dict["join lobby"].clicked:
                    # If the player hasn't entered a name
                    text = self.lobby_menu.e_dict["enter name"].text
                    if text == "Enter text" or text == "":
                        text = "Player"+str(self.player_num)

                    self.lobby_menu.b_dict["join lobby"].clicked = False
                    # We then want to take whatever text is in the entry and store it as the players name and add 25
                    # pixels onto the text_y so the players name will be displayed 25 pixels below the title.
                    self.player_name = text
                    self.text_y += 25
                    # Send a message with "Joined lobby" as header with the players number and name so they can update
                    # the players name on their side
                    self.server.send(pickle.dumps(["Joined lobby", self.player_num, self.player_name]))
                    # We want to move to the next menu so set in_lobby_menu to false so we no longer enter the if
                    # statement for running it's event loop and then set in_lobby to true so we run the elif to call
                    # lobbys event loop
                    self.in_lobby_menu = False
                    self.in_lobby = True

            # In an actual lobby
            elif self.in_lobby:
                # Call the event loop method for the lobby to display it and check and handle events.
                if self.lobby.event_loop() == "Game quit":
                    # "Game quit" is returned from the Menu event loop if the client has pressed the exit button so outside
                    # of the menu we need to know this so that we can tell the server that we've left
                    self.server.send(pickle.dumps(["Player left", self.player_num]))
                    self.running = False
                if self.lobby.b_dict["leave button"].clicked:
                    # If the leave button is clicked then it's clicked variable will be true so we do the below
                    # statements to
                    self.lobby.b_dict["leave button"].clicked = False
                    # We need to notify the server that we left so we send a message with "Left lobby" as header along
                    # with the player number and name so they can update who's in the lobby so everyone else can know
                    # they left
                    self.server.send(pickle.dumps(["Left lobby", self.player_num, self.player_name]))
                    # We want to move back to the lobby menu so set lobby_menu to false so we no longer enter the if
                    # statement for running it's event loop and then set in_lobby_menu to true so we run the elif to
                    # call lobby menus event loop
                    self.in_lobby_menu = True
                    self.in_lobby = False
                    self.readied_up = False
                    # If they were readied up but then left the lobby then we want the readied up button to be reset to
                    # not clicked for if they join the lobby again
                    self.lobby.b_dict["ready button"].clicked = False

                if self.lobby.b_dict["ready button"].clicked and self.readied_up is False:
                    # If the ready button is clicked and it wasn't previously clicked then set readied up variable
                    # to true and notify the server that we are readied up.
                    self.readied_up = True
                    self.server.send(pickle.dumps(["Ready", self.player_num]))

        # If ready variable is true it means we should be in the actual game, we still only run the rest if the
        # application is running
        if self.ready is True and self.running is True:
            s_time = time.perf_counter()
            # Get the player object that is for the client
            p = self.clients[self.player_num]
            self.loop_count += 1

            # Fill the screen with black for the border above the game to be black
            self.win.fill((0, 0, 0))
            # Blit the sky background for the game 50 pixels down to leave a black border above for the time to be shown
            self.win.blit(self.sky, (0, 50))

            # Block_imgs contains all of the images with the co-ordinates to display them so we loop through all of
            # them and draw the images at the desired locations.
            for block in self.block_imgs:
                self.win.blit(block[0], (block[1], block[2]))

            # We want to know if the client's player has any active consumables
            #If neither speed or slowness is active then we want the normal x velocity of 240
            if p.bool_dict["speed_boost_active"]:
                p.velX = 300
            elif p.bool_dict["slowness_active"]:
                p.velX = 180
            else:
                p.velX = 240
            # If slowness and speed boost is active then we want to cancel them out and set the x-velocity to normal
            if p.bool_dict["slowness_active"] and p.bool_dict["speed_boost_active"]:
                p.velX = 240
            # When the player is in the air we increment the air timer by 1, this means if the client presses space
            # again to jump we can not count it as a jump if the air timer is below a certain amount, to do this
            # we check if air_timer is less than jump_reset_num so a low jump reset means there is only a small window
            # of 6 game loop iterations where clicking space again will cause another jump, if we increase this
            # jump reset number then there is a period of time where you can cause a jump again which acts like a
            # double jump
            if p.bool_dict["double_jump_active"]:
                # If jump boost is active then increase the jump reset number
                self.jump_reset_num = 40
            else:
                self.jump_reset_num = 5

            # If the player is crouched then we want the player's height to be 25 pixels rather than 40
            if p.bool_dict["crouched"]:
                p.height = 25
            elif not p.bool_dict["crouched"]:
                p.height = 40
            # The update method will create an updated rect for the player with the new height
            p.update()

            # Every game loop the movement in both x and y direction is set to 0 and then we calculate the movement.
            # Movement is based on the time since last frame as a time variable to be used in motion equations to
            # calculate distance rather than applying a fixed velocity every frame which will mean a constant distance
            # moved every frame so if the frame rate changes then the amount the player moves changes so a player
            # running higher frames would be able to run faster and jump higher than another player with a different
            # frame rate
            movement = [0, 0]
            # We multiply the velX by the dt which is the time since the last frame, this is effectively
            # distance = speed * time so as we have a constant speed, if the time is small then distance will be
            # smaller as it wasn't moving at that speed for as long
            if self.moveL:  # If left key is held then x component of movement is reduced by the players X velocity
                movement[0] -= (p.velX*dt)
            elif self.moveR:  # If right key is held then x component of movement is increased by the players X velocity
                movement[0] += (p.velX*dt)

            # The y-movement is based on the suvat equation of s = ut + 1/2(at^2) and we plug in the time since last
            # frame as the time variable and then the u which is the initial velocity which is just the players current
            # velocity and p.acc for the a variable which is the players acceleration which is constant and act's as the
            # gravitational field strength
            movement[1] += (p.velY*dt)+(0.5*p.acc*(dt*dt))
            # We want to increase the players y-velocity as they fall so we increase the y-velocity by the acceleration
            # multiplied by the time since last frame as v = u + at
            p.velY += (p.acc * dt)

            # We want there to be a cap for the verticle velocity to mirror real life terminal velocity
            if abs(p.velY) > 400:
                p.velY = 400

            # Move function applies x movement then checks collisions then applies y movement and checks collisions
            # and returns the new location for the player and the types of collisions that were made
            p.rect, collisions = self.move(p.rect, movement, self.block_Rects)
            # Player rect is updated but this doesn't update the x and y location so we have to do this from rect values
            p.x = p.rect[0]
            p.y = p.rect[1]

            # If we hit the top of a block then it should stop us from moving up so we set the y velocity to 0 so it no
            # longer keeps moving and the gravity will then make it fall later on.
            if collisions['top']:
                p.velY = 0

            # If player rect collides with top side of block then it's hit the "bottom" so the players Y velocity is
            # set to 0 and air_timer is set to 0 as it's a solid ground so we no longer want to move through it. The air
            # timer is set to 0 as we are no longer in the air as are on the ground.
            if collisions['bottom']:
                p.velY = 0
                self.air_timer = 0

            # If not colliding with "bottom" then the player must be in the air so we increment air_timer by 1
            else:
                self.air_timer += 1

            # This method handles the drawing of all game objects including players consumables and particles
            self.redraw_game_window()
            # When the round ends, this happens for the next two seconds
            if self.round_ended:
                tagged_player = self.clients[self.game_loser]
                text = endGameFont.render(f"{str(tagged_player.name)} Lost", False, (0, 0, 0))
                self.win.blit(text, (200, 350))
                for i, v in sorted(enumerate(self.particles), reverse=True):
                    particle = v
                    # When particles get small we turn them into small
                    if particle[2] < 10:
                        particle[1][1] = -3
                        particle[3] = self.smoke_colour[random.randint(0, len(self.smoke_colour)-1)]
                        # Hardly want these particles to lose size, this means they are hardly removed so if
                        # ending round section is too long there will be too many particles so will lag game out
                    particle[2] += 0.1
                # Add 15 new explosion particles
                for i in range(20):
                    self.particles.append(
                        [[tagged_player.rect.x, tagged_player.rect.y],
                         [(random.randint(0, 20) / 10 - 1)*20, (random.randint(0, 20) / 10 - 1)*20],
                         random.randint(10,20),
                         self.particle_colours[random.randint(0, len(self.particle_colours) - 1)]])

                if time.perf_counter() - self.ended_time > 2:
                    self.round_ended = False
                    self.reset_game()

            for event in pygame.event.get():
                # If a quit event is found then we want to no longer run any of the code so running is now false and
                # we also want to inform the server that we've quit so we send them a message saying this with our
                # clients number and then quit the pygame display and quit pygame
                if event.type == pygame.QUIT:
                    self.running = False
                    self.server.send(pickle.dumps(["Player left", p.num]))
                    pygame.display.quit()
                    pygame.quit()
                if event.type == pygame.VIDEORESIZE:
                    # If the client resize's the window then we want to take the size of the new event and scale the
                    # screen up to this size, we use the HWSURFACE|DOUBLEBUF|RESIZABLE commands to make the new screen
                    # resizable and then Double-buffering uses a separate block of memory to apply all the
                    # draw routines and then copying that block (buffer) to video memory as a single operation. hardware
                    # surface refers to using memory on the video card ("hardware") for storing draws as opposed to main
                    # memory ("software"). These flags prevent screen tearing
                    self.screen = pygame.display.set_mode(event.size, HWSURFACE|DOUBLEBUF|RESIZABLE)

                if event.type == pygame.KEYDOWN:
                    # When falling the player reaches a terminal velocity which can make game play slow as if you jump
                    # you may be waiting for a while to hit the ground and jump. This functionality adds a way to speed
                    # down, if you hit the space bar more than once within 1 second then your y-velocity will be
                    # increased by 500 giving a shooting down affect.
                    if event.key == pygame.K_SPACE:
                        # If space is clicked we store the time of the click and then if it's clicked again we check
                        # if the last time the space was clicked is within a second of the current click and if so
                        # we increase the players y velocity by 500
                        if time.perf_counter() - self.time_space_pressed < 1:
                            p.velY += 500
                        self.time_space_pressed = time.perf_counter()
                    # If left key is clicked the moveL becomes true so we will be applying the x-velocity in the left
                    # direction which is the negative direction
                    if event.key == pygame.K_LEFT:
                        self.moveL = True
                    # If right key is clicked the moveR becomes true so we will be applying the x-velocity in the right
                    # direction which is the positive direction
                    if event.key == pygame.K_RIGHT:
                        self.moveR = True
                    # If we click the down arrow then we want the player to perform a crouch motion so we just set the
                    # crouched variable to true and when this variable is true the players rect height will be reduced
                    # and a different image which represents crouched will be displayed
                    if event.key == pygame.K_DOWN:
                        p.bool_dict["crouched"] = True
                    if event.key == pygame.K_UP:
                        # The air timer is incremented by 1 for every frame that the player is falling and if this
                        # number is less than the jump reset num then we will allow the player to jump, usually
                        # the jump reset num is 5 and this just makes sure that air timer hasn't been increased
                        # accidentally which would block the jump from happening even though the player is technically
                        # on the ground, increasing the jump reset number means the player could jump even if they are
                        # currently off the ground which acts like a double jump. Technically if a player could
                        # click jump quick enough then they could click a second time before the air timer is 5 and then
                        # jump again which adds a secret way to jump higher.
                        if self.air_timer < self.jump_reset_num:
                            # If we've jumped then we want to begin to accelerate up so we set the y velocity to a large
                            # negative value so we begin to move upwards but the acceleration down which acts as gravity
                            # will be constantly reducing this velocity so it will create a parabola affect where the
                            # player accelerates up to a stationary point then falls due to gravity.
                           p.velY = -p.acc
                if event.type == pygame.KEYUP:
                    # If the left key comes up then the player should stop moving to the left so the moveL variable is
                    # set to false so that movement in that direction won't be applied.
                    if event.key == pygame.K_LEFT:
                        self.moveL = False
                    # If the right key comes up then the player should stop moving to the right so the moveR variable is
                    # set to false so that movement in that direction won't be applied.
                    if event.key == pygame.K_RIGHT:
                        self.moveR = False
                    # If they release the down key then we want them to un crouch so we set the players crouched
                    # variable to false to do this
                    if event.key == pygame.K_DOWN:
                        p.bool_dict["crouched"] = False

            # With these values we are just sending an update to the server every game loop, by increasing the
            # values we can send it less frequent in case the connection can't handle it
            if self.send_cooldown <= 0:
                # We send a message to the server with header "Update info" and it contains the players number
                # so they can update the correct player information and the players rect which has the x, y and size.
                self.server.send(pickle.dumps(["Update info", [p.num, p.rect]]))
                self.send_cooldown = 1

            self.send_cooldown -= 1

            # Everything is drawn onto the window and we then scale the window up to the size of the current screen.
            # When the window is the original size the resolution is normal but when we resize the screen the window
            # will have a stretched/squished resolution
            self.screen.blit(pygame.transform.scale(self.win, self.screen.get_rect().size), (0, 0))
            pygame.display.update()
            # Test to see if the game loop is taking longer than 0.1 seconds to run which is just for troubleshooting
            if time.perf_counter()-s_time > 0.1:
                print("loop time: "+str(time.perf_counter()-s_time))

    def reset_tagged_player(self):
        # Loop through clients list which contains all of the player objects and set their tagged variables to
        # False
        for client in self.clients:
            self.clients[client].bool_dict["tagged"] = False

    def reset_game(self):
        # When the games reset all of the necessary variables must be reset so that when a new game starts everything
        # appears as normal. We also set the readied up and lobby variables to false but lobby menu variable to true
        # so in the game loop we will now display the lobby menu
        self.clients = {}
        self.air_timer = 0
        self.time_space_pressed = 0
        self.ready = False
        self.in_lobby_menu = True
        self.readied_up = False
        self.in_lobby = False
        self.moveL = False
        self.moveR = False
        self.lobby.b_dict["ready button"].clicked = False
        self.particles = []
        self.reset_tagged_player()

    def update_tagged_player(self, num):
        # If there isn't images for players then all non tagged players will be blue and tagged player is orange.
        self.current_tagged = num
        # Loop through all player objects in client list and set their tagged variable to false
        for client in self.clients:
            self.clients[client].bool_dict["tagged"] = False
            self.clients[client].colour = (0, 0, 255)

        # Use the parameter which is the tagged players number to access their player object in the client list, we then
        # take this player object and set it's tagged variable to True and change the colour to orange as this is the
        # colour for a tagged player, this colour can be used if there isn't a player image available.
        if num in self.clients:
            self.clients[num].bool_dict["tagged"] = True
            self.clients[num].colour = (255, 165, 0)

    def update_loop(self):
        message = None
        # Using the select.select method to check if the server is readable, ins = readable, outs = writable and ex
        # is for exceptions. The parameters for the select method are three lists, one for "wait until ready for reading
        # another for "wait until ready for writing" and one for "wait for an exceptional condition" and then the final
        # parameter is the timeout which when set to 0 never blocks. We use the wait until ready for reading using the
        # server as the parameter so it will detect when the server to sends a message and then we can process it. If
        # the server isn't sending a message then ins will be empty so the update loop will end there.
        ins, outs, ex = select.select([self.server], [], [], 0)
        for inm in ins:
            try:
                # inm will be the socket that the select statement has detected as readable so we will call the
                # recv method on this to receive the bytes and then use pickle.loads to deserialize the bytes to get
                # it back into normal from which will be a list with a header for what type of update it is
                message = pickle.loads(inm.recv(1024))
            # For connections over unstable connection we allow for many errors to be ignored as they won't affect
            # the game as missing 1 client update will have 0 visual affect
            except (pickle.UnpicklingError, ImportError, EOFError, IndexError, TypeError, ValueError, UnicodeDecodeError):
                print("error with pickle")

            if message is not None:
                # If the header of the message is "Update info" then we know what to except as an update so we
                # process all of the update
                # format ["Update info", [num,rect], [num,rect], ["Tagged player", num],
                # ["Consumables", ["Consumable type", "Consumable rect", player_collided]],["Time left", time]]
                if message[0] == "Update info":
                    # Remove the messages header
                    message.pop(0)
                    # Once the header is removed there will be player location updates and then the tagged player,
                    # consumables and then time left updates so we loop from the start of the update until 3 from the
                    # end of the list so within this loop the index i will access all of the player location updates
                    for i in range(0, len(message) - 3):
                        num = message[i][0]
                        # For each player update we first check if it's the clients player and if so we don't process
                        # it as we already know our players location and updating it from the server will cause our
                        # player to lag
                        if num != self.player_num:
                            # For all players that aren't the clients we want to update their rect and x, y cords.
                            # We then want to check if the height of the rect is 25 and if so this tells us whether
                            # the player is crouched or not and we set the crouched variable to true if so
                            self.clients[num].rect = message[i][1]
                            self.clients[num].x = message[i][1].x
                            self.clients[num].y = message[i][1].y
                            if self.clients[num].rect.height == 25:
                                self.clients[num].bool_dict["crouched"] = True
                            else:
                                self.clients[num].bool_dict["crouched"] = False

                    # The list 3 places back from the end of the list will be the update for the tagged player, we
                    # check if it is by checking it's header and then call the update tagged player method passing
                    # through the second variable in the tagged player update which is the tagged players number.
                    if message[-3][0] == "Tagged player":
                        # If the tagged player sent by the server isn't the current tagged player then we update it,
                        # this prevents us from updating the tagged player when nothing's changed which just wastes
                        # unnecessary processing.
                        if self.current_tagged != message[-3][1]:
                            self.update_tagged_player(message[-3][1])

                    # The list 2 places back from the end of the list is one for the consumables
                    if message[-2][0] == "Consumables":
                        # Remove the header of the consumables update list
                        message[-2].pop(0)
                        # Create an empty list which all consumables will be added to for drawing
                        to_draw = []
                        # Set all the clients player variables that are affected by consumables to false
                        self.clients[self.player_num].bool_dict["speed_boost_active"] = False
                        self.clients[self.player_num].bool_dict["double_jump_active"] = False
                        self.clients[self.player_num].bool_dict["slowness_active"] = False
                        # Loop through all lists within the consumable update list
                        for consumable_details in message[-2]:
                            # If the 3rd consumable detail is None then this means the consumable hasn't been collected
                            # so we don't need to check if we need to apply the affect of the consumable.
                            if consumable_details[2] is not None:
                                # For all consuambles that have been collected we check if the player who collected it
                                # is our player
                                if consumable_details[2] == self.player_num:
                                    # We check what type of consumable it is and set our players corresponding
                                    # consumable affect variable to true
                                    if consumable_details[0] == "Jump":
                                        self.clients[self.player_num].bool_dict["double_jump_active"] = True
                                    elif consumable_details[0] == "Speed":
                                        self.clients[self.player_num].bool_dict["speed_boost_active"] = True
                                    elif consumable_details[0] == "Slow":
                                        self.clients[self.player_num].bool_dict["slowness_active"] = True
                            else:
                                # If the consumable was collected by someone then we wouldn't reach this else statement
                                # as we only display the consumable while it hasn't been collected
                                # We add the consumable type and tuple for co-ordinates to a list and then add this to
                                # the to_draw list
                                to_draw.append([consumable_details[0], consumable_details[1]])
                        # The to_draw list will now contain a list of two details, the type and the location so we
                        # update the public variable for consumables to the new to_draw list
                        self.consumables = to_draw
                    # The final list in the update list will be a the time update, this contains a header to double
                    # check that it's the correct update and then a time left and we just set the public time left
                    # variable to the second thing in the time update list which is an integer for the time
                    if message[-1][0] == "Time left":
                        self.time_left = message[-1][1]

                # If the header is "player num"
                # When we first join we wan't to know what our player/clients number is, all player objects are added
                # to the clients list and to access it we use the number received here to make sure were accessing our
                # player
                elif message[0] == "Player num":
                    self.player_num = message[1]
                    # Set the public player num variable to the second item in player num list
                    print("I am client number "+str(self.player_num))
                    # When the client receives their number they also receive the map in an rle format which then
                    # needs to be decompressed to use it. It's sent in this format so that it's at a size that can be
                    # sent in one message rather than needing to have a buffer and send small amounts of the normal map
                    # and build the map up from that
                    rle_map = message[2]
                    # Call the function which converts the rle into a 2d array
                    self.create_map(rle_map)

                # If the client tries to join the lobby but the game has already started then the server needs to reject
                # us from joining and notify us of this. A message with the header "Not joined lobby" notifies us of
                # this so we then call the reset game method which acts like were in a game that just ended so sends us
                # back to the lobby menu and resets all relevant variables
                elif message[0] == "Not joined lobby":
                    print("here")
                    self.reset_game()

                # When a client closes the window we first send the server a message saying this and then the server
                # tells all clients that this player has left by sending a "Player left" message with the player
                # who lefts number.
                elif message[0] == "Player left":
                    # If the player who left is us then we set running to false
                    if message[1] == self.player_num:
                        self.running = False
                    print("been told player has left")
                    # If the player number is in the clients list then we remove this client from the clients list
                    if message[1] in self.clients:
                        self.clients.pop(message[1])

                # ["Current names", [num, name], [num, name]]
                elif message[0] == "Current names":
                    # Whenever a client leaves or joins the lobby they notify the server and then the server compiles
                    # a new list of current clients in the lobby and broadcasts it too everyone.
                    message.pop(0)
                    to_remove = []
                    # We set the text x and y to the cords we want to start displaying the text at
                    self.text_x, self.text_y = 50, 75
                    # We remove all text from the lobby that isn't the title or the header for the players list
                    for text in self.lobby.t_dict:
                        if text != "players list" and text != "lobby title":
                            to_remove.append(text)
                    for remove in to_remove:
                        # Remove the text from the text dictionary by calling it's delete method with the text's
                        # associated name
                        self.lobby.delete_text(remove)
                    # Loop through all names in the update and add text of their name onto the menu
                    for update in message:
                        # Move 25 pixels down everytime so each name is displayed 25 apart
                        self.text_y += 25
                        # In the lobby Menu object we store the text in the dictionary with the player num as key
                        # and player name as the value.
                        self.lobby.add_text(update[0], normalFont, update[1], (0, 0, 0),
                                            self.text_x, self.text_y)

                #Format ["Start info", ["Client objects", p1, p2, p3], tagged_player]
                elif message[0] == "Start info":
                    # If the header is "Start info" then this means the server has started the game, the server
                    # now sends us all of player objects including our own and the current tagged player.
                    message.pop(0)
                    player_object_list = message[0]
                    tagged_player_list = message[1]
                    player_object_list.pop(0)
                    # Add all of the player objects given in the start info update to the clients dictionary with the
                    # clients number as the key and the player object as the value so that the clients specific player
                    # object can be accessed by calling self.clients[self.player_num]
                    for player_object in player_object_list:
                        self.clients[player_object.num] = player_object
                    num = tagged_player_list[1]
                    # Call the update tagged player method with the number given in the tagged player section of the
                    # start game message
                    self.update_tagged_player(num)
                    # The game has now started so we no longer want to display the lobby so we set the in_lobby variable
                    # to false and ready variable to true so that the game will start to be displayed
                    self.ready = True
                    self.in_lobby = False

                elif message[0] == "Game ended":
                    self.ended_time = time.perf_counter()
                    self.game_loser = message[1]
                    self.round_ended = True
                    #self.reset_game()

def connect_to_server(ip, port):
    # Create a socket on the client's end which is connected to the ip and port of the server and the server uses this
    # socket to send data to the client
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((ip, port))
    except:
        return None

    return server

# Create a menu for entering the ip and port of the server and a button for attempting to connect to it, if the
# connection works then we will exit this loop for the menu and then the normal code will run. This is necessary
# as when the client code is an executable you can't manually go in and alter an ip variable so there needs to be
# a user interface for doing so. If the connection isn't made meaning the server ip and port is either wrong, not
# running or an error occurs then the user will have to enter a new ip and port to try.
screen = pygame.display.set_mode((400,200), HWSURFACE | DOUBLEBUF | RESIZABLE)
connect_menu = Menu((255,215,50), "Enter Server Details", screen, None)
connect_menu.add_button("connect button", 90, 125, 140, 50, (255, 255, 255), (255, 255, 255), (0, 0, 0),
                           "Click to Connect", None, 16, 5, (0, 0, 0))
connect_menu.add_text("ip label", titleFont, "IP", (0, 0, 0), 25, 25)
connect_menu.add_text("port label", titleFont, "Port", (0, 0, 0), 175, 25)
# 172.16.3.149 School
# 192.168.0.32 Sofia gaff
# "192.168.0.92" Dads gaffatron
connect_menu.add_entry("enter IP", 25, 75, 130, 30, (0, 0, 0), 16, 2.5, (0, 0, 0), "192.168.0.92")
connect_menu.add_entry("enter port", 175, 75, 130, 30, (0, 0, 0), 16, 2.5, (0, 0, 0), "5555")
connection_successful = False
window_closed = False
server = None
while not connection_successful:
    if connect_menu.event_loop() == "Game quit":
        break
    if connect_menu.b_dict["connect button"].clicked:
        # If a character that's not a digit is entered into the port entry then when converting this value to an
        # integer an error will be encountered so I convert the string in the port to an ascii value and check if the
        # ascii value is one of a digit and if so then there won't be an error when converting to an integer so we
        # can carry on and try to connect. If not then we will reset the button click to False and put the port entry's
        # text to give an error saying it must be a digit.
        valid_port = True
        # Loop through all characters in the entry's text variable and if any of them isn't an ascii representation of
        # a digit then valid_port is false
        for char in connect_menu.e_dict["enter port"].text:
            if 48 < ord(char) > 57:
                valid_port = False

        # If we have a valid port then we want to try and connect with the port and ip
        if valid_port:
            port = int(connect_menu.e_dict["enter port"].text)
            ip = str(connect_menu.e_dict["enter IP"].text)
            # Create the client object and call the client loop method to start running it.
            server = connect_to_server(ip, port)
            # The above function will return None whenever there is an error, if there isn't an error then the
            # connection must've been successfull so we break out of the loop for the menu as we have a connection made
            if server is not None:
                break
            else:
                # If there was no connection made then we want to reset the button to not be clicked and give the
                # user a prompt to try again
                connect_menu.b_dict["connect button"].clicked = False
                connect_menu.e_dict["enter IP"].text = "Try again"
                connect_menu.e_dict["enter port"].text = "Try again"
        else:
            # If there wasn't a valid port then this must be because non digits were entered so notify the user
            # that an integer is needed in the port field and reset the button to not be clicked so that they can
            # try to connect again
            connect_menu.b_dict["connect button"].clicked = False
            connect_menu.e_dict["enter port"].text = "Integer needed"

# If server is not None then a successfull connection must've been made so we can get the main game ui running.
if server is not None:
    c = Client(server)
    c.client_loop()
