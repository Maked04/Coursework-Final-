import socket
import pickle
import asyncore
from player import Player
from server_loop import AsyncoreThread
from path_finding import find_path
from menus import Menu
import random
import pygame
from pygame.locals import *
import time
import math
import itertools

# All fonts to be used
normalFont = pygame.font.SysFont('Comic Sans MS', 18)
subTitleFont = pygame.font.SysFont('bookmanoldstyle' , 20)
titleFont = pygame.font.SysFont('bookmanoldstyle' , 30)

# Formatted with client number: player object and a new key, value pair is added whenever a client connects
clients = {}

# Whenever an existing client joins the lobby their player object is taken from the clients dict and stored in the
# active players dictionary with the client number as key and a list with the player object and a boolean for whether
# that active player has readied up
active_players = {}

# Whenever a connection is made the information for the connection is stored with connection details: client number
connections = {}


class MainServer(asyncore.dispatcher):
    def __init__(self, port):
        # Using the super classes init method
        asyncore.dispatcher.__init__(self)
        # Create a socket object with AF_INET meaning it uses the IP V4 Protocol and SOCK_STREAM is a
        # connection-based protocol where the connection is established and the two parties
        # have a conversation until the connection is terminated by one of the parties or by a network error.
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind it to the devices current host ip address and a port provided in the init method
        self.bind((socket.gethostname(), port))

        # We now listen on this socket and the parameter 10 means the number of clients to listen for
        self.listen(10)

        # When we create the main server object we want the client number to be 0
        self.client_num = 0

    def handle_accept(self):
        # This function can detect when someone is trying to connect to the server socket and therefore runs and we
        # Accept their connection, if you wanted to block certain ip's from connecting that could be done here
        conn, address = self.accept()

        # Increase the client number by 1 every time we have a connection
        self.client_num += 1

        # Pick a random spawn point from the list of player_spawns
        spawn_point = player_spawns[random.randint(0, len(player_spawns)-1)]

        # Create a player object with the client num and spawn point and store it in the clients dictionary with the
        # client number as the key
        clients[self.client_num] = Player(self.client_num, spawn_point[0], spawn_point[1])

        # Store the connection details in the connections dictionary with the player number as
        connections[conn] = self.client_num

        # Using the send method, send a list containing the header "player num" and the clients number to the
        # connection, the list is serialized with pickle.dumps to convert it from list form to byte form for transfer
        conn.send(pickle.dumps(["Player num", self.client_num, mapFile]))


        # Create a secondary server object to handle the new connection
        s = SecondaryServer(conn)

        # Using the controllers add server method to add the new server and client number to it's list so that it
        # can use each secondary server to send information and close the connection
        controller.add_server(s, self.client_num)

        # Update window in the controller class will display the new client on the admin window with a button to allow
        # the admin to kick this client
        controller.update_window()

        print("connections: "+str(connections))
        print("clients: " + str(clients))
        print("secondary servers: " + str(controller.secondaryServers))


    def remove_conn(self, num):
        # Connections are stored with the connection as the key and client number as the value
        # We take in the client number for the client we want to remove and then using connections.items() returns
        # both the key and value and if the value matches the num parameter then the key to remove is the key from
        # this iteration and then we remove that connection by calling the pop method on the dictionary.
        to_remove = None
        for key, value in connections.items():
            if num == value:
                to_remove = key
        if to_remove is not None:
            connections.pop(to_remove)


class SecondaryServer(asyncore.dispatcher_with_send):

    def handle_read(self):
        # This method asynchronously detects whether the socket becomes readable meaning data is being transferred.
        data_from_client = None
        try:
            data_from_client = self.recv(512)
        except socket.error as e:
            print(e)
        if data_from_client is not None:
            # If data is received then call the handle update method passing the data through to it
            self.handle_update(data_from_client)
        else:
            pass

    def handle_close(self):
        # Controller stores all secondary servers to their corresponding client number so we can call the controller
        # returnServerNum method passing through self which is the secondary server object and the controller will
        # return the number associated with that secondary server object
        num = controller.returnSeverNum(self)

        # If this number is in the client list then remove it and do the same for the active_players list
        if num in clients:
            clients.pop(num)
        if num in active_players:
            print("active player removed")
            active_players.pop(num)
        # Inform all clients that this player has left
        controller.broadcast(["Player left", num])

        # Using the main_server remove connection method passing through the client number
        main_server.remove_conn(num)

        # Remove the secondary server from the controllers list of secondary servers
        controller.remove_server(self)

        # Update window which now won't display the removed client as they have been removed from the client list
        controller.update_window()

        # Close the secondary server socket
        self.close()

    def broadcast(self, message):
        # Loop through all connections and try to use the send method on all of them to send the serialized version
        # of the message parameter.
        conn_to_remove = []
        for conn in connections:
            try:
                conn.send(pickle.dumps(message))
            except socket.error as e:
                print(e)

    def handle_update(self, message):
        # Once an message is received by the secondary server we need to process it to extract the data and update
        # relevant data stores
        player_update = ["None"]
        try:
            # Use the pickle.loads method to deserialize the message
            player_update = pickle.loads(message)
        # For connections over unstable connection we allow for many errors to be ignored as they won't affect
        # the game as missing 1 client update will have 0 visual affect
        except (pickle.UnpicklingError, ImportError, EOFError, IndexError, TypeError, ValueError, UnicodeDecodeError) as e:
            print("error receiving update is: "+str(e))

        # All messages from the client are a list with the first element being a string header so we know what sort
        # of update it is

        # ["Joined lobby", num, name]
        if player_update[0] == "Joined lobby" or player_update[0] == "Left lobby":
                # When a player joins or leaves the lobby they send the server their name and then everyone else is
                # send a list containing all of the current players names to be updated or added or removed
                if controller.players_ready:
                    # If a client tries to join the lobby but the game has already started then notify them that they
                    # cant join the lobby
                    self.send(pickle.dumps(["Not joined lobby"]))
                    return
                if player_update[0] == "Joined lobby":
                    if player_update[1] in clients:
                        client_player = clients[player_update[1]]
                        # Create player object which is a duplicate of the clients skeleton player object and set the player
                        # objects name to what was provided in the update and then store the player object and a boolean
                        # for whether they have readied up (false at start) in the active players dictionary with the player
                        # number as the key
                        p = client_player
                        p.name = player_update[2]
                        active_players[p.num] = [p, False]

                # ["Left lobby", num]
                elif player_update[0] == "Left lobby":
                    # If the client has left then remove their player object from the active players dictionary
                    if player_update[1] in active_players:
                        active_players.pop(player_update[1])

                # Send an update with the header as "Current names" and all active players num and name in a list
                update = ["Current names"]
                for player in active_players:
                    update.append([active_players[player][0].num, active_players[player][0].name])
                self.broadcast(update)

        # Format ["Ready", player_num]
        elif player_update[0] == "Ready":
            # Update the active players boolean for the active player specified by the second item in the update list
            # which is the player who's readied up's number
            player_num = player_update[1]
            active_players[player_num][1] = True


        #["Player left", num]
        elif player_update[0] == "Player left":
            # If the num in the update matches the number associated with the secondary server then call the secondary
            # servers close method and inform everyone that this player has left and then close the secondary server
            num = player_update[1]
            if num in active_players:
                controller.broadcast(["Player left", num])
                num_from_controller = controller.returnSeverNum(self)
                if num == num_from_controller:
                    self.handle_close()


        # format ["Update info", [num, rect]]
        elif player_update[0] == "Update info":
            # If the game has started then update the rect of the player in the active players dictionary who's key is
            # the number in the update
            num = player_update[1][0]
            # Only edit dict if players_ready is true as when a game ends the dict is reset so key error will occur.
            if controller.players_ready:
                if num in active_players:
                    active_players[num][0].rect = player_update[1][1]

class Consumable:
    id_iter = itertools.count()

    def __init__(self, consumable_type, x, y):
        # Gives each consumable a unique id
        self.id = next(Consumable.id_iter)
        # Speed and Jump boost consumables are so similar so no need for a seperate unique class so instead they are
        # just normal consumables which have a type which dictates how long they exist for once collected.
        self.type = consumable_type
        if self.type == "Speed":
            self.life_left = 10
        elif self.type == "Jump":
            self.life_left = 5
        elif self.type == "Slow":
            self.life_left = 5
        self.collected = False
        self.collected_by = None
        # Each consumable needs an x, y and rect so that collision between the clients and the consumables can be tested
        # to see if they've been collected
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x, self.y, 25, 25)

    def consumable_collected(self):
        # Set consumables collected variable to True
        self.collected = True

    def reduce_time(self):
        # If the consumable has been collected then reduce it's life left by 1 and then check if it's still alive and
        # return this.
        if self.collected:
            self.life_left -= 1
        if self.life_left > 0:
            return "Alive"
        return "Dead"

