# JobMailer

**JobMailer** est une application qui vous permet de trouver le job de vos rêve! Il cherche tous les jours des offres d'emploi sur différents site de recherche d'emploi, les filtres selon vos intérêts, et vous les envoie par mail pour faciliter votre recherche. Vous pourrez aussi les consulter et les gérer dans le site web hébergé de JobMailer, définir à quelles offres d'emploi vous avez postulé, et ainsi mieux suivre vos candidatures.

***

## Installation

**JobMailer** a besoin d'être hébergé sur un serveur, soit dans le cloud ou à la maison pour plus de contrôle de vos données.

## 1. Préparez le serveur
- **Clonez le projet**
- Installez **Firefox** si ça n'est pas déjà fait, pour récupérer les informations de certains sites web
- Installez **Python 3** si ça n'est pas déjà fait
- Installer **gunicorn**

## 2. Créez l'environnement python
```bash
cd JobMailer/
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Créez le fichier de configuration config.py
Le script **config.py** vous permet de paramétrer JobMailer pour votre recherche personnelle. Pour commencer, copiez config_example.py pour avoir la base du fichier :
```bash
cp config_example.py config.py
```
Enlevez tous les caractères '**#**' dans le fichier.

Maintenant, il faut paramétrer chaques attributs selon vos besoins :

### 3.1. France Travail
Si vous ne voulez pas rechercher vos offres d'emploi sur France Travail, vous pouvez simplement laisser les paramètres **FRANCE_TRAVAIL_CLIENT_ID** et **FRANCE_TRAVAIL_API_KEY** vides.

Si vous voulez rechercher vos offres d'emploi sur France Travail, vous aurez besoin de votre **client id** et de votre **clé d'api** France Travail. Pour celà, vous devez vous créer un compte sur [https://francetravail.io/](https://francetravail.io/) pour avoir le vôtre (c'est gratuit).
Ensuite, modifiez les valeurs de **FRANCE_TRAVAIL_CLIENT_ID** et de **FRANCE_TRAVAIL_API_KEY** par vos informations. Pour vérifier que votre clé d'api fonctionne bien avec JobMailer, lancez `python main.py` avec juste **[Site.FRANCE_TRAVAIL]** dans l'attribut **websites** de **SCRAPER_CONFIG**.

### 3.2. Authentification de l'email
Vous aurez besoin de mettre vos informations d'email dans ces paramètres. L'application va les utiliser pour vous envoyer des emails avec votre propre adresse email. Ces informations ne seront stocké que sur votre serveur, protégez les.

Vous aurez besoin de modifier les valeurs **SMTP_SERVER**, **SENDER_EMAIL** et **SENDER_PASSWORD**. Vous trouverez ces informations sur le site web de votre service d'email. Il est possible que vous ne puissiez pas utiliser votre vrai mot de passe pour le paramètre **SENDER_PASSWORD**. Par exemple, pour GMail, il faut créer une application et récupérer le mot de passe que Google vous donne.

### 3.3. Chemin de l'exécutable vers Firefox
Si pour une raison quelconque vous ne voulez ou vous ne pouvez pas installer Firefox sur votre serveur, vous pouvez laisser le paramètre **FIREFOX_PATH** vide. Toutefois, tous les scrapers utilisant Selenium seront incabable de fonctionner sans. Voici les sites web concernés :
- Hellowork
- Indeed

Pour trouver l'exécutable de Firefox, utilisez la commande suivante :
```bash
whereis firefox
```
Si vous avez installé Firefox depuis snap, le chemin vers l'exécutable est en général "/snap/firefox/current/usr/lib/firefox/firefox".

### 3.4. L'url de JobMailer
Définir une url et un port pour JobMailer vous permet de marquer comme lues les offres d'emploi sur lesquelles vous avez cliqué dans vos mails. Le port est obligatoire, mais si vous ne souhaitez pas ou ne pouvez pas définir une url pour JobMailer, laissez **JOB_MAILER_ULR** avec une chaine de caractère vide.

Sinon, donnez la valeur de l'url à **JOB_MAILER_URL** et le port dans **JOB_MAILER_PORT**.

### 3.4. Scraper input
**SCRAPER_INPUT** correspond aux options de recherche de votre recherche d'emploi. Voici à quoi correspondent chacun de ses attributs :
- **search_term** : Le nom de l'emploi que vous recherchez
- **cities** : La liste des villes dans lesquels vous cherchez du travail. Les villes supportées sont dans le script models/city.py
- **distance** : Le rayon en km autour des villes dans lesquelles vous cherchez du travail

### 3.5. Scraper Config
**SCRAPER_CONFIG** correspond à la configuration globale de JobMailer. Ses attributs sont :
- **websites** : La liste des sites web où vous cherchez du travail. Les sites disponibles sont dans le script models/site.py
- **verbose** : Le paramètre qui permet de changer le nombre de logs affiché lors du scraping. Il peut être soit **ONLY_ERRORS**, **ALL_WARNINGS** ou **VERBOSE**

### 3.6. Filter Input
**FILTER_INPUT** vous permet de filtrer toutes les offres inintéressantes pour vous faire gagner du temps dans votre recherche. Il est composé de ces attributs :
- **remote_types** : La liste des types de télétravail que vous préférez. Les différentes options sont dans le script models/remote_type.py
- **experiences** : La liste de votre expérience dans votre domaine. Les différentes options sont dans le script models/experience.py
- **contract_types** : La liste des types de contrats que vous recherchez. Les différentes options sont dans le script models/contract_type.py
- **ignore_words** : La liste des mots clés que vous voulez éviter à tout prix de voir dans une offre d'emploi (sa description, son titre, etc.)
- **ignore_words_in_title** : La liste des mots clés que vous voulez éviter à tout prix de voir dans le titre d'une offre d'emploi

### 3.7. Interest Input
**INTEREST_INPUT** vous permet de définir vos centres d'intérêt pour trier les offres d'emploi par pertinence. Il est particulièrement utile si vous trouvez que les attributs **ignore_words** et **ignore_words_in_title** de **FILTER_INPUT** sont trop violent. Vous pouvez ainsi définir une pertinence négative pour certains mots clés. Voici ces attributs : 
- **words_in_title** : Un dictionnaire de mots que vous voulez voir dans le titre d'une offre d'emploi, avec un score d'importance (ex: {"rust": 1000})
- **words_in_description** : Un dictionnaite de mots que vous voulez voir dans une offre d'emploi en général, avec un score d'importance

## 4. Préparer le scraper

Maintenant que vous avez configuré JobMailer, il va falloir faire en sorte que l'application vous envoie un mail tous les jours. **Testez que l'envoie de mail se fait correctement en lançant la commande `python main.py`**.

Ouvrez l'éditeur de tâches cron :
```bash
crontab -e
```
Ajoutez une règle qui permet de lancer le scraper tous les jours à 9h00 :
```bash
0 9 * * * /JobMailer/.venv/bin/python /JobMailer/main.py
```
Ainsi, le serveur mettra à jour les nouvelles offres d'emploi disponibles sur l'application et vous les enverra par mail entre 9h00 et 9h30. Pour changer l'heure à laquelle vous voulez recevoir le mail ou à quelle fréquence, regardez la documentation de cron.

## 5. Lancer le site
Pour visualiser les offres d'emploi, et gérer quelles offres vous avez vu ou auquel vous avez postulé, lancez le site web JobMailer sur votre serveur.
```bash
gunicorn --bind 0.0.0.0:5000 app:app
```
Pour que le site web se lance automatiquement au redémarrage du serveur, créez un service qui se lance au démarrage. Renseignez-vous sur le fonctionnement des services et de systemctl pour linux.
