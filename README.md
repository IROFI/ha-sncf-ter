# SNCF Disruptions pour Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40IROFI-blue.svg)](https://github.com/IROFI)
[![fr](https://img.shields.io/badge/lang-fr-yellow.svg)](https://github.com/IROFI/ha-sncf-ter/blob/main/README.md)

Intégration personnalisée pour suivre les perturbations SNCF entre deux gares.

## Fonctionnalités

- 🚉 Surveillance en temps réel des trains entre deux gares
- ⚠️ Détection automatique des perturbations
- 🕒 Suivi des retards et suppressions
- 📊 Statistiques sur l'état de la ligne
- 🔄 Mise à jour automatique toutes les 5 minutes

## Prérequis

1. Un token Navitia (gratuit) : [S'inscrire ici](https://navitia.io/register/)
2. Les identifiants des gares (format : "stop_area:SNCF:87721001")
   - Utilisez [Navitia.io](https://api.navitia.io/) pour trouver les IDs

## Installation

### HACS

1. Assurez-vous d'avoir [HACS](https://hacs.xyz/) installé
2. Ajoutez ce dépôt comme intégration personnalisée dans HACS :
   - Cliquez sur "Intégrations" dans HACS
   - Cliquez sur les 3 points en haut à droite
   - Sélectionnez "Dépôts personnalisés"
   - Ajoutez : `https://github.com/IROFI/ha-sncf-ter` (Type: Intégration)
3. Recherchez "SNCF Disruptions" dans les intégrations HACS
4. Cliquez sur "Télécharger"
5. Redémarrez Home Assistant

### Configuration

1. Allez dans Configuration > Intégrations
2. Cliquez sur "+ Ajouter une intégration"
3. Recherchez "SNCF Disruptions"
4. Remplissez les champs :
   - Nom : Nom de votre choix
   - Token : Votre token Navitia
   - Station 1 : ID et nom de la première gare
   - Station 2 : ID et nom de la deuxième gare

## États possibles

- **Trafic normal** : Aucune perturbation détectée
- **Retards** : Au moins un train en retard
- **Perturbé** : Plusieurs retards ou une suppression
- **Fortement perturbé** : Plusieurs suppressions

## Attributs disponibles

- `trains` : Liste des trains avec :
  - Heure de départ
  - Heure d'arrivée
  - Statut (à l'heure/retard/supprimé)
- `trains_supprimes` : Nombre de trains supprimés
- `trains_retardes` : Nombre de trains en retard
- `derniere_maj` : Dernière mise à jour

## Dépannage

1. **Aucune donnée** : Vérifiez votre token Navitia
2. **Données incorrectes** : Vérifiez les IDs des gares
3. **Erreurs** : Consultez les logs de Home Assistant

## Support

- 🐛 [Signaler un bug](https://github.com/IROFI/ha-sncf-ter/issues)
- 💡 [Proposer une amélioration](https://github.com/IROFI/ha-sncf-ter/issues)