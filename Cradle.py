from Level import Tags, Color, Tag

import mods.API_Universal.APIs.API_Spells.API_Spells as APISpells

import inspect 

frm = inspect.stack()[-1]
RiftWizard = inspect.getmodule(frm[0])

Tags.elements.append(Tag("Pure", Color(180, 220, 255), ["Cradle", "assets", "effects", "pure"]))

APISpells.add_tag_keybind(Tags.Pure, "p")
RiftWizard.tooltip_colors['purified'] = Tags.Pure.color
RiftWizard.tooltip_colors['pure'] = Tags.Pure.color

import mods.Cradle.TwinStars
#import mods.Cradle.Blackflame
#import mods.Cradle.EndlessSword
import mods.Cradle.HollowKing
import mods.Cradle.Upgrades