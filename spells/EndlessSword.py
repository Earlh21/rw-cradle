from Spells import Spell, all_player_spell_constructors
from Level import Tags, Point, Burst, TEAM_PLAYER

from mods.Cradle.Util import get_bouncing_line, get_bouncing_line_endpoints

import math

class EndlessSwordSpell(Spell):
    def on_init(self):
        self.name = "Endless Sword"
        
        self.max_charges = 8
        self.range = 0
        self.damage = 16
        self.radius = 5

        self.tags = [Tags.Metallic, Tags.Sorcery]
        self.level = 1

    def get_description(self):
        #TODO: Add description
        return "Descriptionn"

    def get_impacted_tiles(self, x, y):
        tiles = set()
        closed = set()

        open = {self.caster}

        while open:
            unit = open.pop()
            closed.add(unit)

            for stage in Burst(self.caster.level, Point(unit.x, unit.y), self.get_stat("radius")):
                for point in stage:
                    tiles.add(point)
                    found_unit = self.caster.level.get_unit_at(point.x, point.y)

                    if found_unit and Tags.Metallic in found_unit.tags and found_unit not in closed:
                        open.add(found_unit)
        
        return list(tiles)

    def cast(self, x, y):
        tiles = self.get_impacted_tiles(x, y)
        for point in tiles:
            unit = self.caster.level.get_unit_at(point.x, point.y)
            if not unit or (unit and unit.team != TEAM_PLAYER):
                self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Metallic, self)
                yield 

class RipplingSwordSpell(Spell):
    def on_init(self):
        self.name = "Rippling Sword"
        
        self.max_charges = 8
        self.range = 5
        self.damage = 16
        self.length = 24
        self.radius = 2

        self.tags = [Tags.Metallic, Tags.Sorcery]
        self.level = 1

    def get_description(self):
        #TODO: Add description
        return "Descriptionn"

    def get_impacted_tiles(self, x, y):
        angle = math.atan2(y - self.caster.y, x - self.caster.x)
        tiles = get_bouncing_line(self.caster.level, Point(self.caster.x, self.caster.y), angle, self.get_stat('length'), True)
        endpoints = get_bouncing_line_endpoints(self.caster.level, Point(self.caster.x, self.caster.y), angle, self.get_stat('length'))

        if len(endpoints) > 2:
            for point in endpoints[1:-1]:
                for stage in Burst(self.caster.level, point, self.get_stat('radius')):
                    for point in stage:
                        tiles.append(point)

        return list(filter(lambda point: point.x != self.caster.x or point.y != self.caster.y, tiles))
    
    def cast(self, x, y):
        angle = math.atan2(y - self.caster.y, x - self.caster.x)
        endpoints = get_bouncing_line_endpoints(self.caster.level, Point(self.caster.x, self.caster.y), angle, self.get_stat('length'))

        for i in range(len(endpoints) - 1):
            first = endpoints[i]
            second = endpoints[i + 1]

            for point in self.caster.level.get_points_in_line(first, second):
                if point.x == self.caster.x and point.y == self.caster.y:
                    continue
                self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Metallic, self)
                yield

            if i == len(endpoints) - 2:
                break

            for stage in Burst(self.caster.level, second, self.get_stat('radius')):
                for point in stage:
                    if point.x == self.caster.x and point.y == self.caster.y:
                        continue
                    self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Metallic, self)
                
                yield
            
            for i in range(3):
                yield

all_player_spell_constructors.append(EndlessSwordSpell)
all_player_spell_constructors.append(RipplingSwordSpell)