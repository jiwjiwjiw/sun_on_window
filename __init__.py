"""The Sun on Window integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_SCAN_INTERVAL
from datetime import timedelta
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_HORIZON_PROFILE, CONF_WINDOWS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "button"]


async def async_setup(hass: HomeAssistant, config):
    """Set up this integration using YAML."""
    # Cette fonction est appelée si le composant est configuré via configuration.yaml
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    # Convertir les données de configuration en structures appropriées
    config = dict(entry.data)
    
    # Stocker la configuration dans le hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = config
    
    # Configurer les plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Enregistrer les fonctions de mise à jour et de suppression
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # Décharger les plateformes
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    
    # Supprimer les données de configuration
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok
