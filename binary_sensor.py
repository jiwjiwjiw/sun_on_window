"""Capteur binaire pour déterminer quand le soleil tape sur une fenêtre."""
import logging
import math
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_HORIZON_PROFILE,
    CONF_WINDOWS,
    CONF_AZIMUTH,
    CONF_ELEVATION,
    CONF_START_AZIMUTH, 
    CONF_END_AZIMUTH,
    CONF_MAX_ELEVATION,
    CONF_NAME,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor(s) from a config entry."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    
    horizon_profile = config[CONF_HORIZON_PROFILE]
    windows = config[CONF_WINDOWS]
        
    entities = []
    for window_conf in windows:
        entities.append(
            SunOnWindowSensor(
                window_conf[CONF_NAME],
                horizon_profile,
                window_conf[CONF_START_AZIMUTH],
                window_conf[CONF_END_AZIMUTH],
                window_conf[CONF_MAX_ELEVATION],
                config_entry.entry_id,
            )
        )
    
    async_add_entities(entities, True)


# Le support YAML est maintenu pour la rétrocompatibilité
async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor from YAML configuration."""
    horizon_profile = config[CONF_HORIZON_PROFILE]
    windows = config[CONF_WINDOWS]
    
    entities = []
    for window_conf in windows:
        entities.append(
            SunOnWindowSensor(
                window_conf[CONF_NAME],
                horizon_profile,
                window_conf[CONF_START_AZIMUTH],
                window_conf[CONF_END_AZIMUTH],
                window_conf[CONF_MAX_ELEVATION],
                None,  # Pas d'ID d'entrée de configuration pour YAML
            )
        )
    
    async_add_entities(entities, True)


class SunOnWindowSensor(BinarySensorEntity):
    """Capteur pour déterminer si le soleil tape sur une fenêtre."""
    
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.LIGHT

    def __init__(
        self,
        name,
        horizon_profile,
        start_azimuth,
        end_azimuth,
        max_elevation,
        config_entry_id,
    ):
        """Initialiser le capteur."""
        self._name = name
        self._horizon_profile = horizon_profile
        self._start_azimuth = start_azimuth
        self._end_azimuth = end_azimuth
        self._max_elevation = max_elevation
        self._config_entry_id = config_entry_id
        self._attr_is_on = None
        self._unsub_update = None
        self._attr_extra_state_attributes = {
            "start_azimuth": start_azimuth,
            "end_azimuth": end_azimuth,
            "max_elevation": max_elevation,
            "horizon_profile": horizon_profile,
        }
        
        # Identifiants uniques pour l'entité
        if config_entry_id:
            self._attr_unique_id = f"{config_entry_id}_{name}"
        else:
            # Pour les configurations YAML
            self._attr_unique_id = f"sun_on_window_{name}"

    @property
    def name(self):
        """Retourne le nom du capteur."""
        return f"Soleil sur {self._name}"

    async def async_added_to_hass(self):
        """Appelé lorsque l'entité est ajoutée à Home Assistant."""
        # S'abonner aux changements d'état de l'entité sun.sun
        self.async_on_remove(
            async_track_state_change_event(self.hass, "sun.sun", self._handle_sun_update_event)
        )
        # Effectuer une mise à jour initiale
        await self._update_sun_position()

    async def _handle_sun_update_event(self, event):
        """Gérer les mises à jour de l'entité sun.sun."""
        new_state = event.data.get("new_state")
        if new_state is not None:
            await self._update_sun_position()

    async def async_will_remove_from_hass(self):
        """Appelé lorsque l'entité est supprimée de Home Assistant."""
        if self._unsub_update is not None:
            self._unsub_update()

    async def _update_sun_position(self, now=None):
        """Met à jour la position du soleil et détermine si le soleil tape sur la fenêtre."""
        # Récupération des informations sur le soleil depuis Home Assistant
        sun_data = self.hass.states.get("sun.sun")
        if sun_data is None:
            _LOGGER.error("Impossible de récupérer les données du soleil")
            return

        # Extraction de l'azimut et de l'élévation actuels du soleil
        azimuth = float(sun_data.attributes.get("azimuth", 0))
        elevation = float(sun_data.attributes.get("elevation", 0))

        # Mise à jour des attributs avec les valeurs actuelles
        self._attr_extra_state_attributes.update({
            "current_azimuth": azimuth,
            "current_elevation": elevation,
        })

        # Vérifier si le soleil est au-dessus de l'horizon
        if elevation <= 0:
            self._attr_is_on = False
            self._attr_extra_state_attributes["sun_position"] = "below_horizon"
        else:
            # Vérifier si l'azimut du soleil est dans la plage de la fenêtre
            in_azimuth_range = False
            
            # Gestion du cas où la plage traverse 0°/360°
            if self._start_azimuth > self._end_azimuth:
                in_azimuth_range = azimuth >= self._start_azimuth or azimuth <= self._end_azimuth
            else:
                in_azimuth_range = self._start_azimuth <= azimuth <= self._end_azimuth
            
            # Vérifier si l'élévation est inférieure à l'élévation maximale pour la fenêtre
            below_max_elevation = elevation < self._max_elevation
            
            # Vérifier si le soleil est au-dessus du profil d'horizon à cet azimut
            above_horizon = True
            horizon_elevation = self._get_horizon_elevation(azimuth)
            if horizon_elevation is not None:
                above_horizon = elevation > horizon_elevation
                self._attr_extra_state_attributes["horizon_elevation_at_current_azimuth"] = horizon_elevation
            
            # Déterminer l'état final
            self._attr_is_on = in_azimuth_range and below_max_elevation and above_horizon
            
            # Mise à jour des attributs avec les raisons
            self._attr_extra_state_attributes.update({
                "in_azimuth_range": in_azimuth_range,
                "below_max_elevation": below_max_elevation,
                "above_horizon": above_horizon,
                "sun_position": "hitting_window" if self._attr_is_on else "not_hitting_window",
            })

        # Notifier Home Assistant de la mise à jour de l'état
        self.async_write_ha_state()

    def _get_horizon_elevation(self, current_azimuth):
        """
        Calcule l'élévation du profil d'horizon à un azimut donné par interpolation linéaire.
        Retourne None si le profil d'horizon n'est pas défini ou ne contient pas assez de points.
        """
        if not self._horizon_profile or len(self._horizon_profile) < 2:
            return None
        
        # Trier le profil d'horizon par azimut
        sorted_profile = sorted(self._horizon_profile, key=lambda x: x[CONF_AZIMUTH])
        
        # Trouver les points d'horizon qui encadrent l'azimut actuel
        for i in range(len(sorted_profile)):
            if sorted_profile[i][CONF_AZIMUTH] > current_azimuth:
                if i == 0:
                    # Cas particulier: l'azimut est avant le premier point
                    # On considère le dernier et le premier point pour l'interpolation
                    point1 = sorted_profile[-1]
                    point1_azimuth = point1[CONF_AZIMUTH] - 360  # Ajuster pour la continuité
                    point2 = sorted_profile[0]
                else:
                    point1 = sorted_profile[i-1]
                    point1_azimuth = point1[CONF_AZIMUTH]
                    point2 = sorted_profile[i]
                
                # Interpolation linéaire
                point2_azimuth = point2[CONF_AZIMUTH]
                elevation1 = point1[CONF_ELEVATION]
                elevation2 = point2[CONF_ELEVATION]
                
                # Calcul de l'élévation interpolée
                if point2_azimuth == point1_azimuth:
                    return elevation1
                
                ratio = (current_azimuth - point1_azimuth) / (point2_azimuth - point1_azimuth)
                return elevation1 + ratio * (elevation2 - elevation1)
        
        # Si nous sommes ici, l'azimut est après le dernier point
        # On considère le dernier et le premier point pour l'interpolation
        point1 = sorted_profile[-1]
        point2 = sorted_profile[0]
        point2_azimuth = point2[CONF_AZIMUTH] + 360  # Ajuster pour la continuité
        
        # Interpolation linéaire
        elevation1 = point1[CONF_ELEVATION]
        elevation2 = point2[CONF_ELEVATION]
        ratio = (current_azimuth - point1[CONF_AZIMUTH]) / (point2_azimuth - point1[CONF_AZIMUTH])
        return elevation1 + ratio * (elevation2 - elevation1)