# A class for consumable like objects that have the ability to move their position
class MovingConsumable(Consumable):
    def __init__(self, consumable_type, x, y, num):
        # Use the super/parent classes init method to give it access to the normal consumable variables and methods
        super().__init__(consumable_type, x, y)
        # The moving consumable follows a certain player so there needs to be a target player and a path for it
        # to follow.
        self.path = None
        self.targetPlayerNum = num
        # A pointer for where we are in the path list
        self.pointer = 0
        # Give it a path to start following
        self.update_path()

    def update_path(self):
        # When we get a new updated path we want to reduce the num_of_moves we've taken in this path to 0
        # Accounting for border so all y values need 50 taken away from them
        tile_path = []
        if self.targetPlayerNum in active_players:
            player = active_players[self.targetPlayerNum][0]
            # Find the shortest path from the consumable to the target player using the find_path method
            tile_path = find_path([self.x, self.y-50], [player.rect.x, player.rect.y-50])

        # The tile path is the shortest path of tiles from the tile the consumable is in to the tile the player is in
        new_path = []
        moves_per_tile = 25
        # To smooth the movement so it's not just moving from 1 tile to another which would be 25 pixels at once we want
        # to split this up into shorter movements so it's smoother, as you increase moves_per_tile the smoothness
        # increases but you'd have to increase the speed at which the consumable moves which can cause lag so as the
        # tile is 25 pixels a moves_per_tile of 25 will mean we move 1 pixel at a time which is smooth enough
        for i in range(0, len(tile_path) - 2):
            # Find the x and y distance from one tile to the next tile
            old_x, new_x = tile_path[i].x, tile_path[i + 1].x
            old_y, new_y = tile_path[i].y, tile_path[i + 1].y
            x_change = new_x - old_x
            y_change = new_y - old_y

            for a in range(1, moves_per_tile + 1):
                # Adding a fraction of the x change to the first tiles x cord and same for y cord. This will run 25
                # times and each time we add these new x and y values to the new path list. each of the values will
                # increase by a which goes from 1 to 26 and does that value divided by moves_per_tile * the change so
                # each loop we are increasing by 1/25 * change so it's a constant increment
                new_x = old_x + (x_change * (a / moves_per_tile))
                new_y = old_y + (y_change * (a / moves_per_tile))
                new_path.append([new_x, new_y])

        # As we are moving multiple times while still being in the same tile when we calculate a new path we will
        # be given a path based on the tile were still in so we will start back from that tiles position so the
        # consumable will jump back to that point. We therefore have a pointer which sais how far we currently are into
        # the path and any points up until that pointer in the path are checked to see if they exist in the new path
        # as well and if they do then they are removed as we have already moved to those locations so this
        # "jumping back" will no longer occur.
        to_remove = []
        for i in range(0, self.pointer):
            path1 = self.path[i]
            for path2 in new_path:
                if path1 == path2:
                    to_remove.append(path2)
        for path in to_remove:
            new_path.remove(path)
        self.path = new_path
        # Set the pointer to 0 so we start at the first point in the new path
        self.pointer = 0


    def update_pos(self, x, y):
        # Update x, y and rect so the consumable is actually moved so collisions and displaying it are in the correct
        # location
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x, self.y, 25, 25)

    def follow_path(self):
        if self.targetPlayerNum in active_players:
            # Get the target players x and y co-ordinates if they are an active player
            player = active_players[self.targetPlayerNum][0]
            x_change = player.rect.x-self.x
            y_change = player.rect.y-self.y
            # As the player exists over multiple tiles, the consumable may think it's at the player but could be
            # a tile away so using pythagoras to determine the manhattan distance from the consumable to the player
            # and if it's within a certain distance then we just say it's hit the player so we update the consumables
            # location to match the players location
            if math.sqrt((x_change * x_change) + (y_change * y_change)) < 50:
                self.update_pos(player.rect.x, player.rect.y)

            if self.path is not None:
                # If there is any new points in the path to move to
                if len(self.path) > 1:
                    # Check if pointer points to a valid location in the path list
                    if self.pointer < len(self.path):
                        new_location = self.path[self.pointer]
                        # Tile.x is index position in matrix so values must be multiplied by rect size then
                        # add 50 back on to account for the border
                        self.update_pos((new_location[0]*25), (new_location[1]*25)+50)
                        self.pointer += 1


