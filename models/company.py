from datetime import datetime
from pydantic import BaseModel

from utils.company_sorting import ScoreDetail, NAF_OVERRIDES, NAF_SECTIONS, DevHiring, TRANCH_STEP_DOWN, CATJUR_STEP_DOWN


class Company(BaseModel):
    id: int = 0
    siren : str = ""
    name: str
    address: str = ""
    city: str = ""
    lat: float | None = None
    lon: float | None = None
    url: str = ""
    logo: str = ""
    tranch_employees: str = "NN"
    has_employees_in_location: bool | None = None
    date_creation_company: datetime | None = None
    date_creation_location: datetime | None = None
    main_activity: str
    company_type: str = ""
    is_siege: bool | None = None
    dev_hiring: DevHiring = DevHiring.UNKNOWN
    is_declared_hiring: bool = True
    details: list[ScoreDetail] = []


    def get_dev_hiring(self):
        today = datetime.today()
        self.details = []

        naf_clean = self.main_activity.replace(".", "").replace(" ", "").upper()
        naf_4 = naf_clean[:4]
        section = naf_clean[0] if naf_clean else "?"

        self.dev_hiring = NAF_OVERRIDES.get(naf_4, NAF_SECTIONS.get(section, DevHiring.DOUBT))
        self.details.append(ScoreDetail(f"NAF {self.main_activity}", self.dev_hiring.value))

        if self.dev_hiring == DevHiring.NO:
            return

        if not self.is_declared_hiring:
            self.dev_hiring = self.dev_hiring.step_down()
            self.details.append(ScoreDetail("Non Employeur", -1))

        if self.tranch_employees in TRANCH_STEP_DOWN:
            self.dev_hiring = self.dev_hiring.step_down()
            self.details.append(ScoreDetail("Pas assez d'employés", -1))

        if not self.has_employees_in_location:
            if self.date_creation_location:
                ecart_jours = (today - self.date_creation_location).days
                if ecart_jours < 0:
                    self.dev_hiring = DevHiring.NO
                    self.details.append(ScoreDetail("Établissement plus récent que l'entreprise (ANOMALIE)", self.dev_hiring.value))
                    return
                elif ecart_jours >= 365 * 3:
                    self.dev_hiring = self.dev_hiring.step_down()
                    self.details.append(ScoreDetail("Établissement vide après 3 ans d'existance", -1))
            else:
                self.dev_hiring = self.dev_hiring.step_down()
                self.details.append(ScoreDetail("Établissement vide", -1))

        if self.company_type and self.company_type[:4] in CATJUR_STEP_DOWN:
            self.dev_hiring = self.dev_hiring.step_down()
            self.details.append(ScoreDetail(self.get_company_type_name(), -1))


    def get_dev_details(self) -> str:
        return ", ".join([f"{details.signal}: {details.points}" for details in self.details])

    def get_nb_employees(self) -> tuple[int, int]:
        tranch_map = {
            "NN": (0, 0),
            "00": (0, 0),
            "01": (1, 2),
            "02": (3, 5),
            "03": (6, 9),
            "11": (10, 19),
            "12": (20, 49),
            "21": (50, 99),
            "22": (100, 199),
            "31": (200, 249),
            "32": (250, 499),
            "41": (500, 999),
            "42": (1000, 1999),
            "51": (2000, 4999),
            "52": (5000, 9999),
            "53": (10000, 100000),
        }
        employees = tranch_map.get(self.tranch_employees, (0, 0))
        return employees

    def get_company_type_name(self) -> str:
        company_type_map = {
            "5710": "SAS",
            "5499": "SARL",
            "5596": "SA",
            "5306": "SA à conseil de surveillance",
            "5307": "Société commerciale",
            "5308": "Société commerciale",
            "5309": "Société commerciale",
            "1000": "Auto-entrepreneur",
            "9220": "Association",
            "7389": "Collectivité publique",
            "7340": "Collectivité publique",
        }
        type_name = company_type_map.get(self.company_type, self.company_type)
        return type_name

    def get_main_activity(self) -> str:
        company_activity_map = {
            "6201": "Développement de logiciel",
            "6202": "Conseil en systèmes et logiciels",
            "6203": "Gestion d'installations informatiques",
            "6209": "Autres activités informatiques",
            "6110": "Télécommunications filaires",
            "6120": "Télécommunications sans fil",
            "6130": "Télécommunications par satellite",
            "7211": "R&D en biotechnologie",
            "7219": "Autre R&D en sciences physiques",
            "4741": "Commerce informatique",
            "6420": "Holdings financières",
            "6430": "Fonds de placement",
            "6491": "Crédit-bail",
            "4711": "Hypermarchés",
            "8610": "Activités hospitalières",
            "0111": "Agriculture, sylviculture, pêche", "0112": "Agriculture, sylviculture, pêche",
            "0113": "Agriculture, sylviculture, pêche", "0114": "Agriculture, sylviculture, pêche",
            "0115": "Agriculture, sylviculture, pêche", "0116": "Agriculture, sylviculture, pêche",
            "0119": "Agriculture, sylviculture, pêche", "0121": "Agriculture, sylviculture, pêche",
            "0122": "Agriculture, sylviculture, pêche", "0123": "Agriculture, sylviculture, pêche",
            "0124": "Agriculture, sylviculture, pêche", "0125": "Agriculture, sylviculture, pêche",
            "0126": "Agriculture, sylviculture, pêche", "0127": "Agriculture, sylviculture, pêche",
            "0128": "Agriculture, sylviculture, pêche", "0129": "Agriculture, sylviculture, pêche",
            "0130": "Agriculture, sylviculture, pêche", "0141": "Agriculture, sylviculture, pêche",
            "0142": "Agriculture, sylviculture, pêche", "0143": "Agriculture, sylviculture, pêche",
            "0144": "Agriculture, sylviculture, pêche", "0145": "Agriculture, sylviculture, pêche",
            "0146": "Agriculture, sylviculture, pêche", "0147": "Agriculture, sylviculture, pêche",
            "0149": "Agriculture, sylviculture, pêche", "0150": "Agriculture, sylviculture, pêche",
            "0161": "Agriculture, sylviculture, pêche", "0162": "Agriculture, sylviculture, pêche",
            "0163": "Agriculture, sylviculture, pêche", "0164": "Agriculture, sylviculture, pêche",
            "0170": "Agriculture, sylviculture, pêche", "0210": "Agriculture, sylviculture, pêche",
            "0220": "Agriculture, sylviculture, pêche", "0230": "Agriculture, sylviculture, pêche",
            "0240": "Agriculture, sylviculture, pêche", "0311": "Agriculture, sylviculture, pêche",
            "0312": "Agriculture, sylviculture, pêche", "0321": "Agriculture, sylviculture, pêche",
            "0322": "Agriculture, sylviculture, pêche",
            "4110": "Construction / BTP / artisanat du bâtiment", "4120": "Construction / BTP / artisanat du bâtiment",
            "4211": "Construction / BTP / artisanat du bâtiment", "4212": "Construction / BTP / artisanat du bâtiment",
            "4213": "Construction / BTP / artisanat du bâtiment", "4221": "Construction / BTP / artisanat du bâtiment",
            "4222": "Construction / BTP / artisanat du bâtiment", "4291": "Construction / BTP / artisanat du bâtiment",
            "4299": "Construction / BTP / artisanat du bâtiment", "4311": "Construction / BTP / artisanat du bâtiment",
            "4312": "Construction / BTP / artisanat du bâtiment", "4313": "Construction / BTP / artisanat du bâtiment",
            "4321": "Construction / BTP / artisanat du bâtiment", "4322": "Construction / BTP / artisanat du bâtiment",
            "4329": "Construction / BTP / artisanat du bâtiment", "4331": "Construction / BTP / artisanat du bâtiment",
            "4332": "Construction / BTP / artisanat du bâtiment", "4333": "Construction / BTP / artisanat du bâtiment",
            "4334": "Construction / BTP / artisanat du bâtiment", "4339": "Construction / BTP / artisanat du bâtiment",
            "4391": "Construction / BTP / artisanat du bâtiment", "4399": "Construction / BTP / artisanat du bâtiment",
            "1610": "Artisanat (bois, métal, textile, alimentaire...)", "1621": "Artisanat (bois, métal, textile, alimentaire...)",
            "1622": "Artisanat (bois, métal, textile, alimentaire...)", "1623": "Artisanat (bois, métal, textile, alimentaire...)",
            "1624": "Artisanat (bois, métal, textile, alimentaire...)", "1629": "Artisanat (bois, métal, textile, alimentaire...)",
            "2511": "Artisanat (bois, métal, textile, alimentaire...)", "2512": "Artisanat (bois, métal, textile, alimentaire...)",
            "2550": "Artisanat (bois, métal, textile, alimentaire...)", "2561": "Artisanat (bois, métal, textile, alimentaire...)",
            "2562": "Artisanat (bois, métal, textile, alimentaire...)", "1411": "Artisanat (bois, métal, textile, alimentaire...)",
            "1412": "Artisanat (bois, métal, textile, alimentaire...)", "1413": "Artisanat (bois, métal, textile, alimentaire...)",
            "1414": "Artisanat (bois, métal, textile, alimentaire...)", "1419": "Artisanat (bois, métal, textile, alimentaire...)",
            "1420": "Artisanat (bois, métal, textile, alimentaire...)", "1431": "Artisanat (bois, métal, textile, alimentaire...)",
            "1439": "Artisanat (bois, métal, textile, alimentaire...)", "1071": "Artisanat (bois, métal, textile, alimentaire...)",
            "1072": "Artisanat (bois, métal, textile, alimentaire...)", "1073": "Artisanat (bois, métal, textile, alimentaire...)",
            "1081": "Artisanat (bois, métal, textile, alimentaire...)", "1082": "Artisanat (bois, métal, textile, alimentaire...)",
            "1083": "Artisanat (bois, métal, textile, alimentaire...)", "1084": "Artisanat (bois, métal, textile, alimentaire...)",
            "1085": "Artisanat (bois, métal, textile, alimentaire...)", "1086": "Artisanat (bois, métal, textile, alimentaire...)",
            "1089": "Artisanat (bois, métal, textile, alimentaire...)", "1091": "Artisanat (bois, métal, textile, alimentaire...)",
            "1092": "Artisanat (bois, métal, textile, alimentaire...)",
            "9602": "Coiffure, esthétique, nettoyage, réparation manuelle", "9604": "Coiffure, esthétique, nettoyage, réparation manuelle",
            "8121": "Coiffure, esthétique, nettoyage, réparation manuelle", "8122": "Coiffure, esthétique, nettoyage, réparation manuelle",
            "9521": "Coiffure, esthétique, nettoyage, réparation manuelle", "9522": "Coiffure, esthétique, nettoyage, réparation manuelle",
            "9523": "Coiffure, esthétique, nettoyage, réparation manuelle", "9524": "Coiffure, esthétique, nettoyage, réparation manuelle",
            "9525": "Coiffure, esthétique, nettoyage, réparation manuelle", "9529": "Coiffure, esthétique, nettoyage, réparation manuelle",
            "8510": "Enseignement primaire / secondaire", "8520": "Enseignement primaire / secondaire",
            "8531": "Enseignement secondaire général / technique", "8532": "Enseignement secondaire général / technique",
            "8541": "Enseignement supérieur, post-secondaire", "8542": "Enseignement supérieur, post-secondaire",
            "8551": "Enseignement sportif, culturel, autre", "8552": "Enseignement sportif, culturel, autre",
            "8553": "Enseignement sportif, culturel, autre", "8559": "Enseignement sportif, culturel, autre",
            "8560": "Activités de soutien à l'enseignement"
        }
        activity_name = company_activity_map.get(self.main_activity.replace(".", "").replace(" ", "")[:4], self.main_activity)
        return activity_name
