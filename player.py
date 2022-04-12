import pygame
pygame.font.init()

# Font and images used for player, images and font's can't be within player object as they cannot be serialized
# by pythons pickle module for sending over the network
myfont = pygame.font.SysFont('Comic Sans MS', 15)
tagged_img = pygame.image.load("images/TaggedPlayer.png")
player_img = pygame.image.load("images/NormalPlayer.png")
tagged_crouched_img = pygame.image.load("images/TaggedCrouched.png")
player_crouched_img = pygame.image.load("images/NormalCrouched.png")

class Player:
    def __init__(self, num, x, y):
        self.num = num
        self.x , self.y = x, y
        self.width, self.height = 25, 40
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        # Set initial velocities and acceleration
        self.velX = 240
        self.acc = 240
        self.velY = 0
        self.name = self.num
        self.bool_dict = {"tagged": False, "crouched": False, "speed_boost_active": False,
                          "double_jump_active": False, "slowness_active": False}



    def draw(self, win):
        # Based on whether the players tagged or crouched there is a different images that needs to be displayed to
        # reflect this so test these and display the correct image
        if self.bool_dict["tagged"] and not self.bool_dict["crouched"]:
            win.blit(tagged_img, (self.rect.x, self.rect.y))
        elif not self.bool_dict["tagged"] and not self.bool_dict["crouched"]:
            win.blit(player_img, (self.rect.x, self.rect.y))
        elif not self.bool_dict["tagged"] and self.bool_dict["crouched"]:
            win.blit(player_crouched_img, (self.rect.x, self.rect.y))
        elif  self.bool_dict["tagged"] and self.bool_dict["crouched"]:
            win.blit(tagged_crouched_img, (self.rect.x, self.rect.y))
        #pygame.draw.rect(win, self.colour, self.rect)
        #print("player with number "+str(self.num)+" has been drawn to the screen")

    def display_name(self, win):
        # Create a text surface from the players name and display it at an offset of 10 pixels to the left of the player
        # rect and 30 pixels above player rect
        textsurface = myfont.render(self.name, False, (0,0,0))
        win.blit(textsurface, (self.x-10,self.y-30))

    def reset_velY(self):
        self.velY = 0

    def update(self):
        # Update players rect, used if new x and y are calculated, new rect needs to be made to mirror this for
        # collisions
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

