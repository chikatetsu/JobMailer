from dataclasses import dataclass
from enum import IntEnum


class DevHiring(IntEnum):
    YES = 4
    PROBABLY = 3
    DOUBT = 2
    NO = 1
    UNKNOWN = 0

    def __str__(self):
        return self.name.title()

    def step_up(self) -> "DevHiring":
        if self.value != 0:
             return DevHiring.UNKNOWN
        return DevHiring(min(DevHiring.YES, self.value + 1))

    def step_down(self) -> "DevHiring":
        if self.value == 0:
            return DevHiring.UNKNOWN
        return DevHiring(max(DevHiring.NO, self.value - 1))

# Surcharges pour des codes NAF très précis (4 chiffres sans point ni lettre)
NAF_OVERRIDES: dict[str, DevHiring] = {
    "6201": DevHiring.YES,      # Dév. logiciel (attention : concurrent si cherche emploi)
    "6202": DevHiring.YES,      # Conseil en systèmes et logiciels
    "6203": DevHiring.YES,      # Gestion d'installations informatiques
    "6209": DevHiring.YES,      # Autres activités informatiques
    "6110": DevHiring.PROBABLY, # Télécommunications filaires
    "6120": DevHiring.PROBABLY, # Télécommunications sans fil
    "6130": DevHiring.PROBABLY, # Télécommunications par satellite
    "7211": DevHiring.PROBABLY, # R&D en biotechnologie
    "7219": DevHiring.PROBABLY, # Autre R&D en sciences physiques
    "4741": DevHiring.DOUBT,    # Commerce informatique (souvent intégrateurs)
    "6420": DevHiring.DOUBT,    # Holdings financières (peu d'opérationnel)
    "6430": DevHiring.DOUBT,    # Fonds de placement
    "6491": DevHiring.DOUBT,    # Crédit-bail
    "4711": DevHiring.DOUBT,    # Hypermarchés (DSI interne possible)
    "8610": DevHiring.DOUBT,    # Activités hospitalières (SIH)

    # Agriculture, sylviculture, pêche
    "0111": DevHiring.NO, "0112": DevHiring.NO, "0113": DevHiring.NO, "0114": DevHiring.NO,
    "0115": DevHiring.NO, "0116": DevHiring.NO, "0119": DevHiring.NO, "0121": DevHiring.NO,
    "0122": DevHiring.NO, "0123": DevHiring.NO, "0124": DevHiring.NO, "0125": DevHiring.NO,
    "0126": DevHiring.NO, "0127": DevHiring.NO, "0128": DevHiring.NO, "0129": DevHiring.NO,
    "0130": DevHiring.NO, "0141": DevHiring.NO, "0142": DevHiring.NO, "0143": DevHiring.NO,
    "0144": DevHiring.NO, "0145": DevHiring.NO, "0146": DevHiring.NO, "0147": DevHiring.NO,
    "0149": DevHiring.NO, "0150": DevHiring.NO, "0161": DevHiring.NO, "0162": DevHiring.NO,
    "0163": DevHiring.NO, "0164": DevHiring.NO, "0170": DevHiring.NO, "0210": DevHiring.NO,
    "0220": DevHiring.NO, "0230": DevHiring.NO, "0240": DevHiring.NO, "0311": DevHiring.NO,
    "0312": DevHiring.NO, "0321": DevHiring.NO, "0322": DevHiring.NO,
    # Construction / BTP / artisanat du bâtiment
    "4110": DevHiring.NO, "4120": DevHiring.NO, "4211": DevHiring.NO, "4212": DevHiring.NO,
    "4213": DevHiring.NO, "4221": DevHiring.NO, "4222": DevHiring.NO, "4291": DevHiring.NO,
    "4299": DevHiring.NO, "4311": DevHiring.NO, "4312": DevHiring.NO, "4313": DevHiring.NO,
    "4321": DevHiring.NO, "4322": DevHiring.NO, "4329": DevHiring.NO, "4331": DevHiring.NO,
    "4332": DevHiring.NO, "4333": DevHiring.NO, "4334": DevHiring.NO, "4339": DevHiring.NO,
    "4391": DevHiring.NO, "4399": DevHiring.NO,
    # Artisanat (bois, métal, textile, alimentaire...)
    "1610": DevHiring.NO, "1621": DevHiring.NO, "1622": DevHiring.NO, "1623": DevHiring.NO,
    "1624": DevHiring.NO, "1629": DevHiring.NO, "2511": DevHiring.NO, "2512": DevHiring.NO,
    "2550": DevHiring.NO, "2561": DevHiring.NO, "2562": DevHiring.NO, "1411": DevHiring.NO,
    "1412": DevHiring.NO, "1413": DevHiring.NO, "1414": DevHiring.NO, "1419": DevHiring.NO,
    "1420": DevHiring.NO, "1431": DevHiring.NO, "1439": DevHiring.NO, "1071": DevHiring.NO,
    "1072": DevHiring.NO, "1073": DevHiring.NO, "1081": DevHiring.NO, "1082": DevHiring.NO,
    "1083": DevHiring.NO, "1084": DevHiring.NO, "1085": DevHiring.NO, "1086": DevHiring.NO,
    "1089": DevHiring.NO, "1091": DevHiring.NO, "1092": DevHiring.NO,
    # Coiffure, esthétique, nettoyage, réparation manuelle
    "9602": DevHiring.NO, "9604": DevHiring.NO, "8121": DevHiring.NO, "8122": DevHiring.NO,
    "9521": DevHiring.NO, "9522": DevHiring.NO, "9523": DevHiring.NO, "9524": DevHiring.NO,
    "9525": DevHiring.NO, "9529": DevHiring.NO,
    # Enseignement primaire / secondaire
    "8510": DevHiring.NO, "8520": DevHiring.NO,
    # Enseignement secondaire général / technique
    "8531": DevHiring.NO, "8532": DevHiring.NO,
    # Enseignement supérieur, post-secondaire
    "8541": DevHiring.NO, "8542": DevHiring.NO,
    # Enseignement sportif, culturel, autre
    "8551": DevHiring.NO, "8552": DevHiring.NO, "8553": DevHiring.NO, "8559": DevHiring.NO,
    # Activités de soutien à l'enseignement
    "8560": DevHiring.NO
}

