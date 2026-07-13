"""
Authentification Garmin Connect — à lancer TOI-MÊME dans ton terminal.

Le mot de passe est saisi en local (masqué, via getpass) et ne transite jamais
par le chat Claude ni par aucun fichier du repo. Seule une session (token
OAuth, pas le mot de passe) est sauvegardée sur ton poste, dans ~/.garminconnect.

Usage :
  python garmin_login.py

Une fois connecté, les scripts suivants (ex: garmin_fetch_sets.py) réutilisent
cette session automatiquement, sans redemander le mot de passe (jusqu'à
expiration du token, généralement plusieurs mois).
"""
import getpass
from pathlib import Path
from garminconnect import Garmin, GarminConnectAuthenticationError

TOKENSTORE = str(Path.home() / '.garminconnect')


def prompt_mfa():
    return input('Code de vérification (MFA) reçu par email/app Garmin : ').strip()


def main():
    email = input('Email Garmin Connect : ').strip()
    password = getpass.getpass('Mot de passe Garmin Connect (saisie masquée) : ')

    garmin = Garmin(email, password, prompt_mfa=prompt_mfa)
    try:
        garmin.login()
    except GarminConnectAuthenticationError as e:
        print(f'[erreur] Échec de connexion : {e}')
        return

    garmin.garth.dump(TOKENSTORE)
    who = garmin.full_name or garmin.display_name
    print(f'[ok] Connecté en tant que {who}.')
    print(f'[ok] Session sauvegardée dans {TOKENSTORE} — plus besoin du mot de passe ensuite.')


if __name__ == '__main__':
    main()
