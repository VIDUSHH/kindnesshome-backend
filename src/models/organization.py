"""
Organization data model for KindnessHome platform
Handles 501(c)(3) charitable organization data from IRS via CharityAPI
"""

from datetime import datetime
from typing import Optional, Dict, Any
import sqlite3
import json

class Organization:
    def __init__(self, 
                 ein: str,
                 name: str,
                 city: Optional[str] = None,
                 state: Optional[str] = None,
                 zip_code: Optional[str] = None,
                 street: Optional[str] = None,
                 ntee_code: Optional[str] = None,
                 classification: Optional[int] = None,
                 deductibility: Optional[int] = None,
                 status: Optional[int] = None,
                 revenue_amount: Optional[int] = None,
                 asset_amount: Optional[int] = None,
                 ruling_date: Optional[str] = None,
                 last_updated: Optional[datetime] = None,
                 is_cached: bool = False):
        
        self.ein = ein
        self.name = name
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.street = street
        self.ntee_code = ntee_code
        self.classification = classification
        self.deductibility = deductibility
        self.status = status
        self.revenue_amount = revenue_amount
        self.asset_amount = asset_amount
        self.ruling_date = ruling_date
        self.last_updated = last_updated or datetime.utcnow()
        self.is_cached = is_cached

    @classmethod
    def from_charity_api(cls, data: Dict[str, Any]) -> 'Organization':
        """Create Organization instance from CharityAPI response"""
        return cls(
            ein=data.get('ein', ''),
            name=data.get('name', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip', ''),
            street=data.get('street', ''),
            ntee_code=data.get('ntee_cd', ''),
            classification=data.get('classification'),
            deductibility=data.get('deductibility'),
            status=data.get('status'),
            revenue_amount=data.get('revenue_amt'),
            asset_amount=data.get('asset_amt'),
            ruling_date=data.get('ruling')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert organization to dictionary for JSON serialization"""
        return {
            'ein': self.ein,
            'name': self.name,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'street': self.street,
            'ntee_code': self.ntee_code,
            'classification': self.classification,
            'deductibility': self.deductibility,
            'status': self.status,
            'revenue_amount': self.revenue_amount,
            'asset_amount': self.asset_amount,
            'ruling_date': self.ruling_date,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_public_charity': self.is_public_charity(),
            'is_tax_deductible': self.is_tax_deductible(),
            'category_name': self.get_category_name(),
            'revenue_range': self.get_revenue_range(),
            'full_address': self.get_full_address()
        }

    def is_public_charity(self) -> bool:
        """Check if organization is a public charity (501c3)"""
        return self.classification == 1000 and self.deductibility == 1

    def is_tax_deductible(self) -> bool:
        """Check if donations are tax deductible"""
        return self.deductibility == 1

    def get_category_name(self) -> str:
        """Get human-readable category name from NTEE code"""
        if not self.ntee_code:
            return "Unknown"
        
        # NTEE Major Group mapping
        ntee_categories = {
            'A': 'Arts, Culture & Humanities',
            'B': 'Education',
            'C': 'Environment and Animals', 
            'D': 'Animal-Related',
            'E': 'Health',
            'F': 'Mental Health, Crisis Intervention',
            'G': 'Diseases, Disorders, Medical Disciplines',
            'H': 'Medical Research',
            'I': 'Crime, Legal Related',
            'J': 'Employment, Job Related',
            'K': 'Food, Agriculture, and Nutrition',
            'L': 'Housing, Shelter',
            'M': 'Public Safety, Disaster Preparedness',
            'N': 'Recreation, Sports, Leisure, Athletics',
            'O': 'Youth Development',
            'P': 'Human Services',
            'Q': 'International, Foreign Affairs',
            'R': 'Civil Rights, Social Action, Advocacy',
            'S': 'Community Improvement, Capacity Building',
            'T': 'Philanthropy, Voluntarism, Grantmaking',
            'U': 'Science and Technology Research',
            'V': 'Social Science Research',
            'W': 'Public, Society Benefit',
            'X': 'Religion Related',
            'Y': 'Mutual/Membership Benefit',
            'Z': 'Unknown'
        }
        
        first_letter = self.ntee_code[0].upper()
        return ntee_categories.get(first_letter, 'Unknown')

    def get_revenue_range(self) -> str:
        """Get human-readable revenue range"""
        if not self.revenue_amount:
            return "Not Available"
        
        amount = self.revenue_amount
        if amount < 100000:
            return "Under $100K"
        elif amount < 500000:
            return "$100K - $500K"
        elif amount < 1000000:
            return "$500K - $1M"
        elif amount < 10000000:
            return "$1M - $10M"
        else:
            return "Over $10M"

    def get_full_address(self) -> str:
        """Get formatted full address"""
        parts = []
        if self.street:
            parts.append(self.street)
        if self.city:
            parts.append(self.city)
        if self.state:
            if self.zip_code:
                parts.append(f"{self.state} {self.zip_code}")
            else:
                parts.append(self.state)
        
        return ", ".join(parts) if parts else ""

class OrganizationCache:
    """SQLite cache for organization data"""
    
    def __init__(self, db_path: str = "organizations_cache.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the organizations cache database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS organizations (
                ein TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                street TEXT,
                ntee_code TEXT,
                classification INTEGER,
                deductibility INTEGER,
                status INTEGER,
                revenue_amount INTEGER,
                asset_amount INTEGER,
                ruling_date TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                search_count INTEGER DEFAULT 0,
                is_popular BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create indexes for better search performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_name ON organizations(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_state ON organizations(state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_ntee ON organizations(ntee_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_popular ON organizations(is_popular)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_org_search_count ON organizations(search_count)')
        
        conn.commit()
        conn.close()

    def get_organization(self, ein: str) -> Optional[Organization]:
        """Get organization from cache by EIN"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM organizations WHERE ein = ?
        ''', (ein,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_organization(row)
        return None

    def save_organization(self, org: Organization):
        """Save organization to cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO organizations 
            (ein, name, city, state, zip_code, street, ntee_code, classification,
             deductibility, status, revenue_amount, asset_amount, ruling_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            org.ein, org.name, org.city, org.state, org.zip_code, org.street,
            org.ntee_code, org.classification, org.deductibility, org.status,
            org.revenue_amount, org.asset_amount, org.ruling_date, org.last_updated
        ))
        
        conn.commit()
        conn.close()

    def increment_search_count(self, ein: str):
        """Increment search count for an organization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE organizations 
            SET search_count = search_count + 1 
            WHERE ein = ?
        ''', (ein,))
        
        conn.commit()
        conn.close()

    def get_popular_organizations(self, limit: int = 20) -> list[Organization]:
        """Get most searched organizations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM organizations 
            ORDER BY search_count DESC, name ASC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_organization(row) for row in rows]

    def search_organizations(self, query: str, state: str = None, limit: int = 20) -> list[Organization]:
        """Search organizations in cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT * FROM organizations 
            WHERE name LIKE ? OR city LIKE ?
        '''
        params = [f'%{query}%', f'%{query}%']
        
        if state:
            sql += ' AND state = ?'
            params.append(state.upper())
        
        sql += ' ORDER BY search_count DESC, name ASC LIMIT ?'
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_organization(row) for row in rows]

    def _row_to_organization(self, row) -> Organization:
        """Convert database row to Organization object"""
        return Organization(
            ein=row[0],
            name=row[1],
            city=row[2],
            state=row[3],
            zip_code=row[4],
            street=row[5],
            ntee_code=row[6],
            classification=row[7],
            deductibility=row[8],
            status=row[9],
            revenue_amount=row[10],
            asset_amount=row[11],
            ruling_date=row[12],
            last_updated=datetime.fromisoformat(row[13]) if row[13] else None,
            is_cached=True
        )

