from mods.API_TileHazards.API_TileHazards import TileHazardBasic
from Level import Tags

class FrozenManaHazard(TileHazardBasic):
    def __init__(self, user, source, duration, damage):
        TileHazardBasic.__init__(self, "Frozen Mana", duration, user)
        self.damage = damage
        self.source = source
        self.asset = ["Cradle", "assets", "tilehazards", "frozen_mana"]

    def effect(self, unit):
        pass

    def advance_effect(self):
        unit = self.user.level.get_unit_at(self.x, self.y)
        if unit is not None:
            self.user.level.deal_damage(self.x, self.y, self.damage, Tags.Ice, self.source)
            self.user.level.deal_damage(self.x, self.y, self.damage, Tags.Pure, self.source)