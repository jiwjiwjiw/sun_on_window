"""Constants for the Sun on Window component."""
from datetime import timedelta

DOMAIN = "sun_on_window"

# Configuration pour le profil d'horizon global
CONF_HORIZON_PROFILE = "horizon_profile"
CONF_AZIMUTH = "azimuth"
CONF_ELEVATION = "elevation"

# Configuration pour chaque fenêtre
CONF_WINDOWS = "windows"
CONF_START_AZIMUTH = "start_azimuth"
CONF_END_AZIMUTH = "end_azimuth"
CONF_MAX_ELEVATION = "max_elevation"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

# Messages d'erreur
ERROR_MIN_HORIZON_POINTS = "minimum_horizon_points"
ERROR_NO_WINDOWS = "no_windows"
