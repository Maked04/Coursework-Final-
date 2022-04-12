import pygame
from pygame.locals import *


class Menu:
    # The menu class will have it's own window to draw everything onto, it will also have access to the screen which
    # the menu is to be displayed onto. We then draw everything onto the menus window and then scale it up too the
    # size of screen.

    def __init__(self, bc, name, screen, img):
        self.background_colour = bc  # Background colour, screen is filled with this colour then stuff displayed on top
        self.img1 = img  # Background image, everything else is displayed on top of this
        # All dictionaries have a name as key then a object or list as value
        self.b_dict = {}  # "name of button": Button Object
        self.e_dict = {}  # "name of entry": Entry Object
        self.t_dict = {}  # "name of text": [Text surface Object, [x, y]]
        self.i_dict = {}  # "name of image": [Image, [x, y]]
        self.box_dict = {}  # "name of text box": [[InnerBox, colour], [Outer box, colour]]
        self.screen = screen  # Screen is the display which the menu is displayed too.
        self.win = self.screen.copy()  # Create a copy of the screen
        pygame.display.set_caption(name)

    def draw_text(self):
        # For all text in the text dictionary we take the x and y cords and "blit" meaning display the text surface
        # onto the window at the given cords.
        text_keys = self.t_dict.keys()
        for key in text_keys:
            if key in self.t_dict:
                text_details = self.t_dict[key]
                self.win.blit(text_details[0], text_details[1])

    def draw_text_boxes(self):
        # Each key in the text box dictionary corresponds to two rect, colour pairs and we display them both
        # with the second set being the outer box first to give the text box a border.
        box_keys = self.box_dict.keys()
        for key in box_keys:
            if key in self.box_dict:
                rect1, colour1 = self.box_dict[key][0][0], self.box_dict[key][0][1]
                rect2, colour2 = self.box_dict[key][1][0], self.box_dict[key][1][1]
                pygame.draw.rect(self.win, colour2, rect2)  # Outer rect displayed first
                pygame.draw.rect(self.win, colour1, rect1)  # Inner rect displayed "on top" of outer rect

    def draw_widgets(self):
        # Each key in the button and entry dictionary's correspond to a widget type object which have
        # a draw method and we draw them to the window.
        button_keys = self.b_dict.keys()
        for key in button_keys:
            if key in self.b_dict:
                self.b_dict[key].draw_widget(self.win)

        entry_keys = self.e_dict.keys()
        for key in entry_keys:
            if key in self.e_dict:
                self.e_dict[key].draw_widget(self.win)

    def draw_images(self):
        # For all images in the images dictionary we take the x and y cords and "blit" meaning display the image
        # onto the window at the given cords.
        image_keys = self.i_dict.keys()
        for key in image_keys:
            if key in self.i_dict:
                details = self.i_dict[key]
                self.win.blit(details[0], details[1])

    def add_image(self, name, x, y, img):
        # Takes in a name for the dictionary key and then image, x and y for the value and stores in the dictionary
        self.i_dict[name] = [img, (x, y)]

    def add_box(self, name, x, y, w, h, c1, c2, bs):
        # Takes in a name for the dictionary key and then the x, y, width, height, colour for inner box, colour
        # for outer box and the border size. We then create two pygame rectangle objects where one uses the normal
        # x,y,w,h and the other uses the border size to have another rectangle which has a border all the way round the
        # inner rectangle.
        self.box_dict[name] = [[pygame.Rect(x, y, w, h), c1],
                               [pygame.Rect(x - bs, y - bs, (w + (bs * 2)), h + (bs * 2)), c2]]

    def add_button(self, name, x, y, w, h, rcb, rca, tc, tb, ta, fontsize, bs, bc):
        # Has the name and all relevant attributes for a button object as parameters then creates a button object
        # from them and stores it with the key as the name parameter.
        self.b_dict[name] = Button(x, y, w, h, rcb, rca, tc, tb, ta, fontsize, bs, bc)

    def add_entry(self, name, x, y, w, h, tc, fontsize, bs, bc, text=None):
        # Has the name and all relevant attributes for a entry object as parameters then creates a entry object
        # from them and stores it with the key as the name parameter.
        self.e_dict[name] = Entry(x, y, w, h, tc, fontsize, bs, bc, text)

    def add_text(self, name, font, text, colour, x, y):
        # Uses a default pygame system font along with the text and colour parameters to render a text surface. We then
        # store it in the text dictionary with the cords to display it at with the name parameter as the key
        font = font
        if font is None:
            font = pygame.font.SysFont('Comic Sans MS', 15)
        self.t_dict[name] = [font.render(text, False, colour), (x, y)]

    # For all delete methods we take in the name to remove which is the key in the dictionary
    def delete_box(self, name):
        self.box_dict.pop(name, None)

    def delete_button(self, name):
        self.b_dict.pop(name, None)

    def delete_entry(self, name):
        self.e_dict.pop(name, None)

    def delete_text(self, name):
        self.t_dict.pop(name, None)

    def delete_image(self, name):
        self.i_dict.pop(name, None)

    # Every time you want to display the menu frame you call the event_loop which does this
    def event_loop(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.display.quit()
                return "Game quit"  # Return something to notify user of class that the windows been closed
            if event.type == pygame.VIDEORESIZE:
                # If the window is resized then take the event size to set the screen to the correct size
                self.screen = pygame.display.set_mode(event.size, HWSURFACE | DOUBLEBUF | RESIZABLE)

            if event.type == pygame.MOUSEBUTTONUP:
                # If the mouse button is pressed then we take the position of the press and use the button and entry's
                # check if clicked method so they can update themselves.
                pos = pygame.mouse.get_pos()

                for entry in self.e_dict:
                    self.e_dict[entry].check_if_clicked(pos)

                for button in self.b_dict:
                    self.b_dict[button].check_if_clicked(pos)

            if event.type == pygame.KEYDOWN:
                # If a key is pressed then we call the entry's check keys method so that it can be updated when the user
                # types
                for entry in self.e_dict:
                    self.e_dict[entry].check_keys(event.key)

        # If the menu img1 which is the background is None then it means the user want's to use the background colour
        # so we will fill the screen with this colour
        if self.img1 is None:
            self.win.fill(self.background_colour)

        # Otherwise there must be an image to display so we scale it up too the size of the screen so it fills it
        # then we draw it at (0, 0) meaning top left corner
        else:
            self.img1 = pygame.transform.scale(self.img1, self.screen.get_rect().size)
            self.win.blit(self.img1, (0, 0))

        # We draw all text boxes in the text box dictionary first then we draw the text on top of this so it can be seen
        # We then draw all images
        self.draw_text_boxes()
        self.draw_text()
        self.draw_images()
        # The window is then scaled up to the size screen
        self.win = pygame.transform.scale(self.win, self.screen.get_rect().size)
        # We then draw the widgets onto the window, this is done after the windows scaled as they are interact able
        # so if they were scaled then the checking clicks would'nt work as the box for checking collisions wouldn't
        # be changed
        self.draw_widgets()
        # We then draw the window onto the screen
        self.screen.blit(self.win, (0, 0))

        # pygame's method for updating the screen.
        pygame.display.update()
        return "Not exited"


class Widget:
    def __init__(self, x, y, w, h, colour, font_size, border_size, border_colour, tc):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.bs = border_size
        self.bc = border_colour
        self.fontsize = font_size
        self.myfont = pygame.font.SysFont('Comic Sans MS', self.fontsize)
        self.rect_colour = colour
        self.text_colour = tc
        self.rect = pygame.Rect(self.x, self.y, self.w, self.h)
        self.innerRect = pygame.Rect(self.x + self.bs, self.y + self.bs, (self.w - (self.bs * 2)),
                                     (self.h - (self.bs * 2)))
        self.clicked = False

    def check_if_clicked(self, pos):
        x, y = pos[0], pos[1]
        x1, y1, w1, h1 = self.rect.x, self.rect.y, self.rect.w, self.rect.h
        if x1 < x < (x1 + w1):  # Check if x position of click is between the widgets left side and right side
            if y1 < y < (y1 + h1):  # Check if y position of click is between the widgets top side and bottom side
                #  If both are true then the click must be within the widgets bounding box so we set it's clicked
                # variable to true and return true
                self.clicked = True
                return True
        else:
            # if the click was not within the widgets bounding box then return false
            return False

    def draw_widget(self, win):
        # Draw the inner and outer rectangle with they're associated colours to give the widget a border
        pygame.draw.rect(win, self.bc, self.rect)
        pygame.draw.rect(win, self.rect_colour, self.innerRect)


class Button(Widget):
    def __init__(self, x, y, w, h, rcb, rca, tc, tb, ta, fontsize, bs, bc):
        # Call the parent classes init method which gives it the base variables and methods
        super().__init__(x, y, w, h, rcb, fontsize, bs, bc, tc)
        # Extra variables as buttons can change colour and text when clicked
        self.rect_colour_after = rca
        self.text_before = tb
        self.text_after = ta

    def draw_widget(self, win):
        if self.clicked:
            # If the buttons been clicked then we want to display the normal outer (border) rectangle then the inner
            # rectangle with the colour after clicked and the text after
            pygame.draw.rect(win, self.bc, self.rect)
            pygame.draw.rect(win, self.rect_colour_after, self.innerRect)
            if self.text_after is not None:
                textsurface = self.myfont.render(self.text_after, False, self.text_colour)
                # Display the text 5 + border size pixels in from the buttons x cord and the y cord for the
                # text is the buttons y cord plus a quarter of the buttons height
                win.blit(textsurface, (self.x + 5 + self.bs, (self.y + (0.25 * self.h))))
        else:

            pygame.draw.rect(win, self.bc, self.rect)
            pygame.draw.rect(win, self.rect_colour, self.innerRect)
            if self.text_before is not None:
                textsurface = self.myfont.render(self.text_before, False, self.text_colour)
                win.blit(textsurface, (self.x + 5 + self.bs, (self.y + (0.25 * self.h))))



class Entry(Widget):
    def __init__(self, x, y, w, h, tc, fontsize, bs, bc, startText=None):
        super().__init__(x, y, w, h, None, fontsize, bs, bc, tc)
        # Entry's have a default light grey inner rect and darker grey outer rect colours
        self.rect_colour = (240, 240, 240)
        self.bc = (169, 169, 169)
        # Default starting text of "Enter text" to help with user navigation
        self.text = startText
        if self.text is None:
            self.text = "Enter text"
        # Can't know if capital is already on in pygame so just assuming it's false as default
        self.capital_active = False

    def draw_widget(self, win):
        # Use the super classes draw method
        super().draw_widget(win)
        # Render a text surface based on the text variable and text colour
        textsurface = self.myfont.render(self.text, False, self.text_colour)
        # Display it at an offset from the x and y of the entry, the offset is a fraction of the width and height
        win.blit(textsurface, ((self.x + (0.045 * self.w)), (self.y + (0.11 * self.h))))

    def check_if_clicked(self, pos):
        # Override the check_if_clicked method from super class, first call the super class method
        # but then depending on what it returns from super class method
        clicked = super().check_if_clicked(pos)
        # if clicked is true then we want to reset the text variable to empty.
        if clicked:
            self.text = ""
        # if you click outside of the entry then the entry's clicked variable should be set to false so that any
        # key presses you make from then aren't added to text variable
        elif not clicked:
            self.clicked = False
            # self.text = "Enter text"

    def check_keys(self, key):
        # We only want to alter text variable if the user is currently clicked onto the entry
        if self.clicked:
            # Key 8 is backspace so we remove the last key in the text variable by using string slicing
            if key == 8:
                self.text = self.text[:-1]
            # Key 301 is the CapsLock, if capital_active is already True and we click CapsLock then we want to
            # set it too false otherwise set it too true
            elif key == 301:
                if self.capital_active:
                    self.capital_active = False
                else:
                    self.capital_active = True
            else:
                # If key is neither caps or backspace then use chr which converts key which is
                # ascii into a str then if capital is active then call the upper method to make it the uppercase of
                # that character otherwise add the lowercase of the key to the text variable
                if self.capital_active:
                    self.text += chr(key).upper()
                else:
                    self.text += chr(key).lower()


'''
screen_height = 700
screen_width = 900


# Double-buffering, as the description for the tag mentions, is using a separate block of memory to apply all the 
# draw routines and then copying that block (buffer) to video memory as a single operation.


pygame.font.init()
font_size = 16
screen = pygame.display.set_mode((screen_width,screen_height), HWSURFACE|DOUBLEBUF|RESIZABLE)


img1 = pygame.transform.scale(pygame.image.load("Kitchen.png"), screen.get_rect().size)

lobby_menu = Menu((255,215,50), "cunt",  screen)
lobby_menu.add_button("join lobby", 230, 270, 130, 50, (255, 255, 255), (255, 255, 255), (0, 0, 0), "Join lobby", None, font_size)
lobby_menu.add_label("enter name", 230, 220, 130, 30, (0, 0, 0), font_size)

lobby = Menu((255,120,120), "doge", screen)
lobby.add_button("ready button", 230, 100, 130, 50, (0, 0, 0), (0, 0, 0), (255, 255, 255), "Click to Ready Up", "readied up", font_size)
lobby.add_button("leave button", 230, 250, 130, 50, (0, 0, 0), (0, 0, 0), (255, 255, 255), "Leave lobby", None, font_size)
lobby.add_text("players list", font_size, "Players list", (0,0,255), 50,50)



in_lobby_menu = True
in_lobby = False

while True:
    lobby_menu.event_loop()
    if lobby_menu.b_dict["join lobby"].clicked:
        lobby_menu.b_dict["join lobby"].clicked = False
        lobby.add_text("player1", font_size, lobby_menu.l_dict["enter name"].text, (0, 0, 255), 50, 75)
        # NOTE TO SELF, Label text is reset to default as after ready button is clicked, the label checks for clicks
        # and sees a click outside its rect
        while True:
            lobby.event_loop()
            if lobby.b_dict["leave button"].clicked:
                lobby.b_dict["leave button"].clicked = False

                break

    #lobby.event_loop()

'''
