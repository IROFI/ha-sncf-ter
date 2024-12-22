"""Capteur de perturbations SNCF pour Home Assistant."""
from datetime import datetime, timedelta
import logging
import requests
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import Throttle

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_STATION1_ID,
    CONF_STATION1_NAME,
    CONF_STATION2_ID,
    CONF_STATION2_NAME,
    DEFAULT_NAME,
    ATTRIBUTION,
)

_LOGGER = logging.getLogger(__name__)

# États possibles de la ligne
LINE_STATUS = {
    "normal": "Trafic normal",
    "delayed": "Retards",
    "disrupted": "Perturbé",
    "critical": "Fortement perturbé"
}

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SNCF Disruptions sensor based on a config entry."""
    async_add_entities(
        [
            SNCFDisruptionsSensor(
                entry.entry_id,
                entry.data[CONF_NAME],
                entry.data[CONF_TOKEN],
                entry.data[CONF_STATION1_ID],
                entry.data[CONF_STATION1_NAME],
                entry.data[CONF_STATION2_ID],
                entry.data[CONF_STATION2_NAME],
            )
        ],
        True,
    )

class SNCFDisruptionsSensor(SensorEntity):
    """Représentation du capteur de perturbations SNCF."""

    def __init__(
        self,
        entry_id: str,
        name: str,
        token: str,
        station1_id: str,
        station1_name: str,
        station2_id: str,
        station2_name: str,
    ) -> None:
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._attr_name = name
        self._token = token
        self._station1 = {"id": station1_id, "name": station1_name}
        self._station2 = {"id": station2_id, "name": station2_name}
        self._attr_unique_id = f"{entry_id}_{station1_id}_{station2_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=f"SNCF {station1_name}-{station2_name}",
            manufacturer="SNCF",
            model="Train Service",
            sw_version="1.0.0",
        )
        self._state = None
        self._attributes = {}
        self._attr_icon = "mdi:train"
        self._attr_entity_category = None

    @property
    def name(self):
        return self._attr_name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    @property
    def icon(self) -> str:
        """Icône de l'entité basée sur son état."""
        if self._state == LINE_STATUS["normal"]:
            return "mdi:train"
        elif self._state == LINE_STATUS["delayed"]:
            return "mdi:train-clock"
        elif self._state == LINE_STATUS["disrupted"]:
            return "mdi:train-variant-alert"
        elif self._state == LINE_STATUS["critical"]:
            return "mdi:train-variant-alert"
        elif self._state == "Erreur":
            return "mdi:alert-circle"
        elif self._state == "Indisponible":
            return "mdi:cloud-off-outline"
        return self._attr_icon

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