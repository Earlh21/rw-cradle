from tkinter import E
from Level import EventOnUnitAdded, are_hostile, Tags, Burst, Point, Spell, Unit
from Level import EventOnDamaged, EventOnBuffApply, EventOnBuffRemove, EventOnSpellCast
from CommonContent import Poison
from Upgrades import Upgrade, skill_constructors

from mods.Cradle.Pure import PureBuff, PureCloud, mana_cloud_desc
from mods.Cradle.Tilehazards import FrozenManaHazard
from mods.Cradle.Util import has_adjacent_chasm

class CleansingFlame(Upgrade):
    def on_init(self):
        self.name = "Cleansing Flame"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Fire]

        self.asset = ["Cradle", "assets", "skills", "cleansing_flame"]

        self.damage = 6
        self.radius = 2

        self.global_triggers[EventOnDamaged] = self.on_damage
    
    def get_description(self):
        return ("[Purified:pure] enemies explode in a [{radius}_tile:radius] burst for [{damage}_fire:fire] damage "
                "upon taking any fire damage.\n"
                "[Purified:pure] is removed from the enemy.").format(**self.fmt_dict())
    
    def on_damage(self, evt):
        if not are_hostile(evt.unit, self.owner):
            return
        
        if evt.damage_type == Tags.Fire and evt.unit.has_buff(PureBuff):
            evt.unit.remove_buffs(PureBuff)
            for stage in Burst(self.owner.level, Point(evt.unit.x, evt.unit.y), self.radius):
                for point in stage:
                    self.owner.level.deal_damage(point.x, point.y, self.get_stat("damage"), Tags.Fire, self)

class SpiritCorruption(Upgrade):
    def on_init(self):
        self.name = "Spirit Corruption"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Nature]

        self.asset = ["Cradle", "assets", "skills", "spirit_corruption"]

        self.damage = 3
    
    def get_description(self):
        return ("Enemies that are both [purified] and [poisoned] take [{damage}_pure:pure] and [{damage}_poison:poison] damage "
                "for each ability they have.").format(**self.fmt_dict())
    
    def on_advance(self):
        for unit in self.owner.level.units:
            if not are_hostile(unit, self.owner):
                continue
            if not (unit.has_buff(PureBuff) and unit.has_buff(Poison)):
                continue

            damage = self.get_stat("damage") * len(unit.spells)
            unit.deal_damage(damage, Tags.Pure, self)
            unit.deal_damage(damage, Tags.Poison, self)

class FrozenMana(Upgrade):
    def on_init(self):
        self.name = "Frozen Mana"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Ice]

        self.asset = ["Cradle", "assets", "skills", "frozen_mana"]

        self.damage = 6
        self.duration = 7

        self.owner_triggers[EventOnSpellCast] = self.on_spell_cast
        self.global_triggers[EventOnDamaged] = self.on_damage
    
    def get_description(self):
        return ("Your [ice] spells leave behind frozen mana spikes when impacting "
                "[purified] units or mana clouds.\n"
                "This effect also occurs wherever an enemy takes [ice] damage.\n"
                "Frozen mana spikes last [{duration}_turns:duration] and deal [{damage}_ice:ice] and [{damage}_pure:pure] damage to units "
                "standing on them each turn.").format(**self.fmt_dict())
    
    def add_frozen_mana(self, x, y):
        mana = FrozenManaHazard(self.owner, self, self.get_stat("duration"), self.get_stat("damage"))
        self.owner.level.add_obj(mana, x, y)

    def handle_ice(self, x, y):
        tile = self.owner.level.tiles[x][y]

        if not tile.is_floor():
            return
        if tile.prop is not None:
            return

        if tile.cloud is not None and isinstance(tile.cloud, PureCloud):
            tile.cloud.kill()
            self.add_frozen_mana(tile.x, tile.y)
            return

        unit = self.owner.level.get_unit_at(tile.x, tile.y)

        if unit is not None and unit.has_buff(PureBuff):
            self.add_frozen_mana(tile.x, tile.y)

    def on_damage(self, evt):
        if evt.damage_type != Tags.Ice:
            return
        if not evt.unit:
            return
        if not are_hostile(self.owner, evt.unit):
            return
        
        self.handle_ice(evt.unit.x, evt.unit.y)

    def on_spell_cast(self, evt):
        if evt.spell is None:
            return
        if not isinstance(evt.spell, Spell):
            return
        if not Tags.Ice in evt.spell.tags:
            return

        points = evt.spell.get_impacted_tiles(evt.x, evt.y)

        for point in points:
            self.handle_ice(point.x, point.y)

class Nihilism(Upgrade):
    def on_init(self):
        self.name = "Nihilism"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Arcane]

        self.asset = ["Cradle", "assets", "skills", "nihilism"]

        self.damage = 3

    def get_description(self):
        return ("[Purified:pure] enemies standing next to a chasm take [{damage}_pure:pure] and [{damage}_arcane:arcane] damage each turn.\n"
                "Enemies flying above a chasm take double this damage.").format(**self.fmt_dict())

    def on_advance(self):
        for unit in self.owner.level.units:
            if not are_hostile(unit, self.owner):
                continue
                
            tile = self.owner.level.tiles[unit.x][unit.y]

            if tile.is_chasm:
                unit.deal_damage(self.get_stat("damage") * 2, Tags.Pure, self)
                unit.deal_damage(self.get_stat("damage") * 2, Tags.Arcane, self)
            elif has_adjacent_chasm(self.owner.level, unit.x, unit.y):
                unit.deal_damage(self.get_stat("damage"), Tags.Pure, self)
                unit.deal_damage(self.get_stat("damage"), Tags.Arcane, self)

