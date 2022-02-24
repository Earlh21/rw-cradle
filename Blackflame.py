from Spells import Spell, all_player_spell_constructors
from Level import Buff, Tags, Burst, Point, ChannelBuff
from Level import BUFF_TYPE_BLESS, STACK_NONE, EventOnDamaged

import Monsters

class VoidDragonDanceBuff(Buff):
    def __init__(self, damage, units):
        Buff.__init__(self)

        self.damage = damage
        self.units = units

        self.cancelled = False

        self.buff_type = BUFF_TYPE_BLESS
        self.name = "Void Dragon's Dance"
        self.stack_type = STACK_NONE

        self.owner_triggers[EventOnDamaged] = self.cancel
    
    def cancel(self, evt):
        self.cancelled = True

        self.owner.remove_buff(self)

    def on_unapplied(self):
        if self.cancelled:
            return
        
        for unit in self.units:
            unit.deal_damage(self.damage, Tags.Fire, self)
            unit.deal_damage(self.damage, Tags.Dark, self)

class VoidDragonDanceSpell(Spell):
    def on_init(self):
        self.name = "Void Dragon's Dance"
        
        self.max_charges = 8
        self.range = 7
        self.damage = 14
        self.radius = 4

        self.tags = [Tags.Dark, Tags.Fire, Tags.Sorcery]
        self.level = 1

    def get_description(self):
        #TODO: Add description
        return "Descriptionn"

    def cast(self, x, y):
        units = []

        for stage in Burst(self.caster.level, Point(x, y), self.get_stat("radius")):
            for point in stage:
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit and unit != self.caster:
                    units.append(unit)
            yield
        
        if units:
            self.caster.apply_buff(VoidDragonDanceBuff(self.get_stat("damage"), units), 3)

        return

class DragonsBreathSpell(Spell):
    def on_init(self):
        self.name = "Dragon's Breath"
        
        self.max_charges = 6
        self.range = 9
        self.damage = 6
        self.max_channel = 6

        self.melts_walls = 1
        self.channel = 1
        self.requires_los = False
        
        self.tags = [Tags.Dark, Tags.Fire, Tags.Sorcery]
        self.level = 1

    def get_description(self):
        #TODO: Add description
        return "Descriptionn"
    
    def get_impacted_tiles(self, x, y):
        start = Point(self.caster.x, self.caster.y)
        target = Point(x, y)
        path = self.caster.level.get_points_in_line(start, target)
        path.remove(start)
        return path

    def cast(self, x, y, channel_cast = False):
        if self.get_stat('channel') and not channel_cast:
            self.caster.apply_buff(ChannelBuff(self.cast, Point(x, y)), self.get_stat('max_channel'))
            return

        for point in self.get_impacted_tiles(x, y):
            if self.caster.level.tiles[point.x][point.y].is_wall():
                self.caster.level.make_floor(point.x, point.y)
            self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Fire, self)
            self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Dark, self)
            yield

all_player_spell_constructors.append(VoidDragonDanceSpell)
all_player_spell_constructors.append(DragonsBreathSpell)