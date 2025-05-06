"""Config flow pour le composant Sun on Window."""
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

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


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input."""
    # On peut ajouter des validations supplémentaires ici si nécessaire
    return {"title": "Sun on Window"}


class SunOnWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sun on Window."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the config flow."""
        self._horizon_profile = []
        self._windows = []

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Redirect immediately to horizon step."""
        return await self.async_step_horizon()

    async def async_step_horizon(self, user_input=None) -> FlowResult:
        """Handle the horizon profile configuration step."""
        errors = {}

        if user_input is not None:
            # Traitement de l'entrée JSON du profil d'horizon
            if "horizon_profile_json" in user_input and user_input["horizon_profile_json"]:
                try:
                    # Analyser la chaîne JSON
                    import json
                    horizon_data = json.loads(user_input["horizon_profile_json"])
                    
                    # Vérifier que c'est un dictionnaire
                    if not isinstance(horizon_data, dict):
                        errors["horizon_profile_json"] = "invalid_json_format"
                    else:
                        # Convertir le dictionnaire en liste de points
                        self._horizon_profile = []
                        for azimuth_str, elevation in horizon_data.items():
                            try:
                                azimuth = float(azimuth_str)
                                if not (0 <= azimuth <= 360):
                                    errors["horizon_profile_json"] = "invalid_azimuth_range"
                                    break
                                
                                if not isinstance(elevation, (int, float)) or not (-90 <= elevation <= 90):
                                    errors["horizon_profile_json"] = "invalid_elevation_range"
                                    break
                                
                                self._horizon_profile.append({
                                    CONF_AZIMUTH: azimuth,
                                    CONF_ELEVATION: float(elevation),
                                })
                            except ValueError:
                                errors["horizon_profile_json"] = "invalid_number_format"
                                break
                
                except json.JSONDecodeError:
                    errors["horizon_profile_json"] = "invalid_json"

            # Si l'utilisateur veut passer à l'étape suivante
            if not errors:
                if len(self._horizon_profile) < 2:
                    errors["horizon_profile_json"] = "minimum_horizon_points"
                else:
                    return await self.async_step_window()

        # Formater les points d'horizon actuels pour l'affichage
        horizon_points_str = ", ".join(
            f"Azimut: {point[CONF_AZIMUTH]}°, Élévation: {point[CONF_ELEVATION]}°"
            for point in self._horizon_profile
        )
        
        # Convertir les points actuels en format JSON pour l'affichage
        current_json = {}
        for point in self._horizon_profile:
            current_json[str(point[CONF_AZIMUTH])] = point[CONF_ELEVATION]
        
        horizon_json_str = json.dumps(current_json, indent=2) if current_json else ""

        return self.async_show_form(
            step_id="horizon",
            data_schema=vol.Schema({
                vol.Optional("horizon_profile_json", default=horizon_json_str): cv.string,
            }),
            description_placeholders={
                "current_points": horizon_points_str or "Aucun point défini",
                "description": "Définissez le profil d'horizon global au format JSON où les clés sont les azimuts (0-360°) "
                               "et les valeurs sont les élévations (-90° à 90°). "
                               "Exemple: {\"0\": 5, \"90\": 3, \"180\": 10, \"270\": 7}. "
                               "Ajoutez au moins 2 points, puis cochez la case pour passer à l'étape suivante.",
            },
            errors=errors,
        )

    async def async_step_window(self, user_input=None) -> FlowResult:
        """Handle the window configuration step."""
        errors = {}

        if user_input is not None:
            # Si une fenêtre est configurée, l'ajouter à la liste
            if all(k in user_input for k in [CONF_NAME, CONF_START_AZIMUTH, CONF_END_AZIMUTH, CONF_MAX_ELEVATION]):
                name = user_input[CONF_NAME]
                # Vérifier si une fenêtre avec ce nom existe déjà
                for i, window in enumerate(self._windows):
                    if window[CONF_NAME] == name:
                        # Mettre à jour la fenêtre existante
                        self._windows[i] = {
                            CONF_NAME: name,
                            CONF_START_AZIMUTH: user_input[CONF_START_AZIMUTH],
                            CONF_END_AZIMUTH: user_input[CONF_END_AZIMUTH],
                            CONF_MAX_ELEVATION: user_input[CONF_MAX_ELEVATION],
                        }
                        break
                else:
                    # Ajouter une nouvelle fenêtre
                    self._windows.append({
                        CONF_NAME: name,
                        CONF_START_AZIMUTH: user_input[CONF_START_AZIMUTH],
                        CONF_END_AZIMUTH: user_input[CONF_END_AZIMUTH],
                        CONF_MAX_ELEVATION: user_input[CONF_MAX_ELEVATION],
                    })

            # Si l'utilisateur a terminé d'ajouter des fenêtres
            if user_input.get("next_step", False):
                if not self._windows:
                    errors["base"] = "no_windows"
                else:
                    # Créer l'entrée de configuration finale
                    data = {
                        CONF_HORIZON_PROFILE: self._horizon_profile,
                        CONF_WINDOWS: self._windows,
                    }

                    return self.async_create_entry(
                        title="Sun on Window",
                        data=data,
                    )

        # Afficher les fenêtres actuelles et le formulaire pour en ajouter
        windows_str = "\n".join(
            f"- {window[CONF_NAME]}: Azimut {window[CONF_START_AZIMUTH]}° à {window[CONF_END_AZIMUTH]}°, "
            f"Élévation max: {window[CONF_MAX_ELEVATION]}°"
            for window in self._windows
        )

        return self.async_show_form(
            step_id="window",
            data_schema=vol.Schema({
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_START_AZIMUTH): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=360)
                ),
                vol.Optional(CONF_END_AZIMUTH): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=360)
                ),
                vol.Optional(CONF_MAX_ELEVATION): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=90)
                ),
                vol.Optional("next_step", default=False): bool,
            }),
            description_placeholders={
                "current_windows": windows_str or "Aucune fenêtre définie",
                "description": "Définissez les fenêtres à surveiller en spécifiant leur nom, "
                               "la plage d'azimut et l'élévation maximale. "
                               "Ajoutez au moins une fenêtre, puis cochez la case pour passer à l'étape suivante.",
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SunOnWindowOptionsFlow(config_entry)


class SunOnWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the component."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self._horizon_profile = list(config_entry.data.get(CONF_HORIZON_PROFILE, []))
        self._windows = list(config_entry.data.get(CONF_WINDOWS, []))

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options for the custom component."""
        return await self.async_step_menu()

    async def async_step_menu(self, user_input=None) -> FlowResult:
        """Show menu for options flow."""
        if user_input is not None:
            menu_option = user_input.get("menu_option")
            if menu_option == "horizon":
                return await self.async_step_edit_horizon()
            elif menu_option == "windows":
                return await self.async_step_edit_windows()

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema({
                vol.Required("menu_option", default="horizon"): vol.In({
                    "horizon": "Modifier le profil d'horizon",
                    "windows": "Gérer les fenêtres",
                }),
            }),
        )

    async def async_step_edit_horizon(self, user_input=None) -> FlowResult:
        """Edit horizon profile."""
        errors = {}
        import json

        if user_input is not None:
            if "action" in user_input:
                action = user_input["action"]
                
                if action == "edit_json" and "horizon_profile_json" in user_input:
                    # Traiter l'entrée JSON du profil d'horizon
                    try:
                        horizon_data = json.loads(user_input["horizon_profile_json"])
                        
                        if not isinstance(horizon_data, dict):
                            errors["horizon_profile_json"] = "invalid_json_format"
                        else:
                            # Convertir le dictionnaire en liste de points
                            self._horizon_profile = []
                            for azimuth_str, elevation in horizon_data.items():
                                try:
                                    azimuth = float(azimuth_str)
                                    if not (0 <= azimuth <= 360):
                                        errors["horizon_profile_json"] = "invalid_azimuth_range"
                                        break
                                    
                                    if not isinstance(elevation, (int, float)) or not (-90 <= elevation <= 90):
                                        errors["horizon_profile_json"] = "invalid_elevation_range"
                                        break
                                    
                                    self._horizon_profile.append({
                                        CONF_AZIMUTH: azimuth,
                                        CONF_ELEVATION: float(elevation),
                                    })
                                except ValueError:
                                    errors["horizon_profile_json"] = "invalid_number_format"
                                    break
                    
                    except json.JSONDecodeError:
                        errors["horizon_profile_json"] = "invalid_json"
                
                elif action == "save":
                    # Sauvegarder les modifications et revenir au menu
                    if len(self._horizon_profile) < 2:
                        errors["horizon_profile_json"] = "minimum_horizon_points"
                    else:
                        # Mettre à jour l'entrée de configuration
                        new_data = dict(self.config_entry.data)
                        new_data[CONF_HORIZON_PROFILE] = self._horizon_profile
                        self.hass.config_entries.async_update_entry(
                            self.config_entry, data=new_data
                        )
                        return await self.async_step_menu()

        # Convertir les points actuels en format JSON pour l'affichage
        current_json = {}
        for point in self._horizon_profile:
            current_json[str(point[CONF_AZIMUTH])] = point[CONF_ELEVATION]
        
        horizon_json_str = json.dumps(current_json, indent=2) if current_json else ""

        # Préparer les points pour l'affichage
        horizon_points_display = "\n".join(
            f"- Azimut: {point[CONF_AZIMUTH]}°, Élévation: {point[CONF_ELEVATION]}°"
            for point in sorted(self._horizon_profile, key=lambda x: x[CONF_AZIMUTH])
        ) or "Aucun point défini"

        # Afficher le formulaire
        return self.async_show_form(
            step_id="edit_horizon",
            data_schema=vol.Schema({
                vol.Required("action", default="edit_json"): vol.In({
                    "edit_json": "Éditer le profil d'horizon (JSON)",
                    "save": "Enregistrer et revenir au menu",
                }),
                vol.Optional("horizon_profile_json", default=horizon_json_str): str,
            }),
            description_placeholders={
                "current_points": horizon_points_display,
                "description": "Modifiez le profil d'horizon global au format JSON où les clés sont les azimuts (0-360°) "
                               "et les valeurs sont les élévations (-90° à 90°). "
                               "Exemple: {\"0\": 5, \"90\": 3, \"180\": 10, \"270\": 7}.",
            },
            errors=errors,
        )

    async def async_step_edit_windows(self, user_input=None) -> FlowResult:
        """Edit windows."""
        errors = {}

        if user_input is not None:
            if "action" in user_input:
                action = user_input["action"]
                
                if action == "add":
                    # Ajouter ou mettre à jour une fenêtre
                    if all(k in user_input for k in [CONF_NAME, CONF_START_AZIMUTH, CONF_END_AZIMUTH, CONF_MAX_ELEVATION]):
                        name = user_input[CONF_NAME]
                        
                        # Vérifier si une fenêtre avec ce nom existe déjà
                        for i, window in enumerate(self._windows):
                            if window[CONF_NAME] == name:
                                self._windows[i] = {
                                    CONF_NAME: name,
                                    CONF_START_AZIMUTH: user_input[CONF_START_AZIMUTH],
                                    CONF_END_AZIMUTH: user_input[CONF_END_AZIMUTH],
                                    CONF_MAX_ELEVATION: user_input[CONF_MAX_ELEVATION],
                                }
                                break
                        else:
                            self._windows.append({
                                CONF_NAME: name,
                                CONF_START_AZIMUTH: user_input[CONF_START_AZIMUTH],
                                CONF_END_AZIMUTH: user_input[CONF_END_AZIMUTH],
                                CONF_MAX_ELEVATION: user_input[CONF_MAX_ELEVATION],
                            })
                
                elif action == "delete" and "delete_window" in user_input:
                    # Supprimer une fenêtre
                    window_name = user_input["delete_window"]
                    self._windows = [w for w in self._windows if w[CONF_NAME] != window_name]
                
                elif action == "save":
                    # Sauvegarder les modifications et revenir au menu
                    if not self._windows:
                        errors["base"] = "no_windows"
                    else:
                        # Mettre à jour l'entrée de configuration
                        new_data = dict(self.config_entry.data)
                        new_data[CONF_WINDOWS] = self._windows
                        self.hass.config_entries.async_update_entry(
                            self.config_entry, data=new_data
                        )
                        return await self.async_step_menu()

        # Préparer les options de suppression
        delete_options = {
            window[CONF_NAME]: window[CONF_NAME] 
            for window in self._windows
        }

        # Afficher le formulaire
        return self.async_show_form(
            step_id="edit_windows",
            data_schema=vol.Schema({
                vol.Required("action", default="add"): vol.In({
                    "add": "Ajouter/Modifier une fenêtre",
                    "delete": "Supprimer une fenêtre",
                    "save": "Enregistrer et revenir au menu",
                }),
                vol.Optional(CONF_NAME): str,
                vol.Optional(CONF_START_AZIMUTH): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=360)
                ),
                vol.Optional(CONF_END_AZIMUTH): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=360)
                ),
                vol.Optional(CONF_MAX_ELEVATION): vol.All(
                    vol.Coerce(float), vol.Range(min=0, max=90)
                ),
                vol.Optional("delete_window"): vol.In(delete_options if delete_options else {"none": "Aucune fenêtre à supprimer"}),
            }),
            description_placeholders={
                "current_windows": "\n".join(
                    f"- {window[CONF_NAME]}: Azimut {window[CONF_START_AZIMUTH]}° à {window[CONF_END_AZIMUTH]}°, "
                    f"Élévation max: {window[CONF_MAX_ELEVATION]}°"
                    for window in self._windows
                ) or "Aucune fenêtre définie",
            },
            errors=errors,
        )
