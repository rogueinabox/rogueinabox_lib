class RogueFrameInfo:
    """Provides a convenient interface to access information about a rogue frame"""

    def __init__(self, pixel, map, statusbar, screen):
        """
        :param dict[str, dict[str, list[tuple[int,int]]]] pixel:
        :param list[list[str]] map:
        :param dict[str, int | str] statusbar:
        :param list[str] screen:
        """
        self.pixel = pixel
        self.map = map
        self.statusbar = statusbar
        self.screen = screen

    def get_tile_below_player(self):
        """Returns the tile below the player, which is not visible on the screen"""
        pos = self.get_player_pos()
        return self.get_environment_tile_at(pos)

    def get_environment_tile_at(self, pos):
        """Return the tile at the given position

        :param tuple[int,int] pos:
            coordinates of the tile
        :return:
            tile string
        """
        x, y = pos
        if x >= 0 and y >= 0 and x < len(self.map) and y < len(self.map[x]):
            return self.map[x][y]
        return ' '

    def get_player_pos(self):
        """Returns the coordinates of the position of the rogue

        :rtype tuple[int, int]
        :return:
            rogue coordinates
        """
        return self.pixel["agents"]["@"][0]

    def has_statusbar(self):
        """Returns whether the frame contains the status bar"""
        return not self.statusbar["is_empty"]

    def get_list_of_positions_by_tile(self, tile):
        """Returns a list of all positions containing the given tile

        TODO: should we list all rogue tiles here?

        :param str tile:
             tile looked for, i.e. '+' for doors, '#' for corridors and so on
        :rtype list[tuple[int, int]]
        :return:
            possibly empty list of coordinates
        """
        for tile_type, tiles_positions in self.pixel.items():
            try:
                return tiles_positions[tile]
            except KeyError:
                continue
        return []

    def get_list_of_positions_by_type(self, tile_type):
        """Returns a list of all positions containing tiles of the given type.
        See 'tile_type' for the available types.

        :param str tile_type:
            type of tile looked for.
            The available types are:
                "environment"
                    doors, floors, corridors, ...
                "items"
                    anything that can be picked up by stepping on it
                "monsters"
                    hostile entities
                "agents"
                    the rogue
        :rtype list[tuple[int, int]]
        :return:
            possibily empty list of coordinates
        """
        result = []
        try:
            tiles_positions = self.pixel[tile_type]
            for tile, positions in tiles_positions.items():
                # TODO: is using a set useful here?
                # it is useful only if two tiles of the same type (e.g. environment tiles like doors, floors and corridors)
                # could be on the same position AND we don't want to insert that same position twice in the list
                # otherwise it's a waste of time
                result = list(set().union(result, positions))
        except KeyError:
            pass
        return result

    def get_list_of_walkable_positions(self):
        """Return the list of positions that can be walked on

        :rtype list[tuple[int, int]]
        :return:
            possibily empty list of coordinates
        """
        corridors = self.get_list_of_positions_by_tile("#")
        doors = self.get_list_of_positions_by_tile("+")
        floors = self.get_list_of_positions_by_tile(".")
        items = self.get_list_of_positions_by_type("items")
        # TODO: is using a set useful here?
        # same reasons as above
        return list(set().union(corridors, doors, floors, items))

    def get_tile_count(self, tile):
        """Returns the number of occurrences of the given tile on the screen

        TODO: should we list all rogue tiles here?

        :param str tile:
             tile looked for, i.e. '+' for doors, '#' for corridors and so on
        :rtype int
        :return:
            number of occurrences of the given tile
        """
        return len(self.get_list_of_positions_by_tile(tile))

    def get_known_tiles_count(self):
        """Returns the number of all non-empty tiles on the screen"""
        return sum(len(self.get_list_of_positions_by_type(tile_type)) for tile_type in self.pixel)
