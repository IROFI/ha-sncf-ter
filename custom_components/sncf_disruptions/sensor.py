"""Capteur de perturbations SNCF pour Home Assistant."""
from datetime import datetime, timedelta
import logging
import requests
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

CONF_TOKEN = "token"
CONF_STATION1_ID = "station1_id"
CONF_STATION1_NAME = "station1_name"
CONF_STATION2_ID = "station2_id"
CONF_STATION2_NAME = "station2_name"

DEFAULT_NAME = "SNCF Disruptions"
ATTRIBUTION = "Données fournies par Navitia"

# États possibles de la ligne
LINE_STATUS = {
    "normal": "Trafic normal",
    "delayed": "Retards",
    "disrupted": "Perturbé",
    "critical": "Fortement perturbé"
}

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TOKEN): cv.string,
    vol.Required(CONF_STATION1_ID): cv.string,
    vol.Required(CONF_STATION1_NAME): cv.string,
    vol.Required(CONF_STATION2_ID): cv.string,
    vol.Required(CONF_STATION2_NAME): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Configuration du capteur."""
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    station1_id = config.get(CONF_STATION1_ID)
    station1_name = config.get(CONF_STATION1_NAME)
    station2_id = config.get(CONF_STATION2_ID)
    station2_name = config.get(CONF_STATION2_NAME)

    add_entities([SNCFDisruptionsSensor(
        name, token, station1_id, station1_name, station2_id, station2_name
    )], True)

class SNCFDisruptionsSensor(Entity):
    """Représentation du capteur de perturbations SNCF."""

    def __init__(self, name, token, station1_id, station1_name, station2_id, station2_name):
        self._name = name
        self._token = token
        self._station1 = {"id": station1_id, "name": station1_name}
        self._station2 = {"id": station2_id, "name": station2_name}
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    def calculate_delay(self, base_time, realtime):
        """Calcule le retard en minutes."""
        base = datetime.strptime(base_time, "%Y%m%dT%H%M%S")
        real = datetime.strptime(realtime, "%Y%m%dT%H%M%S")
        return int((real - base).total_seconds() / 60)

    def format_time(self, time_str: str) -> str:
        dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        return dt.strftime("%H:%M")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Mise à jour des données du capteur."""
        try:
            journeys_data = self._get_journeys_data(datetime.now())
            
            if not journeys_data or 'journeys' not in journeys_data:
                self._state = "Indisponible"
                return

            trains = []
            delayed_count = 0
            cancelled_count = 0

            for journey in journeys_data['journeys']:
                for section in journey['sections']:
                    if section.get('type') == 'public_transport':
                        train_info = {
                            'depart': self.format_time(section['departure_date_time']),
                            'arrivee': self.format_time(section['arrival_date_time'])
                        }

                        # Vérification du statut
                        if journey.get('status') == 'NO_SERVICE':
                            train_info['status'] = 'Supprimé'
                            cancelled_count += 1
                        elif 'stop_date_times' in section:
                            for stop in section['stop_date_times']:
                                if stop.get('departure_time') and stop.get('base_departure_time'):
                                    delay = self.calculate_delay(
                                        stop['base_departure_time'],
                                        stop['departure_time']
                                    )
                                    if delay > 0:
                                        train_info['status'] = f"Retard de {delay} min"
                                        delayed_count += 1
                                        break
                            else:
                                train_info['status'] = "À l'heure"
                        
                        trains.append(train_info)

            # Détermination de l'état de la ligne
            if cancelled_count > 2:
                self._state = LINE_STATUS["critical"]
            elif cancelled_count > 0 or delayed_count > 2:
                self._state = LINE_STATUS["disrupted"]
            elif delayed_count > 0:
                self._state = LINE_STATUS["delayed"]
            else:
                self._state = LINE_STATUS["normal"]

            self._attributes = {
                'trains': trains,
                'trains_supprimes': cancelled_count,
                'trains_retardes': delayed_count,
                'derniere_maj': datetime.now().strftime("%H:%M"),
                ATTR_ATTRIBUTION: ATTRIBUTION
            }

        except Exception as error:
            _LOGGER.error("Erreur lors de la mise à jour: %s", error)
            self._state = "Erreur"
            self._attributes = {"error": str(error)}

    def _get_journeys_data(self, from_datetime):
        """Récupère les données des trajets."""
        base_url = "https://api.navitia.io/v1/coverage/sncf/journeys"
        headers = {'Authorization': self._token}
        
        params = {
            'from': self._station1['id'],
            'to': self._station2['id'],
            'datetime': from_datetime.strftime("%Y%m%dT%H%M%S"),
            'data_freshness': 'realtime',
            'count': 10
        }

        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()