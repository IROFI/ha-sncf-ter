import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Dict, Optional
import argparse

load_dotenv()

def format_time(time_str: str) -> str:
    """Convertit le format de temps Navitia en format lisible"""
    dt = datetime.strptime(time_str, "%Y%m%dT%H%M%S")
    return dt.strftime("%H:%M")

def check_train_direction(from_station: Dict, to_station: Dict) -> None:
    """Vérifie les trains dans une direction donnée"""
    print(f"\n🚂 Trajets de {from_station['name']} → {to_station['name']}")
    print("=" * 80)
    
    token = os.getenv('TOKEN_NAVITIA')
    if not token:
        raise ValueError("TOKEN_NAVITIA n'est pas défini dans le fichier .env")

    base_url = "https://api.navitia.io/v1/coverage/sncf/journeys"
    headers = {'Authorization': token}
    
    params = {
        'from': from_station['id'],
        'to': to_station['id'],
        'datetime': datetime.now().strftime("%Y%m%dT%H%M%S"),
        'data_freshness': 'realtime'
    }

    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if 'journeys' not in data or not data['journeys']:
            print("Aucun trajet trouvé pour cette période.")
            return

        for journey in data['journeys']:
            disruption_msg = []
            
            if journey.get('status'):
                if journey['status'] == 'NO_SERVICE':
                    disruption_msg.append("🚫 TRAIN SUPPRIMÉ")
                elif journey['status'] == 'SIGNIFICANT_DELAYS':
                    disruption_msg.append("⚠️ RETARD IMPORTANT")

            for section in journey['sections']:
                if section.get('type') == 'public_transport':
                    depart = format_time(section['departure_date_time'])
                    arrivee = format_time(section['arrival_date_time'])
                    
                    if 'display_informations' in section:
                        info = section['display_informations']
                        if info.get('message'):
                            disruption_msg.append(f"ℹ️ {info['message']}")
                    
                    print(f"Départ: {depart} - Arrivée: {arrivee}")
                    if disruption_msg:
                        for msg in disruption_msg:
                            print(msg)
                    print("-" * 80)

    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête: {e}")

def check_both_directions(station1_id: str, station1_name: str, station2_id: str, station2_name: str):
    """Vérifie les trains dans les deux sens entre deux stations"""
    stations = {
        'station1': {
            'id': station1_id,
            'name': station1_name
        },
        'station2': {
            'id': station2_id,
            'name': station2_name
        }
    }

    print("\n📍 VÉRIFICATION DES HORAIRES ET PERTURBATIONS")
    print("=" * 80)
    
    check_train_direction(stations['station1'], stations['station2'])
    check_train_direction(stations['station2'], stations['station1'])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Vérifier les horaires des trains entre deux stations')
    parser.add_argument('--station1-id', required=True, help='ID de la première station')
    parser.add_argument('--station1-name', required=True, help='Nom de la première station')
    parser.add_argument('--station2-id', required=True, help='ID de la deuxième station')
    parser.add_argument('--station2-name', required=True, help='Nom de la deuxième station')
    
    args = parser.parse_args()
    
    check_both_directions(
        args.station1_id,
        args.station1_name,
        args.station2_id,
        args.station2_name
    )