class Controller:
    def __init__(self):
        self.secondaryServers = {}
        self.consumable_object_list = []
        self.players_ready = False
        self.start_time = None
        # Used to track how many times we've sent the end game message as we want to send it multiple times to guarantee
        # that the client knows the games ended.
        self.sent_count = 0
        self.consumable_spawns  = self.create_spawn_map()
        #Admin window stuff
        self.screen = pygame.display.set_mode((300, 600), HWSURFACE | DOUBLEBUF | RESIZABLE)
        self.text_x, self.text_y = 50, 75
        self.running = True
        self.admin_window = self.setup_window()


    def setup_window(self):
        # Using the menu class to create a UI for the admin of the server which has a text box containing all
        # clients and a button to kick each one
        window = Menu((255, 120, 120), "lobby", self.screen, None)
        window.add_text("admin window", titleFont, "Admin window", (0, 0, 0), 50, 0)

        window.add_box("client list box", 25, 50, 250, 500, (255, 255, 255), (0, 0, 0), 5)
        window.add_text("client list", subTitleFont, "Client list: ", (0, 0, 0), self.text_x, self.text_y)

        self.text_y += 50

        return window

    def window_loop(self):
        if self.running:
            # Uses the menu objects event loop to display the menu and check for inputs.
            if self.admin_window.event_loop() == "Game quit":
                self.running = False
            else:
                # Check for any buttons clicked, if a button has been clicked then the client associated to that
                # button should have it's corresponding secondary servers handle close method called
                buttons_clicked = []
                # Add all clicked buttons keys to a list
                for b_key in self.admin_window.b_dict:
                    if self.admin_window.b_dict[b_key].clicked:
                        buttons_clicked.append(b_key)
                if len(buttons_clicked) > 0:
                    to_kick = []
                    # The secondary server is linked to the client number and the buttons are linked to a client number
                    # so if they match then we call the secondary servers handle close method as they've been "kicked"
                    for num in buttons_clicked:
                        for key, value in self.secondaryServers.items():
                            if num == value:
                                to_kick.append(key)
                    for server in to_kick:
                        server.handle_close()

    def update_window(self):
        # Called whenever a client is added or removed
        to_remove = []
        # Set starting location for text to be displayed at
        self.text_x, self.text_y = 50, 100
        # Remove all objects from menu that aren't a set few which removes all client text and client buttons using
        # the menus remove object methods.
        for text in self.admin_window.t_dict:
            if text != "client list" and text != "admin window":
                to_remove.append(text)
        for remove in to_remove:
            self.admin_window.delete_text(remove)
            self.admin_window.delete_button(remove)
        # For each client in the clients list we want to display their number and then create a button beside this
        # which has a key of the clients number so that when it's clicked the corresponding client number is used to
        # kick them from the game
        for client in clients:
            self.text_y += 50
            self.admin_window.add_text(client, normalFont, f"Player: {client}", (0, 0, 0),
                                self.text_x, self.text_y)
            self.admin_window.add_button(client, self.text_x+75, self.text_y, 60, 30, (0,255,0), (255,0,0), (0, 0, 0),
                              "Kick", "Kicked", 16, 2, (0,0,0))

    def create_spawn_map(self):
        # Create a spawn map for consumables by going through the game map and finding locations that aren't blocks
        # so that they can be accessed by players and adding all these locations to a list then returning them
        list = []
        size = 25
        border_size = 50
        for y in range(len(tile_map)):
            for x in range(len(tile_map[0])):
                if int(tile_map[y][x]) == 0:
                    list.append([x * size, (y * size) + border_size])
        return list

    def add_consumable(self):
        # If statement guarantees that no more than 3 consumables can be in game at once
        if len(self.consumable_object_list) <= 2:
            # If there is less than 3 consumables in the game then we wan't to pick a random type of consumable to spawn
            # in, there is 3 different consumable types so generate a random number from 1 to 3
            ran_num = random.randint(1,3)
            # Pick a random spawn point in the list of available spawn points in the map
            spawn = self.consumable_spawns[random.randint(0, len(self.consumable_spawns)-1)]
            if ran_num == 1:
                # Adding a new consumable object of type "jump" and adding it to the consumable object list with cords
                self.consumable_object_list.append(Consumable("Jump", spawn[0], spawn[1]))
            elif ran_num == 2:
                # Adding a new consumable object of type "speed" and adding it to the consumable object list with cords
                self.consumable_object_list.append(Consumable("Speed", spawn[0], spawn[1]))
            elif ran_num == 3:
                players = []
                # Add all active players to a list
                for player in active_players:
                    players.append(active_players[player][0])
                if len(players) != 0:
                    # Pick a random player from this list of active players for the moving consumable to target
                    player = players[random.randint(0, len(players)-1)]
                    # Create a moving consumable object with type "slow" and add it to the consumable object list with
                    # it's current co-ordinates
                    self.consumable_object_list.append(MovingConsumable("Slow", spawn[0], spawn[1], player.num))

    def check_consumable_collision(self):
        # Format [[consumable_num, consumable_type, player_num]]
        # Loop through all consumables and all players to see if any player collected any consumable by calling
        # the collide rect which checks collision between the consumables rect and the players rect and if this method
        # returns true then there was a collision so we want to set the consumables collected variable to true so it's
        # an active consumable and set the collected by variable to the player object so that specific player will be
        # affected by the consumable
        for consumable in self.consumable_object_list:
            for player in active_players:
                if pygame.Rect.colliderect(active_players[player][0].rect, consumable.rect):
                    consumable.collected = True
                    consumable.collected_by = active_players[player][0].num

    def move_consumables(self):
        # For all moving consumables which are ones with type "slow" we wan't to call their follow path method
        for consumable in self.consumable_object_list:
            if consumable.type == "Slow":
                consumable.follow_path()

    def update_consumables(self):
        to_remove = []
        for consumable in self.consumable_object_list:
            if consumable.type == "Slow":
                # Update the consumables path to move along as the player will be moving so we need to create a new
                # path their new location if they've moved
                consumable.update_path()
            # Call the reduce time method for all consumables
            result = consumable.reduce_time()
            # If "Dead" is returned from this then we need to remove this consumable from the list of consumables
            if result == "Dead":
                to_remove.append(consumable)
        for consumable in to_remove:
            self.consumable_object_list.remove(consumable)

    def returnSeverNum(self, server):
        # Given a server as the key return the value associated with it if it exits in the secondary servers list.
        if server in self.secondaryServers:
            return self.secondaryServers[server]

    def add_server(self, server, num):
        # Add a dictionary item with the server object as key and client number as value, both these values are supplied
        # by the parameters
        self.secondaryServers[server] = num

    def remove_server(self, server):
        # Remove a given secondary server from the list of secondary servers
        self.secondaryServers.pop(server)

    def broadcast(self, message):
        # All broadcasts from controller are messages for players currently playing so only send message to connections
        # who are in the game
        current_dict_keys = self.secondaryServers.keys()
        for server in current_dict_keys:
            if self.secondaryServers[server] in active_players:
                # Send the gamestate to all scondary servers that are handling clients that are in the game
                try:
                    server.send(pickle.dumps(message))
                except socket.error as e:
                    print("error in controller broadcast thing")
                    print(e)

    def find_tagged_player(self):
        # Loop through all active players to find which one has it's "tagged" variable which exists in the player
        # objects dictionary set to true and return the player number of this player
        tagged = None
        for player in active_players:
            if active_players[player][0].bool_dict["tagged"]:
                tagged = active_players[player][0].num
        return tagged

    def pick_tagged_player(self):
        # Picks a random active player to start tagged
        # Get a random number from 0 to the length of the active players list
        index = random.randint(0, len(active_players) - 1)
        # Pass this random number into the dictionary key from index method which will return a key in active players
        # from this random number
        key = dict_key_from_index(active_players, index)
        # Get the player object from that key and return the player objects number
        num = active_players[key][0].num
        #print("player with num: " + str(num) + " was randomly selected to be tagged")
        return ["Tagged player", num]

    def check_if_all_ready(self):
        if len(active_players) > 0:
            # Set ready to true
            players_ready = True
            for player in active_players:
                # If any player isnt ready then set players ready to false
                if not (active_players[player][1]):
                    players_ready = False

            if players_ready:
                # If all players are ready then we need to send the start information for the game, this includes
                # all active player objects and the starting player to be tagged using the pick tagged player method.
                message = ["Start info", ["Client objects"]]
                for player in active_players:
                    message[1].append(active_players[player][0])
                result = self.pick_tagged_player()
                message.append(result)
                self.broadcast(message)
                # Only set player tagged variable to true once we have sent the clients the player objects
                active_players[result[1]][0].bool_dict["tagged"] = True

                # Set players_ready variable to true so that we start sending game state updates and also set the
                # start time variable to the current time so that the time playing can be calculated
                self.players_ready = True
                self.start_time = time.perf_counter()
            else:
                self.players_ready = False

    def update_game_timer(self):
        # 100 is the length of the game so we minus the current time minus the start time and round this value
        # to give us the time left in the game.
        time_left = round(20-(time.perf_counter()-self.start_time), 1)
        if time_left <= 0 or len(active_players) <= 0:
            tagged_player = self.find_tagged_player()

            # Once the timer runs out this will still run 5 times to make sure that the client has received
            # the update about the game ending.
            if self.sent_count > 5:
                for player in active_players:
                    # Reset all player variables to default and pick a new random spawn for the next game
                    active_players[player][1] = False
                    p = active_players[player][0]
                    p.bool_dict["tagged"] = False
                    spawn_point = player_spawns[random.randint(0, len(player_spawns) - 1)]
                    p.x, p.y = spawn_point[0], spawn_point[1]
                    p.update()
                # There is now no active players as all players are returned to lobby menu so clear this dictionary
                active_players.clear()

                # To stop sending game state updates we set players ready to false
                self.players_ready = False
                self.sent_count = 0
                self.consumable_object_list = []

            # send to all active players the fact that the game has ended and the player who ended being tagged
            # therefore the one lost
            self.broadcast(["Game ended", tagged_player])
            # We want to make sure clients receive this message before they receive another game state update
            time.sleep(0.1)
            self.sent_count += 1
            return None
        return time_left

    def check_collision(self, previous_time):
        key = None
        hit_list = []

        # Find client in clients dict who's player object has the tagged variable set to True
        key = self.find_tagged_player()

        # If tagged player is found, check rect collision between this player and all other players and
        # add these players to hit_list
        if key is not None:
            for player in active_players:
                # Check that player is not the tagged player
                if player != key:
                    if not active_players[player][0].bool_dict["tagged"]:
                        # If the player is not the tagged player then we want to test collision between the
                        # tagged player and this player and add it too a hit list
                        if pygame.Rect.colliderect(active_players[key][0].rect, active_players[player][0].rect):
                            hit_list.append(player)
            # If collisions are found then set the original tagged players tagged variable to False then
            # randomly pick a player from hit_list to be the one who's now tagged and broadcast this
            if len(hit_list) > 0:
                # Only set new tagged player if it's been 3 seconds since someone was previously tagged
                if (time.perf_counter() - previous_time) > 3:
                    # When someones tagged we record the time it happened
                    previous_time = time.perf_counter()
                    # If multiple players collided with the tagged player at once then we still have to decide which
                    # player will end up tagged so we just pick a random one of the players in the hit list
                    player_tagged = active_players[hit_list[random.randint(0, len(hit_list) - 1)]][0]
                    # Set all active players tagged variable to false then set the new tagged players tagged variable to
                    # true
                    for player in active_players:
                        active_players[player][0].bool_dict["tagged"] = False
                    player_tagged.bool_dict["tagged"] = True
        # This will either be the same as when we entered the method if no one new has been tagged so it can be
        # used again when next checking collision or it will be the new time that someone was tagged at
        return previous_time

    def send_update(self):
        # Each update is in the format of ["Update info", [num,rect], [num,rect], ["Tagged player", num],
        # ["Consumables", ["Consumable type", "Consumable rect", player_collided]],["Time left", time]]
        update = ["Update info"]
        # Get current tagged player
        current_tagged = ["Tagged player", self.find_tagged_player()]
        # Add all active player objects num and rect
        for player in active_players:
            p = active_players[player][0]
            update.append([p.num, p.rect])
        # Add tagged player
        update.append(current_tagged)
        # Add consumables with their type, rect and who collected them so the client can display them properly and
        # add the affect of the consumable if they collected it
        consumable_update = ["Consumables"]
        for consumable in self.consumable_object_list:
            consumable_update.append([consumable.type, consumable.rect, consumable.collected_by])
        update.append(consumable_update)
        # Call the update game timer which calculates the new time left for the game and whether it's over
        time_left = self.update_game_timer()
        if time_left is not None:
            # Add the time left to the update
            update.append(["Time left", time_left])
            # Finally once all of this has been added we use the broadcast method to send it too all active players
            self.broadcast(update)