NAF_SECTIONS: dict[str, DevHiring] = {
    "J": DevHiring.PROBABLY,    # Info & communication (IT, télécom, édition logiciel)
    "K": DevHiring.PROBABLY,    # Finance & assurance
    "L": DevHiring.PROBABLY,    # Immobilier (proptech)
    "M": DevHiring.PROBABLY,    # Activités spécialisées (conseil, R&D, ingénierie)
    "N": DevHiring.PROBABLY,    # Services administratifs & support
    "C": DevHiring.DOUBT,       # Industrie manufacturière (ERP, SCADA...)
    "D": DevHiring.DOUBT,       # Production énergie
    "E": DevHiring.DOUBT,       # Eau, déchets (souvent systèmes de supervision)
    "G": DevHiring.DOUBT,       # Commerce (grande distrib peut avoir des devs)
    "H": DevHiring.DOUBT,       # Transport & logistique
    "I": DevHiring.DOUBT,       # Hébergement / restauration (chaînes seulement)
    "Q": DevHiring.DOUBT,       # Santé (cliniques privées)
    "R": DevHiring.DOUBT,       # Arts & spectacles
    # "S": DevHiring.UNKNOWN,   # Services divers
    "A": DevHiring.NO,          # Agriculture
    "B": DevHiring.NO,          # Industries extractives
    "F": DevHiring.NO,          # Construction
    "O": DevHiring.NO,          # Administration publique
    "P": DevHiring.NO,          # Enseignement
    "T": DevHiring.NO,          # Ménages employeurs
    "U": DevHiring.NO,          # Extraterritorial
}

TRANCH_STEP_DOWN: set[str] = {
    "NN",   # Aucun salarié
    "00",   # Aucun salarié
    "01",   # 1-2 salariés
    "02",   # 3-5 salariés
    "03",   # 6-9 salariés
    "11",   # 10-19 salariés
    # "12", # 20-49 salariés
    # "21", # 50-99 salariés
    # "22", # 100-199 salariés
    # "31", # 200-249 salariés
    # "32", # 250-499 salariés
    # "41", # 500-999 salariés
    # "42", # 1000-1999 salariés
    # "51", # 2000-4999 salariés
    # "52", # 5000-9999 salariés
    # "53", # 10 000+ salariés
}

CATJUR_STEP_DOWN: set[str] = {
    # "5710", # SAS ok
    # "5499", # SARL ok
    # "5596", # SA ok
    # "5306", # SA à conseil de surveillance ok
    # "5307", "5308", "5309",
    "1000", # Auto-entrepreneur
    "9220", # Association
    "7389", # Collectivités publiques
    "7340", # Collectivités publiques
}

@dataclass
class ScoreDetail:
    signal: str
    points: int
