from Level import Cloud, Color, Tags, Buff, are_hostile
from CommonContent import SimpleMeleeAttack

from Level import BUFF_TYPE_CURSE, STACK_NONE
from Monsters import MordredCorruption

pure_desc = "Purified units cannot use abilities unless they deal physical damage."
mana_cloud_desc = ("Mana clouds apply [purified] to units each turn. Purified "
                    "units cannot use abilities unless they deal physical damage.")

def pure_unaffected(spell):
    if hasattr(spell, 'damage_type') and spell.damage_type == Tags.Physical:
        return True
    
    if isinstance(spell, MordredCorruption):
        return True
    
    return False

def deny_cooldowns(unit):
    for spell in unit.spells:
        if pure_unaffected(spell):
            return

        current_cooldown = unit.cool_downs.get(spell, 0)
        unit.cool_downs[spell] = max(2, current_cooldown)

class PureCloud(Cloud):
    def __init__(self, owner, duration, healing = 0):
        Cloud.__init__(self)

        self.duration = duration
        self.owner = owner
        self.healing = healing

        self.asset_name = "../../../mods/Cradle/assets/clouds/mana_cloud"

        self.color = Color(180, 220, 255)
        self.name = "Mana Cloud"
        self.description = ("Each turn, any unit standing inside is purified.\n"
                            + pure_desc)

    def on_advance(self):
        unit = self.level.get_unit_at(self.x, self.y)

        if unit is None:
            return

        if unit == self.owner:
            return

        if self.healing > 0 and not are_hostile(unit, self.owner):
            unit.deal_damage(-self.healing, Tags.Heal, self)
            self.kill()
        else:
            unit.apply_buff(PureBuff(), 2)

class PureBuff(Buff):
    def __init__(self):
        Buff.__init__(self)

        self.name = "Purified"
        self.description = "Overwhelmed by pure mana. Cannot use abilities."

        self.buff_type = BUFF_TYPE_CURSE
        self.stack_type = STACK_NONE

    def on_applied(self, owner):
        deny_cooldowns(owner)

    def on_advance(self):
        deny_cooldowns(self.owner)