def dict_key_from_index(dict, index):
    # Dictionaries have no order so you can't access them with an index so instead we create an empty list, add all
    # of the elements of the dictionary to the list and we can then return the value at the index of the list which
    # can then be used to find the element in the dictionary.
    list = []
    for element in dict:
        list.append(element)

    return list[index]

def index_from_dict_key(dict, key):
    # Go through all elements in the dict increasing the index variable by 1 until we find the element matches the
    # key then return the index
    i=0
    for element in dict:
        if element == key:
            return i
        i += 1
    print("key not in dict")

def create_player_spawns(map, tile_size):
    # Go through the entire map and find a location that isn't a block, we then test the tile below to see if it's
    # also not a block so there is room for player to be spawned then we add the location of the first block to the
    # valid spawns list and return it
    valid_spawns = []
    for x in range(0, len(map[0])):
        for y in range(0, len(map)):
            if map[y][x] == 0:
                pos = [(x * tile_size), ((2 * tile_size) + (y * tile_size))]
                if y < len(map)-1:
                    if map[y + 1][x] == 0:
                        valid_spawns.append([pos[0], pos[1]])
    return valid_spawns

def create_map(rle_map):
    # Decompress from rle
    normal_list = []
    for y in range(0, len(rle_map)):
        normal_list.append([])
        for x in range(0, len(rle_map[y]), 3):
            count = (int(rle_map[y][x])*10)+int(rle_map[y][x+1])
            for i in range(count):
                normal_list[y].append(int(rle_map[y][x+2]))
    return normal_list

