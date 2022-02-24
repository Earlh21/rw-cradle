from Spells import Spell, all_player_spell_constructors
from Level import EventOnSpellCast, EventOnPreDamaged, Tags, Burst, Point, Buff, are_hostile, distance
from CommonContent import FireCloud, BlizzardCloud, StormCloud

from Level import BUFF_TYPE_BLESS, STACK_NONE

from mods.Cradle.Pure import PureBuff, pure_desc, pure_unaffected, mana_cloud_desc, PureCloud
from mods.Cradle.Util import get_perp_point, has_adjacent_wall, get_bouncing_line, get_bouncing_line_endpoints
import math

class MadraPulseSpell(Spell):
    def on_init(self):
        self.name = "Mana Pulse"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Sorcery]
        
        self.asset = ["Cradle", "assets", "spells", "mana_pulse"]
        
        self.max_charges = 6
        self.range = 0
        self.damage = 25
        self.radius = 7
        self.duration = 3

        self.upgrades['radius'] = (3, 2)
        self.upgrades['damage'] = (6, 2)
        self.upgrades['duration'] = (2, 2)
        self.upgrades['reflection'] = (2, 5, "Reflection", "Impacted tiles next to a wall release another 2 tile burst that doesn't damage the caster")
        
    def get_description(self):
        return ("Deals [{damage}_pure:pure] damage in a [{radius}_tile:radius] burst around the caster.\n"
                "Units are [purified] for [{duration}_turns:duration].\n"
                + pure_desc).format(**self.fmt_dict())

    # Categorize reflected points by distance from the wall
    # This gives a nicer animation
    def get_reflect_dict(self, reflect_points):
        damage_points = {}
        for point in reflect_points:
            for i, stage in enumerate(Burst(self.caster.level, point, self.get_stat("reflection"))):
                for point in stage:
                    damage_points[point] = min(i, damage_points.get(point, i))
        
        return damage_points

    def get_impacted_tiles(self, x, y):
        points = set([p for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')) for p in stage])
        if self.get_stat("reflection"):
            reflect_points = filter(lambda p: has_adjacent_wall(self.caster.level, p.x, p.y), points)
            reflect_dict = self.get_reflect_dict(reflect_points)
            points = points.union(set(reflect_dict.keys()))

        points.remove(Point(x, y))

        return list(points)

    def damage_point(self, x, y):
        if self.caster.x == x and self.caster.y == y:
            return

        unit = self.caster.level.get_unit_at(x, y)
        if unit:
            unit.apply_buff(PureBuff(), self.get_stat("duration"))

        self.caster.level.deal_damage(x, y, self.get_stat("damage"), Tags.Pure, self)

    def cast(self, x, y):
        reflect_points = []
        for stage in Burst(self.caster.level, Point(x, y), self.get_stat("radius")):
            for point in stage:
                self.damage_point(point.x, point.y)
                if has_adjacent_wall(self.caster.level, point.x, point.y):
                    reflect_points.append(point)

            yield
        
        if not self.get_stat("reflection"):
            return
        
        damage_points = sorted(self.get_reflect_dict(reflect_points).items(), key=lambda x: x[1])
        previous = None
        for point, i in damage_points:
            if previous != i:
                yield
                previous = i
            self.damage_point(point.x, point.y)

class HollowSpearSpell(Spell):
    def __init__(self):
        self.thunder_damage = 6
        self.thunder_radius = 6
        Spell.__init__(self)

    def on_init(self):
        self.name = "Hollow Spear"
        self.level = 2
        self.tags = [Tags.Pure, Tags.Sorcery]
        
        self.asset = ["Cradle", "assets", "spells", "hollow_spear"]
        
        self.max_charges = 18
        self.range = 11
        self.damage = 22
        self.radius = 1
        self.duration = 5
        
        self.upgrades["max_charges"] = (6, 2)
        self.upgrades["radius"] = (1, 2)
        self.upgrades["thunder_spear"] = (1, 3, "Thunder Spear", f"Deals {self.thunder_damage} lightning damage to enemies within 12 tiles of damaged units")
        self.upgrades["barrage"] = (1, 4, "Barrage", "Fires a perpendicular barrage of four extra spears")
        
    def get_description(self):
        return ("Deals [{damage}_pure:pure] damage to units in a [{radius}_tile:radius] burst.\n"
                "Units are [purified] for [{duration}_turns:duration].\n"
                + pure_desc).format(**self.fmt_dict())
    
    def get_barrage_lines(self, x, y):
        start_tiles = []

        start_tiles.append(get_perp_point(Point(self.caster.x, self.caster.y), Point(x, y), 4, -1))
        start_tiles.append(get_perp_point(Point(self.caster.x, self.caster.y), Point(x, y), 2, -1))
        start_tiles.append(Point(self.caster.x, self.caster.y))
        start_tiles.append(get_perp_point(Point(self.caster.x, self.caster.y), Point(x, y), 2, 1))
        start_tiles.append(get_perp_point(Point(self.caster.x, self.caster.y), Point(x, y), 4, 1))

        disp_x = x - self.caster.x
        disp_y = y - self.caster.y

        end_tiles = [Point(tile.x + disp_x, tile.y + disp_y) for tile in start_tiles]

        lines = []
        for start, end in zip(start_tiles, end_tiles):
            if not self.caster.level.is_point_in_bounds(end):
                continue
            if not self.caster.level.is_point_in_bounds(start):
                continue
            line = self.caster.level.get_points_in_line(start, end, find_clear=True)
            if line:
                lines.append(line)

        return lines

    def can_cast(self, x, y):
        self.requires_los = False if self.get_stat("barrage") else True
        return Spell.can_cast(self, x, y)

    def get_impacted_tiles(self, x, y):
        if self.get_stat("barrage"):
            lines = self.get_barrage_lines(x, y)

            tiles = []
            for line in lines:
                tiles.extend([p for stage in Burst(self.caster.level, line[-1], self.get_stat("radius")) for p in stage])
            
            return tiles
        else:
            return [p for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')) for p in stage]

    def thunder_damage_point(self, point):
        los_units = self.caster.level.get_units_in_los(point)
        for unit in los_units:
            if unit.x == point.x and unit.y == point.y:
                continue
            if distance(point, Point(unit.x, unit.y)) > self.thunder_radius:
                continue
            if not are_hostile(self.caster, unit):
                continue
                
            line = self.caster.level.get_points_in_line(point, Point(unit.x, unit.y))
            for line_point in line:
                self.caster.level.show_effect(line_point.x, line_point.y, Tags.Lightning, minor=True)
            
            unit.deal_damage(self.thunder_damage, Tags.Lightning, self)
        
    def cast(self, x, y):
        lines = []
        if self.get_stat("barrage"):
            lines = self.get_barrage_lines(x, y)
        else:
            lines.append(self.caster.level.get_points_in_line(Point(self.caster.x, self.caster.y), Point(x, y)))

        if not lines:
            return

        max_len = max([len(line) for line in lines])

        for i in range(max_len):
            for line in lines:
                if i >= len(line):
                    continue
                
                point = line[i]

                self.caster.level.show_effect(point.x, point.y, Tags.Pure, minor=True)

                if i == len(line) - 1:
                    for stage in Burst(self.caster.level, point, self.get_stat("radius")):
                        for p in stage:
                            unit = self.caster.level.get_unit_at(p.x, p.y)
                            if self.get_stat("thunder_spear") and unit:
                                self.thunder_damage_point(p)
                                
                            self.caster.level.deal_damage(p.x, p.y, self.get_stat("damage"), Tags.Pure, self)
                            
                            if unit:
                                unit.apply_buff(PureBuff(), self.get_stat("duration"))
            yield
            

class SevenStarsBuff(Buff):
    def __init__(self, point, seven_stars):
        Buff.__init__(self)
        self.seven_stars = seven_stars
        self.point = point

        self.buff_type = BUFF_TYPE_BLESS
        self.stack_type = STACK_NONE

        self.owner_triggers[EventOnSpellCast] = self.spell_cast
    
    def spell_cast(self, evt):
        self.point = Point(evt.x, evt.y)
    
    def on_init(self):
        self.name = "Seven Stars"

    def on_advance(self):
        spell = StarSpell(self.seven_stars)
        self.owner.level.act_cast(self.owner, spell, self.point.x, self.point.y, pay_costs=False)

class StarSpell(Spell):
    def __init__(self, seven_stars):
        self.seven_stars = seven_stars
        Spell.__init__(self)
    
    def on_init(self):
        self.name = "Seven Stars"
        self.tags = [Tags.Pure, Tags.Sorcery]
        self.level = 6

        self.max_charges = self.seven_stars.get_stat("max_charges")
        self.damage = self.seven_stars.get_stat("damage")
        self.radius = self.seven_stars.get_stat("radius")
    
    def cast(self, x, y):
        # Not sure why, but self.caster isn't being set
        # So use the seven_stars spell's caster for the level
        caster = self.seven_stars.caster
        level = caster.level

        for stage in Burst(level, Point(x, y), self.radius):
            for point in stage:
                level.deal_damage(point.x, point.y, self.damage, Tags.Pure, self)
                unit = level.get_unit_at(point.x, point.y)

                if unit is not None:
                    unit.apply_buff(PureBuff(), 5)
            yield

            if self.seven_stars.get_stat("burning"):
                for point in stage:
                    level.add_obj(FireCloud(caster), point.x, point.y)
                yield
            elif self.seven_stars.get_stat("frozen"):
                for point in stage:
                    level.add_obj(BlizzardCloud(caster), point.x, point.y)
                yield
            elif self.seven_stars.get_stat("voltaic"):
                for point in stage:
                    level.add_obj(StormCloud(caster), point.x, point.y)
                yield
        
class SevenStarsSpell(Spell):
    def on_init(self):
        self.name = "Seven Stars"
        self.tags = [Tags.Pure, Tags.Sorcery]
        self.level = 6

        self.asset = ["Cradle", "assets", "spells", "seven_stars"]

        self.max_charges = 2
        self.range = 12
        self.radius = 3
        self.duration = 7
        self.damage = 16

        self.requires_los = True

        self.upgrades['max_charges'] = (2, 2)
        self.upgrades['damage'] = (6, 3)
        self.upgrades['radius'] = (2, 3)
        self.upgrades['burning'] = (1, 3, "Burning Stars", "Leaves behind fire clouds", 'cloud')
        self.upgrades['frozen'] = (1, 3, "Frozen Stars", "Leaves behind ice clouds", 'cloud')
        self.upgrades['voltaic'] = (1, 3, "Voltaic Stars", "Leaves behind storm clouds", 'cloud')
        self.upgrades['duration'] = (5, 4, "Twelve Stars", "Fires 12 bursts instead of 7")
        
    def get_description(self):
        return ("For [{duration}_turns:duration], deal [{damage}_damage:pure] in a [{radius}_tile:radius] burst at the target of your most recent spell.\n"
                "Units are [purified] for [5_turns:duration].\n"
                + pure_desc).format(**self.fmt_dict())

    def get_impacted_tiles(self, x, y):
        return [p for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')) for p in stage]

    def cast_instant(self, x, y):
        buff = SevenStarsBuff(Point(x, y), self)
        self.caster.apply_buff(buff, self.get_stat("duration"))

class KingsMantle(Buff):
    def __init__(self):
        Buff.__init__(self)
        self.name = "King's Mantle"
        self.owner_triggers[EventOnPreDamaged] = self.pre_damaged
        self.spells_reflected = []

        self.buff_type = BUFF_TYPE_BLESS
        self.stack_type = STACK_NONE
    
    def pre_damaged(self, evt):
        if evt.source is None:
            return

        if evt.source in self.spells_reflected:
            return

        if not isinstance(evt.source, Spell):
            return

        if not are_hostile(self.owner, evt.source.caster):
            return

        if pure_unaffected(evt.source):
            return

        self.spells_reflected.append(evt.source)
        self.owner.level.act_cast(self.owner, evt.source, evt.source.caster.x, evt.source.caster.y, pay_costs=False)

    def on_advance(self):
        self.spells_reflected = []
        
class KingsMantleSpell(Spell):
    def on_init(self):
        self.name = "King's Mantle"
        self.tags = [Tags.Pure, Tags.Enchantment]
        self.level = 5

        self.max_charges = 4
        self.range = 0
        self.duration = 3
        
    def get_description(self):
        return ("For [{duration}_turns:duration], enemy spells that damage you are reflected back at the caster "
                "unless the spell deals physical damage.").format(**self.fmt_dict())

    def cast_instant(self, x, y):
        buff = KingsMantle()
        self.caster.apply_buff(buff, self.get_stat("duration"))

class SwordOfJudgment(Spell):
    def __init__(self):
        self.holy_damage = 5
        Spell.__init__(self)

    def on_init(self):
        self.name = "Sword of Judgment"
        self.level = 3
        self.tags = [Tags.Holy, Tags.Pure, Tags.Sorcery]
        
        self.asset = ["Cradle", "assets", "spells", "sword_of_judgment"]

        self.max_charges = 10
        self.range = 9
        self.radius = 0
        self.damage = 28

        self.upgrades['radius'] = (1, 2)
        self.upgrades['max_charges'] = (4, 2)
        self.upgrades['holy_damage'] = (4, 3, "Holy Damage")
        self.upgrades['web_of_light'] = (1, 3, "Web of Light", "Your holy units deal damage in a beam towards damaged units")

        self.requires_los = True
    
    def get_description(self):
        return ("Deals [{damage}_damage:pure] to the target.\n"
                "Your summoned holy units within line of sight deal [{holy_damage}_damage:holy] to the target.").format(**self.fmt_dict())

    def cast(self, x, y):
        holy_points = []

        for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')):
            for point in stage:
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit is not None:
                    holy_points.append(Point(unit.x, unit.y))

                self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Pure, self)

        yield

        for point in holy_points:
            los_units = self.caster.level.get_units_in_los(Point(x, y))

            for los_unit in los_units:
                if are_hostile(self.caster, los_unit):
                    continue
                if not Tags.Holy in los_unit.tags:
                    continue
                
                line = self.caster.level.get_points_in_line(Point(los_unit.x, los_unit.y), point)

                if self.get_stat("web_of_light"):
                    for line_point in line[1:]:
                        self.caster.level.deal_damage(line_point.x, line_point.y, self.get_stat('holy_damage'), Tags.Holy, self)
                    yield
                else:
                    for line_point in line:
                        self.caster.level.show_effect(line_point.x, line_point.y, Tags.Holy, minor=True)
                        yield
                    self.caster.level.deal_damage(point.x, point.y, self.get_stat('holy_damage'), Tags.Holy, self)

class ManaBulletSpell(Spell):
    def __init__(self):
        self.length = 24
        Spell.__init__(self)

    def on_init(self):
        self.name = "Mana Bullet"
        self.level = 3
        self.tags = [Tags.Pure, Tags.Sorcery]

        self.asset = ["Cradle", "assets", "spells", "mana_bullet"]

        self.max_charges = 14
        self.range = 14
        self.radius = 3
        self.damage = 20
        self.duration = 5

        self.requires_los = False

        self.upgrades["length"] = (9, 2)
        self.upgrades["duration"] = (2, 2)
        self.upgrades["radius"] = (1, 2)

    def get_description(self):
        return ("Deals [{damage}_pure:pure] damage to units.\n"
                "Bounces off walls and lasts for {length} tiles. Creates mana clouds in a [{radius}_tile:radius] burst "
                "at each bounce.\n"
                "Clouds last [{duration}_turns:duration].\n"
                + mana_cloud_desc).format(**self.fmt_dict())
    
    def get_bounce_results(self, x, y):
        angle = math.atan2(y - self.caster.y, x - self.caster.x)
        points = get_bouncing_line(self.caster.level, Point(self.caster.x, self.caster.y), angle, self.get_stat("length"), True)
        endpoints = get_bouncing_line_endpoints(self.caster.level, Point(self.caster.x, self.caster.y), angle, self.get_stat('length'))

        if len(endpoints) > 2:
            return points, endpoints[1:-1]
        else:
            return points, []

    def get_impacted_tiles(self, x, y):
        return self.get_bounce_results(x, y)[0]
    
    def cast(self, x, y):
        points, endpoints = self.get_bounce_results(x, y)
        for point in points:
            if self.caster.x == point.x and self.caster.y == point.y:
                continue

            self.caster.level.deal_damage(point.x, point.y, self.get_stat('damage'), Tags.Pure, self)
            yield

            if not point in endpoints:
                continue

            for stage in Burst(self.caster.level, point, self.get_stat('radius')):
                for burst_point in stage:
                    tile = self.caster.level.tiles[burst_point.x][burst_point.y]
                    if tile.cloud is not None:
                        tile.cloud.kill()
                    cloud = PureCloud(self.caster, self.get_stat('duration'))
                    self.caster.level.add_obj(cloud, burst_point.x, burst_point.y)

all_player_spell_constructors.append(MadraPulseSpell)
all_player_spell_constructors.append(HollowSpearSpell)
all_player_spell_constructors.append(SevenStarsSpell)
#all_player_spell_constructors.append(KingsMantleSpell)
all_player_spell_constructors.append(SwordOfJudgment)
all_player_spell_constructors.append(ManaBulletSpell)