class Ozone(Upgrade):
    def on_init(self):
        self.name = "Ozone"
        self.level = 4
        self.tags = [Tags.Pure, Tags.Lightning]

        self.asset = ["Cradle", "assets", "skills", "ozone"]

        self.global_triggers[EventOnDamaged] = self.on_damage

        self.radius = 1
        self.duration = 2
    
    def get_description(self):
        return ("Whenever an enemy takes [lightning] damage, clouds of pure mana are spawned in a "
                "[{radius}_tile:radius] burst around the enemy.\n"
                "Clouds last [{duration}_turns:duration].\n"
                + mana_cloud_desc).format(**self.fmt_dict())
    
    def on_damage(self, evt):
        if evt.damage_type != Tags.Lightning:
            return
        if not evt.unit:
            return
        if not are_hostile(self.owner, evt.unit):
            return

        for stage in Burst(self.owner.level, Point(evt.unit.x, evt.unit.y), self.get_stat("radius")):
            for point in stage:
                tile = self.owner.level.tiles[point.x][point.y]
                if tile.cloud is not None:
                    continue

                cloud = PureCloud(self.owner, self.get_stat("duration"), healing = False)
                self.owner.level.add_obj(cloud, point.x, point.y)

class PermeatingLight(Upgrade):
    def on_init(self):
        self.name = "Permeating Light"
        self.level = 4
        self.tags = [Tags.Holy, Tags.Pure]

        self.asset = ["Cradle", "assets", "skills", "permeating_light"]

        self.damage = 8
    
    def get_description(self):
        return ("Your [holy] minions deal [{damage}_holy:holy] damage to [purified] enemies "
                "within their line of sight each turn.\n").format(**self.fmt_dict())
    
    def on_advance(self):
        for unit in self.owner.level.units:
            if are_hostile(self.owner, unit):
                continue

            if Tags.Holy not in unit.tags:
                continue

            for enemy in self.owner.level.get_units_in_los(unit):
                if not are_hostile(self.owner, enemy):
                    continue
                    
                if not enemy.has_buff(PureBuff):
                    continue
                
                enemy.deal_damage(self.get_stat("damage"), Tags.Holy, self)

class Mindlessness(Upgrade):
    def on_init(self):
        self.name = "Mindlessness"
        self.level = 4
        self.tags = [Tags.Dark, Tags.Pure]

        self.asset = ["Cradle", "assets", "skills", "mindlessness"]

        self.damage = 5

        self.global_triggers[EventOnUnitAdded] = self.on_unit_added
        self.global_triggers[EventOnBuffApply] = self.on_buff_apply
        self.global_triggers[EventOnBuffRemove] = self.on_buff_remove
        self.units = []

    def get_description(self):
        return ("Your summoned [undead] units gain [100_pure:pure] resist.\n"
                "They also gain a {damage} damage bonus to [physical] attacks while [purified].").format(**self.fmt_dict())
    
    def applicable(self, unit):
        if are_hostile(self.owner, unit):
            return False
        
        if Tags.Undead not in unit.tags:
            return False

        if not unit.has_buff(PureBuff):
            return False
    
        return True

    def add_unit(self, unit):
        self.units.append(unit)
        
        for spell in unit.spells:
            if not hasattr(spell, "damage_type") or spell.damage_type != Tags.Physical:
                continue
            if not hasattr(spell, "damage"):
                continue
            
            spell.damage += self.damage

    def remove_unit(self, unit):
        self.units.remove(unit)
        
        for spell in unit.spells:
            if not hasattr(spell, "damage_type") or spell.damage_type != Tags.Physical:
                continue
            if not hasattr(spell, "damage"):
                continue
            
            spell.damage -= self.damage

    def update_unit(self, unit):
        if unit in self.units and not self.applicable(unit):
            self.remove_unit(unit)
        if unit not in self.units and self.applicable(unit):
            self.add_unit(unit)

    def on_buff_apply(self, evt):
        if evt.unit is not None:
            self.update_unit(evt.unit)

    def on_buff_remove(self, evt):
        if evt.unit is not None:
            self.update_unit(evt.unit)

    def on_advance(self):
        for unit in self.owner.level.units:
            self.update_unit(unit)

    def on_unit_added(self, evt):
        if are_hostile(self.owner, evt.unit):
            return

        if Tags.Undead not in evt.unit.tags:
            return

        evt.unit.resists[Tags.Pure] += 100

class ManaPrism(Upgrade):
    def on_init(self):
        self.name = "Mana Prism"
        self.level = 4
        self.tags = [Tags.Pure]

        self.damage = 6
        self.radius = 2

        self.global_triggers[EventOnDamaged] = self.on_damage
    
    def get_description(self):
        return ("Deals 1 [fire], [lightning], [ice], [holy], [dark], and [arcane] damage when an enemy takes [pure] damage."
                ).format(**self.fmt_dict())
    
    def on_damage(self, evt):
        if evt.source is None:
            return
        if not hasattr(evt.source, "owner"):
            return
        if not evt.source.owner == self.owner:
            return
        if not evt.damage_type == Tags.Pure:
            return
        if evt.unit is None:
            return
        
        for damage_type in [Tags.Fire, Tags.Lightning, Tags.Ice, Tags.Holy, Tags.Dark, Tags.Arcane]:
            if not evt.unit.is_alive():
                break
            self.owner.level.deal_damage(evt.unit.x, evt.unit.y, self.get_stat("damage"), damage_type, self)

skill_constructors.append(CleansingFlame)
skill_constructors.append(SpiritCorruption)
skill_constructors.append(FrozenMana)
skill_constructors.append(Nihilism)
skill_constructors.append(Ozone)
skill_constructors.append(PermeatingLight)
skill_constructors.append(Mindlessness)
skill_constructors.append(ManaPrism)