# We store the map file in rle so we need to convert it back to use it in the server script for spawn locations etc
# and sending the map to the clients. We compress the map so it's not too long to send in one single socket message.
mapFile = open("map.txt","r").read().splitlines()
tile_map = create_map(mapFile)

tile_size = 25
player_spawns = create_player_spawns(tile_map, tile_size)

# Create the controller object for the game
controller = Controller()

# Create the main server, if we wanted multiple different games running at same time then we could create many of these
# objects
main_server = MainServer(5555)
# Create a thread for running the main server on using the custom AsyncoreThread object and then start that thread
t2=AsyncoreThread()
t2.start()

# Set time variables which are used to make things happen after a certain amount of time.
previous_time = time.perf_counter()

last_send = time.perf_counter()
check_ready_cooldown = time.perf_counter()
check_collision_cooldown = time.perf_counter()

add_consumable_cooldown = time.perf_counter()
update_consumable_cooldown = time.perf_counter()
move_consumable_cooldown = time.perf_counter()

while asyncore.socket_map:
    #asyncore.loop(timeout=1, count=1)
    # Call the window loop method which updates the admin window
    controller.window_loop()

    if not controller.players_ready:
        # If all the players aren't currently ready then every half a second check to see if they have all readied up
        if time.perf_counter()-check_ready_cooldown > 0.5:
            controller.check_if_all_ready()
            check_ready_cooldown = time.perf_counter()

    else:
        # Check collision between players and player and also players and consumables every 0.1 seconds
        if time.perf_counter() - check_collision_cooldown > 0.1:
            previous_time = controller.check_collision(previous_time)
            controller.check_consumable_collision()
            check_collision_cooldown = time.perf_counter()

        # Spawn a new consumable every 5 seconds
        if time.perf_counter() - add_consumable_cooldown > 5:
            controller.add_consumable()
            add_consumable_cooldown = time.perf_counter()

        # Update consumables which reduces their life left and if it's a moving consumable then create a new path
        # for it to follow
        if time.perf_counter() - update_consumable_cooldown > 1:
            controller.update_consumables()
            update_consumable_cooldown = time.perf_counter()

        # Move the consumable to it's next pre calculated location, the 0.008 means we move the consumable this
        # often so changing this number affects its speed
        if time.perf_counter() - move_consumable_cooldown > 0.008:
            controller.move_consumables()
            move_consumable_cooldown = time.perf_counter()

        # Send the game state update every 5 milliseconds, decreasing this number can make the game run smoother but
        # can also cause it too crash if the hardware can't handle sending updates that quickly
        if time.perf_counter()-last_send > 0.05:
            controller.send_update()
            last_send = time.perf_counter()