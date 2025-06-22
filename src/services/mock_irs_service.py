import os
import requests
import json
from datetime import datetime
from flask import current_app

class MockIRSDataService:
    """Mock IRS service for demonstration purposes"""
    
    def __init__(self):
        self.mock_organizations = [
            {
                'ein': '530196605',
                'name': 'American Red Cross',
                'city': 'Washington',
                'state': 'DC',
                'zip_code': '20006',
                'ntee_code': 'P20',
                'tax_exempt_status': '501(c)(3)',
                'is_verified': True
            },
            {
                'ein': '134334452',
                'name': 'Doctors Without Borders USA Inc',
                'city': 'New York',
                'state': 'NY',
                'zip_code': '10013',
                'ntee_code': 'Q30',
                'tax_exempt_status': '501(c)(3)',
                'is_verified': True
            },
            {
                'ein': '363673599',
                'name': 'Feeding America',
                'city': 'Chicago',
                'state': 'IL',
                'zip_code': '60601',
                'ntee_code': 'K31',
                'tax_exempt_status': '501(c)(3)',
                'is_verified': True
            },
            {
                'ein': '137884491',
                'name': 'American Cancer Society Inc',
                'city': 'Atlanta',
                'state': 'GA',
                'zip_code': '30303',
                'ntee_code': 'G12',
                'tax_exempt_status': '501(c)(3)',
                'is_verified': True
            },
            {
                'ein': '521693387',
                'name': 'World Wildlife Fund Inc',
                'city': 'Washington',
                'state': 'DC',
                'zip_code': '20037',
                'ntee_code': 'C01',
                'tax_exempt_status': '501(c)(3)',
                'is_verified': True
            }
        ]
    
    def validate_ein_format(self, ein):
        """Validate EIN format (XX-XXXXXXX)"""
        import re
        
        # Remove any formatting
        clean_ein = re.sub(r'[^0-9]', '', ein)
        
        # Check if it's 9 digits
        if len(clean_ein) != 9:
            return False
        
        return True
    
    def get_ntee_category(self, ntee_code):
        """Get category from NTEE code"""
        if not ntee_code:
            return "Other"
        
        # NTEE major group mappings
        ntee_mappings = {
            'A': 'Arts & Culture',
            'B': 'Education',
            'C': 'Environment',
            'D': 'Animal Welfare',
            'E': 'Health',
            'F': 'Mental Health',
            'G': 'Disease Research',
            'H': 'Medical Research',
            'I': 'Crime & Legal',
            'J': 'Employment',
            'K': 'Food & Agriculture',
            'L': 'Housing',
            'M': 'Public Safety',
            'N': 'Recreation & Sports',
            'O': 'Youth Development',
            'P': 'Human Services',
            'Q': 'International',
            'R': 'Civil Rights',
            'S': 'Community Improvement',
            'T': 'Philanthropy',
            'U': 'Science & Technology',
            'V': 'Social Science',
            'W': 'Public & Societal Benefit',
            'X': 'Religion',
            'Y': 'Mutual Benefit',
            'Z': 'Unknown'
        }
        
        major_group = ntee_code[0].upper() if ntee_code else 'Z'
        return ntee_mappings.get(major_group, 'Other')
    
    def get_mock_categories(self):
        """Get mock NTEE categories with counts"""
        categories = [
            {'code': 'P', 'name': 'Human Services', 'organization_count': 15000},
            {'code': 'X', 'name': 'Religion', 'organization_count': 18000},
            {'code': 'B', 'name': 'Education', 'organization_count': 12000},
            {'code': 'E', 'name': 'Health', 'organization_count': 8500},
            {'code': 'A', 'name': 'Arts & Culture', 'organization_count': 4800},
            {'code': 'C', 'name': 'Environment', 'organization_count': 3200},
            {'code': 'D', 'name': 'Animal Welfare', 'organization_count': 2100},
            {'code': 'Q', 'name': 'International', 'organization_count': 1900}
        ]
        return categories
    
    def verify_organization(self, ein):
        """Mock organization verification"""
        clean_ein = ein.replace('-', '').zfill(9)
        
        for org in self.mock_organizations:
            if org['ein'] == clean_ein:
                return {
                    'valid': True,
                    'verified': True,
                    'organization': org,
                    'source': 'mock_irs_database'
                }
        
        return {
            'valid': False,
            'error': 'Organization not found in IRS database'
        }

