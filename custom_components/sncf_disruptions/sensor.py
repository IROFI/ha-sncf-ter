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

# Configuration des constantes
CONF_TOKEN = "token"
CONF_STATION1_ID = "station1_id"
CONF_STATION1_NAME = "station1_name"
CONF_STATION2_ID = "station2_id"
CONF_STATION2_NAME = "station2_name"

DEFAULT_NAME = "SNCF Disruptions"
ATTRIBUTION = "Données fournies par Navitia"

# Mise à jour toutes les 5 minutes
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

# Schéma de configuration
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
        """Initialisation du capteur."""
        self._name = name
        self._token = token
        self._station1 = {"id": station1_id, "name": station1_name}
        self._station2 = {"id": station2_id, "name": station2_name}
        self._state = None
        self._attributes = {}

    @property
    def name(self):
        """Retourne le nom du capteur."""
        return self._name

    @property
    def state(self):
        """Retourne l'état du capteur."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Retourne les attributs du capteur."""
        return self._attributes

    def format_time(self, time_str: str) -> str:
        """Convertit le format de temps Navitia."""
        dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
        return dt.strftime("%H:%M")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Mise à jour des données du capteur."""
        try:
            journeys_data = self._get_journeys_data()
            self._process_journeys_data(journeys_data)
        except Exception as error:
            _LOGGER.error("Erreur lors de la mise à jour: %s", error)
            self._state = "error"
            self._attributes = {"error": str(error)}

    def _get_journeys_data(self):
        """Récupère les données des trajets."""
        base_url = "https://api.navitia.io/v1/coverage/sncf/journeys"
        headers = {'Authorization': self._token}
        
        params = {
            'from': self._station1['id'],
            'to': self._station2['id'],
            'datetime': datetime.now().strftime("%Y%m%dT%H%M%S"),
            'data_freshness': 'realtime'
        }

        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _process_journeys_data(self, data):
        """Traite les données des trajets."""
        disruptions = []
        next_departures = []

        if 'journeys' in data and data['journeys']:
            for journey in data['journeys']:
                journey_info = {}
                
                for section in journey['sections']:
                    if section.get('type') == 'public_transport':
                        depart = self.format_time(section['departure_date_time'])
                        arrivee = self.format_time(section['arrival_date_time'])
                        
                        journey_info = {
                            'depart': depart,
                            'arrivee': arrivee,
                            'status': journey.get('status', 'normal')
                        }

                        if journey.get('status'):
                            if journey['status'] == 'NO_SERVICE':
                                journey_info['disruption'] = "TRAIN SUPPRIMÉ"
                            elif journey['status'] == 'SIGNIFICANT_DELAYS':
                                journey_info['disruption'] = "RETARD IMPORTANT"

                        if 'display_informations' in section:
                            info = section['display_informations']
                            if info.get('message'):
                                journey_info['message'] = info['message']

                if journey_info:
                    next_departures.append(journey_info)
                    if 'disruption' in journey_info:
                        disruptions.append(journey_info)

        # Mise à jour de l'état et des attributs
        self._state = len(disruptions)
        self._attributes = {
            'disruptions': disruptions,
            'next_departures': next_departures[:5],  # Limite aux 5 prochains départs
            'last_update': datetime.now().strftime("%H:%M:%S"),
            ATTR_ATTRIBUTION: ATTRIBUTION
        } 