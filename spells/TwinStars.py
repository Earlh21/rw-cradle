from Spells import InfernoCloud, Spell, all_player_spell_constructors
from Level import Tags, Burst, Point, Buff, are_hostile, EventOnDamaged, Unit
from CommonContent import BlizzardCloud, FireCloud, Poison, SimpleMeleeAttack, StormCloud, apply_minion_bonuses
from Monsters import Bloodghast, Ghost, GhostFire, GhostKing, GhostMass
import random
import math

from Level import BUFF_TYPE_BLESS, STACK_NONE

from mods.Cradle.Pure import PureCloud, PureBuff, pure_desc, mana_cloud_desc
from mods.Cradle.Util import get_perp_point_slope

class HollowDomainSpell(Spell):
    def __init__(self):
        self.overload_damage = 4
        Spell.__init__(self)

    def on_init(self):
        self.name = "Hollow Domain"
        self.level = 3
        self.tags = [Tags.Pure, Tags.Enchantment]

        self.asset = ["Cradle", "assets", "spells", "hollow_domain"]
        
        self.max_charges = 4
        self.range = 0
        self.damage = 0
        self.radius = 10
        self.duration = 8

        self.upgrades['radius'] = (4, 2)
        self.upgrades['duration'] = (3, 2)
        self.upgrades['healing'] = (6, 2, "Healing Mana", f"Friendly units absorb these mana clouds to heal for 6 HP")
        self.upgrades['overload'] = (1, 3, "Overload", f"Deal {self.overload_damage} elemental damage in a 1 tile burst when a mana cloud replaces an elemental cloud")

    def get_description(self):
        return ("Creates clouds of pure mana in a [{radius}_tile:radius] radius around the caster.\n"
                "Clouds last [{duration}_turns:duration] turns.\n"
                + mana_cloud_desc).format(**self.fmt_dict())
    
    def get_impacted_tiles(self, x, y):
        return [p for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')) for p in stage]

    def cast(self, x, y):
        tiles = self.get_impacted_tiles(x, y)

        for i, point in enumerate(tiles):
            tile = self.caster.level.tiles[point.x][point.y]
            if tile.cloud is not None:
                if self.get_stat("overload"):
                    damage_type = None
                    if isinstance(tile.cloud, BlizzardCloud):
                        damage_type = Tags.Ice
                    elif isinstance(tile.cloud, FireCloud) or isinstance(tile.cloud, InfernoCloud):
                        damage_type = Tags.Fire
                    elif isinstance(tile.cloud, StormCloud):
                        damage_type = Tags.Lightning
                    
                    if damage_type is not None:
                        for stage in Burst(self.caster.level, tile, self.get_stat("overload")):
                            for burst_point in stage:
                                self.caster.level.deal_damage(burst_point.x, burst_point.y, self.overload_damage, damage_type, self)
                        yield
                
                tile.cloud.kill()

            cloud = PureCloud(self.caster, self.get_stat("duration"), self.get_stat("healing"))
            self.caster.level.add_obj(cloud, point.x, point.y)
            
            if i % 8 == 0:  
                yield

class SoulCloakBuff(Buff):
    def __init__(self, radius, resonance_radius):
        Buff.__init__(self)

        self.radius = radius
        self.resonance_radius = resonance_radius

        self.name = "Soul Cloak"
        self.description = f"Unit deals their melee damage to all enemies in a {radius} tile radius every turn."

        self.buff_type = BUFF_TYPE_BLESS
        self.stack_type = STACK_NONE

    def find_melee_attack(self, unit):
        for spell in unit.spells:
            if isinstance(spell, SimpleMeleeAttack):
                return spell

        return None

    def resonance_burst(self, attack, enemy):
        for stage in Burst(self.owner.level, Point(enemy.x, enemy.y), self.resonance_radius):
            for point in stage:
                unit = self.owner.level.get_unit_at(point.x, point.y)

                if unit is not None and are_hostile(self.owner, unit):
                    unit.deal_damage(attack.get_stat("damage"), attack.damage_type, self)

    def on_advance(self):
        attack = self.find_melee_attack(self.owner)
        if attack is None:
            return
        
        for stage in Burst(self.owner.level, Point(self.owner.x, self.owner.y), self.radius):
            for point in stage:
                unit = self.owner.level.get_unit_at(point.x, point.y)

                if unit is None:
                    continue

                if are_hostile(self.owner, unit):
                    unit.deal_damage(attack.get_stat("damage"), attack.damage_type, self)

                if self.resonance_radius is not None and unit.has_buff(PureBuff):
                    self.resonance_burst(attack, unit)

class SoulCloakSpell(Spell):
    def on_init(self):
        self.name = "Soul Cloak"
        self.level = 3
        self.tags = [Tags.Pure, Tags.Enchantment]

        self.asset = ["Cradle", "assets", "spells", "soul_cloak"]
        
        self.max_charges = 6
        self.range = 9
        self.radius = 3
        self.duration = 12
        self.resonance_radius = 2

        self.upgrades['duration'] = (5, 2)
        self.upgrades['radius'] = (2, 3)
        self.upgrades['resonance'] = (1, 4, "Resonance", f"Purified enemies repeat the damage to enemies in a [{self.resonance_radius}_tile:radius] burst.")
    
    def get_description(self):
        return ("Target a friendly unit.\n"
                "That unit deals their melee damage to all enemies in a [{radius}_tile:radius] burst every turn.\n"
                "Lasts [{duration}_turns:duration].\n").format(**self.fmt_dict())

    def get_impacted_tiles(self, x, y):
        return [p for stage in Burst(self.caster.level, Point(x, y), self.get_stat('radius')) for p in stage]

    def can_cast(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        return Spell.can_cast(self, x, y) and unit is not None and unit.team == self.caster.team
    
    def cast_instant(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        if unit is not None:
            resonance_radius = self.get_stat("resonance") if self.get_stat("resonance") else None
            buff = SoulCloakBuff(self.get_stat("radius"), resonance_radius)
            unit.apply_buff(buff, self.get_stat("duration"))

class EmptyPalmSpell(Spell):
    def on_init(self):
        self.name = "Empty Palm"
        self.level = 1
        self.tags = [Tags.Pure, Tags.Sorcery]

        self.asset = ["Cradle", "assets", "spells", "empty_palm"]
        
        self.max_charges = 20
        self.damage = 21
        self.range = 2
        self.duration = 5

        self.upgrades['damage'] = (8, 2)
        self.upgrades['range'] = (2, 1)
        self.upgrades['cardinal projection'] = (1, 1, "Cardinal Projection", "This spell is repeated in all cardinal directions")
        self.upgrades['empty echo'] = (1, 2, "Empty Echo", "Damaging purified units spawns a ghost")
    
    def get_description(self):
        return ("Deals [{damage}_pure:pure] damage to a unit.\n"
                "That unit is [purified] for [{duration}_turns:duration].\n"
                + pure_desc).format(**self.fmt_dict())

    def can_cast(self, x, y):
        unit = self.caster.level.get_unit_at(x, y)
        return Spell.can_cast(self, x, y) and unit is not None

    def get_impacted_tiles(self, x, y):
        x_dist = x - self.caster.x
        y_dist = y - self.caster.y

        tiles = []

        if self.get_stat("cardinal projection"):
            tiles.append(Point(self.caster.x + x_dist, self.caster.y + y_dist))
            tiles.append(Point(self.caster.x + y_dist, self.caster.y - x_dist))
            tiles.append(Point(self.caster.x - x_dist, self.caster.y - y_dist))
            tiles.append(Point(self.caster.x - y_dist, self.caster.y + x_dist))
        else:
            tiles.append(Point(x, y))
        
        return tiles
    
    def cast_instant(self, x, y):
        tiles = self.get_impacted_tiles(x, y)

        for tile in tiles:
            unit = self.caster.level.get_unit_at(tile.x, tile.y)
            if unit is not None:
                if self.get_stat('empty echo') and unit.has_buff(PureBuff):
                    ghost = Ghost()
                    ghost.turns_to_death = 14
                    apply_minion_bonuses(self, ghost)
                    self.summon(ghost, Point(x, y))
                
                unit.apply_buff(PureBuff(), self.get_stat("duration"))
            
            self.caster.level.deal_damage(tile.x, tile.y, self.get_stat("damage"), Tags.Pure, self)

class WordOfEmptiness(Spell):
    def on_init(self):
        self.name = "Word of Emptiness"
        self.level = 1
        self.tags = [Tags.Pure, Tags.Sorcery]

        self.max_charges = 1
        self.duration = 5
        self.radius = 3
        self.range = 0

        self.upgrades['duration'] = (5, 2)
        self.upgrades['max_charges'] = (1, 3)
        self.upgrades['radius'] = (1, 2)

    def get_description(self):
        return ("Apply [purified] to all enemies for [{duration}_turns:duration].\n"
                "Spawn mana clouds in a [{radius}_tile:radius] burst at each enemy.\n"
                "Mana clouds last [4_turns:duration].\n"
                + mana_cloud_desc).format(**self.fmt_dict())
    
    def get_impacted_tiles(self, x, y):
        tiles = set()
        for unit in self.caster.level.units:
            if not are_hostile(self.caster, unit):
                continue

            for stage in Burst(self.caster.level, Point(unit.x, unit.y), self.get_stat("radius")):
                for p in stage:
                    tiles.add(p)
        
        return list(tiles)

    def cast(self, x, y):
        self.caster.xp += 100
        for unit in self.caster.level.units:
            if not are_hostile(self.caster, unit):
                continue

            unit.apply_buff(PureBuff(), self.get_stat("duration"))
            
            for stage in Burst(self.caster.level, Point(unit.x, unit.y), self.get_stat("radius")):
                for point in stage:
                    tile = self.caster.level.tiles[point.x][point.y]
                    if tile.cloud is not None:
                        tile.cloud.kill()
                    cloud = PureCloud(self.caster, 4, 0)
                    self.caster.level.add_obj(cloud, point.x, point.y)
            yield

class Shred(Spell):
    def on_init(self):
        self.name = "Shred"
        self.description = "Desc"
    
    def spawn_clouds(self):
        clouds_left = self.get_stat("cloud_count")
        for stage in Burst(self.caster.level, Point(self.caster.x, self.caster.y), self.caster.level.width):
            for point in stage:
                if point.x == self.caster.x and point.y == self.caster.y:
                    continue

                tile = self.caster.level.tiles[point.x][point.y]
                if tile.cloud is not None:
                    if isinstance(tile.cloud, PureCloud):
                        continue
                    tile.cloud.kill()
                
                cloud = PureCloud(self.caster.source.caster, self.get_stat("duration"), 0)
                self.caster.level.add_obj(cloud, point.x, point.y)
                clouds_left -= 1

                if clouds_left < 1:
                    return

    def cast(self, x, y):
        for stage in Burst(self.caster.level, Point(self.caster.x, self.caster.y), self.get_stat("radius")):
            for point in stage:
                unit = self.caster.level.get_unit_at(point.x, point.y)
                if unit is None:
                    continue

                if not are_hostile(self.caster, unit):
                    continue

                unit.deal_damage(self.get_stat("damage"), Tags.Pure, self)
                unit.deal_damage(self.get_stat("damage"), Tags.Arcane, self)

                if unit.killed:
                    self.spawn_clouds()
                    yield

class ManaShredder(Spell):
    def on_init(self):
        self.name = "Mana Shredder"
        self.level = 3
        self.tags = [Tags.Pure, Tags.Arcane, Tags.Conjuration]

        self.max_charges = 8

        self.minion_health = 10
        self.shields = 2
        self.minion_damage = 8

        self.minion_duration = 14
        self.minion_range = 6

        self.must_target_empty = True

    def get_description(self):
        return "summon"

    def cast_instant(self, x, y):
        shredder = Unit()
        shredder.name = "Mana Shredder"
        shredder.tags = [Tags.Pure, Tags.Arcane]

        shredder.sprite.char = 's'
        shredder.sprite.color = Tags.Pure.color
        shredder.asset = ["Cradle", "assets", "tilehazards", "frozen_mana"]

        shredder.max_hp = self.get_stat("minion_health")
        shredder.shields = self.get_stat("shields")

        shredder.resists[Tags.Pure] = 100
        shredder.resists[Tags.Arcane] = 75

        shredder.stationary = True

        shred = Shred()
        shred.damage = self.get_stat("minion_damage")
        shred.radius = self.get_stat("minion_range")
        shred.range = self.get_stat("minion_range")
        shred.duration = 5
        shred.cloud_count = 10
        shredder.spells.append(shred)

        shredder.turns_to_death = self.get_stat("minion_duration")

        self.summon(shredder, Point(x, y))

class SoulFormation(Spell):
    def on_init(self):
        self.name = "Soul Formation"
        self.level = 5
        self.tags = [Tags.Pure, Tags.Dark, Tags.Conjuration]
        
        self.max_charges = 4
        self.range = 12
        self.radius = 3
        self.minion_duration = 6

        self.upgrades['radius'] = (1, 2)
        self.upgrades['minion_duration'] = (4, 3)
        self.upgrades['instability'] = (1, 5, "Instability", "Summon random variations of ghosts.")

        self.ghost_types = [
            (Ghost, 1),
            (GhostMass, 0.12),
            (GhostKing, 0.12),
            (GhostFire, 0.3),
            (Bloodghast, 0.3)
        ]
        # For the asset, draw a ghost rising from a mana cloud

    def get_description(self):
        return "Desc"
    
    def cast_instant(self, x, y):
        for point in self.get_impacted_tiles(x, y):
            tile = self.caster.level.tiles[point.x][point.y]
            if tile.cloud is None:
                continue

            if not isinstance(tile.cloud, PureCloud):
                continue

            tile.cloud.kill()

            ghost = Ghost()

            if self.get_stat("instability"):
                ghost = random.choices([g[0] for g in self.ghost_types], weights=[g[1] for g in self.ghost_types])[0]()

            ghost.turns_to_death = 6
            apply_minion_bonuses(self, ghost)
            self.summon(ghost, point)

class HelixBeam(Spell):
    def on_init(self):
        self.name = "Helix Beam"
        self.level = 1
        self.tags = [Tags.Pure, Tags.Sorcery]

        self.range = 12
        self.damage = 16

        self.requires_los = True
    
    def get_description(self):
        return "Desc"

    def get_point_sets(self, x, y):
        line = self.caster.level.get_points_in_line(Point(self.caster.x, self.caster.y), Point(x, y))
        helix = []
        dx = x - self.caster.x
        dy = y - self.caster.y
        for point in line:
            distance = math.sqrt((point.x - self.caster.x)**2 + (point.y - self.caster.y)**2)
            perp_distance = (math.sin(distance * 0.5) + 1) * 0.7
            point_1 = get_perp_point_slope(point, dx, dy, perp_distance, 1)
            point_2 = get_perp_point_slope(point, dx, dy, perp_distance, -1)
            helix.append((point_1, point_2))
        
        return helix

    def get_impacted_tiles(self, x, y):
        return [point for point_set in self.get_point_sets(x, y) for point in point_set]

    def cast(self, x, y):
        point_sets = self.get_point_sets(x, y)
        for point_set in point_sets:
            if self.caster.level.is_point_in_bounds(point_set[0]):
                self.caster.level.deal_damage(point_set[0].x, point_set[0].y, self.get_stat("damage"), Tags.Pure, self)
            if self.caster.level.is_point_in_bounds(point_set[1]):
                self.caster.level.deal_damage(point_set[1].x, point_set[1].y, self.get_stat("damage"), Tags.Pure, self)
            
            yield

all_player_spell_constructors.append(HollowDomainSpell)
all_player_spell_constructors.append(SoulCloakSpell)
all_player_spell_constructors.append(EmptyPalmSpell)
all_player_spell_constructors.append(WordOfEmptiness)
all_player_spell_constructors.append(ManaShredder)
all_player_spell_constructors.append(SoulFormation)
all_player_spell_constructors.append(HelixBeam)