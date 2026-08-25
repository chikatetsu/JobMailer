import sqlite3
from pathlib import Path

from models.city import City
from models.company import Company
from utils.company_sorting import DevHiring
from utils.logger import create_logger


class CompanyRepository:
    def __init__(self, check_same_thread: bool = True):
        project_root = Path(__file__).resolve().parent.parent
        bdd_name = project_root / "data" / "db" / f"jobs.db"
        self.conn = sqlite3.connect(bdd_name, check_same_thread=check_same_thread)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siren TEXT,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                lat REAL,
                lon REAL,
                url TEXT,
                logo TEXT,
                tranch_employees TEXT,
                has_employees_in_location BOOLEAN,
                date_creation_company DATE,
                date_creation_location DATE,
                main_activity TEXT,
                company_type TEXT,
                is_siege BOOLEAN,
                dev_hiring INTEGER
            )
        """)
        self.conn.row_factory = sqlite3.Row
        self.log = create_logger(CompanyRepository.__name__)

    @staticmethod
    def _company_from_row(row) -> Company:
        company = Company(
            id=row["id"],
            siren=row["siren"],
            name=row["name"],
            address=row["address"],
            city=row["city"],
            url=row["url"] if row["url"] else "",
            lat=row["lat"],
            lon=row["lon"],
            logo=row["logo"] if row["logo"] else "",
            tranch_employees=row["tranch_employees"],
            has_employees_in_location=row["has_employees_in_location"],
            date_creation_company=row["date_creation_company"],
            date_creation_location=row["date_creation_location"],
            main_activity=row["main_activity"],
            company_type=row["company_type"],
            is_siege=row["is_siege"],
            dev_hiring=DevHiring(int(row["dev_hiring"])),
        )
        return company

    def get_all_companies(self, cities: list[City] | City) -> list[Company]:
        companies = []
        if isinstance(cities, City):
            cities = [cities]
        for city in cities:
            cursor = self.conn.execute("SELECT * FROM companies WHERE city = ? ORDER BY dev_hiring DESC, name ASC", (str(city),))
            for row in cursor:
                if row:
                    company = self._company_from_row(row)
                    companies.append(company)
        return companies

    def get_company_by_id(self, company_id: int) -> Company | None:
        cursor = self.conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        if row:
            company = self._company_from_row(row)
            return company
        return None

    def get_company_by_name(self, name: str, city: City) -> Company | None:
        company_name = (
            name.upper()
                .replace(str(city), "")
                .replace("FRANCE", "")
                .replace(" SARL", "")
                .replace(" SASU", "")
                .replace(" SAS", "")
                .replace(" S.A.S.", "")
                .replace("É", "")
                .replace("®", "")
                .strip()
        )
        cursor = self.conn.execute("SELECT * FROM companies WHERE name = ? AND city = ?", (company_name, str(city)))
        row = cursor.fetchone()
        if row:
            company = self._company_from_row(row)
            return company
        cursor = self.conn.execute("SELECT * FROM companies WHERE name LIKE ? AND city = ? ORDER BY dev_hiring DESC", (f"%{company_name}%", str(city)))
        row = cursor.fetchone()
        if row:
            company = self._company_from_row(row)
            return company
        return None

    def update_company(self, company_id: int, company: Company) -> bool:
        saved_company = self.get_company_by_id(company_id)
        if not saved_company:
            return self.insert_company(company)
        try:
            self.conn.execute("""
                UPDATE companies
                SET siren = :siren,
                    name = :name,
                    address = :address,
                    city = :city,
                    lat = :lat,
                    lon = :lon,
                    url = :url,
                    logo = :logo,
                    tranch_employees = :tranch_employees,
                    has_employees_in_location = :has_employees_in_location,
                    date_creation_company = :date_creation_company,
                    date_creation_location = :date_creation_location,
                    main_activity = :main_activity,
                    company_type = :company_type,
                    is_siege = :is_siege,
                    dev_hiring = :dev_hiring
                WHERE id = :company_id
            """, {
                "siren": company.siren if company.siren else saved_company.siren,
                "name": company.name if company.name else saved_company.name,
                "address": company.address if company.address else saved_company.address,
                "city": company.city if company.city else saved_company.city,
                "lat": company.lat if company.lat else saved_company.lat,
                "lon": company.lon if company.lon else saved_company.lon,
                "url": company.url if company.url else saved_company.url,
                "logo": company.logo if company.logo else saved_company.logo,
                "tranch_employees": company.tranch_employees if company.tranch_employees else saved_company.tranch_employees,
                "has_employees_in_location": company.has_employees_in_location if company.has_employees_in_location else saved_company.has_employees_in_location,
                "date_creation_company": company.date_creation_company if company.date_creation_company else saved_company.date_creation_company,
                "date_creation_location": company.date_creation_location if company.date_creation_location else saved_company.date_creation_location,
                "main_activity": company.main_activity if company.main_activity else saved_company.main_activity,
                "company_type": company.company_type if company.company_type else saved_company.company_type,
                "is_siege": company.is_siege if company.is_siege else saved_company.is_siege,
                "dev_hiring": company.dev_hiring.value if company.dev_hiring.value != 0 else saved_company.dev_hiring.value,
                "company_id": company_id
            })
        except Exception as e:
            self.log.error(f"Failed to update company: {e}")
            return False
        return True

    def insert_company(self, company: Company) -> bool:
        try:
            self.conn.execute("""
                INSERT INTO companies (
                    siren, name, address, city, lat, lon, url, logo, tranch_employees,
                    has_employees_in_location, date_creation_company, date_creation_location, main_activity,
                    company_type, is_siege, dev_hiring
                ) VALUES (
                    :siren, :name, :address, :city, :lat, :lon, :url, :logo, :tranch_employees,
                    :has_employees_in_location, :date_creation_company, :date_creation_location, :main_activity,
                    :company_type, :is_siege, :dev_hiring
                )""", {
                    "siren": company.siren if company.siren else "",
                    "name": company.name if company.name else "",
                    "address": company.address if company.address else "",
                    "city": company.city if company.city else "",
                    "lat": company.lat if company.lat else None,
                    "lon": company.lon if company.lon else None,
                    "url": company.url if company.url else "",
                    "logo": company.logo if company.logo else "",
                    "tranch_employees": company.tranch_employees if company.tranch_employees else "",
                    "has_employees_in_location": company.has_employees_in_location,
                    "date_creation_company": company.date_creation_company,
                    "date_creation_location": company.date_creation_location,
                    "main_activity": company.main_activity if company.main_activity else "",
                    "company_type": company.company_type if company.company_type else "",
                    "is_siege": company.is_siege,
                    "dev_hiring": company.dev_hiring.value
            })
            return True
        except Exception as e:
            self.log.error(f"Failed to insert company: {e}")
            return False

    def delete_company_by_id(self, company_id: int) -> bool:
        try:
            self.conn.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            return True
        except Exception as e:
            self.log.error(f"Failed to delete company: {e}")
            return False

    def commit(self):
        self.conn.commit()
