from Spells import InfernoCloud, Spell, all_player_spell_constructors
from Level import Tags, Burst, Point, Buff, are_hostile, EventOnDamaged
from CommonContent import BlizzardCloud, FireCloud, Poison, SimpleMeleeAttack, StormCloud, apply_minion_bonuses
from Monsters import Ghost

from Level import BUFF_TYPE_BLESS, STACK_NONE

from mods.Cradle.Pure import PureCloud, PureBuff, pure_desc, mana_cloud_desc

class HollowDomainSpell(Spell):
    def __init__(self):
        self.overload_damage = 4
        Spell.__init__(self)

    def on_init(self):
        self.name = "Hollow Domain"
        self.level = 1
        #3
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
        self.caster.xp += 10
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
            
all_player_spell_constructors.append(HollowDomainSpell)
all_player_spell_constructors.append(SoulCloakSpell)
all_player_spell_constructors.append(EmptyPalmSpell)