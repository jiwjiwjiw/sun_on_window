from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    async_add_entities([HorizonProfileConfigButton(hass, config_entry)])

class HorizonProfileConfigButton(ButtonEntity):
    """Bouton pour configurer le profil d'horizon."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self.hass = hass
        self._attr_name = "Configurer le profil d'horizon"
        self._attr_unique_id = f"{config_entry.entry_id}_config_horizon"
        self._config_entry = config_entry

    async def async_press(self) -> None:
        """Action du bouton : ouvrir le flow d'options sur le profil d'horizon."""
        await self.hass.config_entries.flow.async_init(
            self._config_entry.entry_id,
            context={"source": "options"},
        )
