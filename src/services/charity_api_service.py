"""
CharityAPI service integration for KindnessHome platform
Handles communication with CharityAPI.org for IRS nonprofit data
"""

import os
import requests
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CharityAPIService:
    """Service for interacting with CharityAPI.org"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('CHARITY_API_KEY')
        self.base_url = 'https://api.charityapi.org'
        self.headers = {
            'apikey': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if not self.api_key:
            logger.warning("CharityAPI key not found. Set CHARITY_API_KEY environment variable.")

    def search_organizations(self, 
                           query: str, 
                           city: str = None, 
                           state: str = None, 
                           limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for organizations by name, city, or state
        
        Args:
            query: Search term for organization name
            city: Filter by city (optional)
            state: Filter by state code (optional)
            limit: Maximum number of results (default 20)
            
        Returns:
            List of organization dictionaries
        """
        try:
            # Build search URL
            url = f"{self.base_url}/api/organizations/search/{query}"
            params = {}
            
            if city:
                params['city'] = city
            if state:
                params['state'] = state.upper()
                
            logger.info(f"Searching CharityAPI for: {query}")
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                organizations = data.get('data', [])
                
                # Limit results
                if limit and len(organizations) > limit:
                    organizations = organizations[:limit]
                    
                logger.info(f"Found {len(organizations)} organizations")
                return organizations
                
            elif response.status_code == 404:
                logger.info(f"No organizations found for query: {query}")
                return []
                
            else:
                logger.error(f"CharityAPI search failed: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"CharityAPI request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in CharityAPI search: {str(e)}")
            return []

    def get_organization_by_ein(self, ein: str) -> Optional[Dict[str, Any]]:
        """
        Get organization details by EIN (Tax ID)
        
        Args:
            ein: Employer Identification Number (Tax ID)
            
        Returns:
            Organization dictionary or None if not found
        """
        try:
            # Clean EIN (remove dashes, spaces)
            clean_ein = ein.replace('-', '').replace(' ', '')
            
            url = f"{self.base_url}/api/organizations/{clean_ein}"
            
            logger.info(f"Looking up organization by EIN: {clean_ein}")
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                organization = data.get('data')
                
                if organization:
                    logger.info(f"Found organization: {organization.get('name', 'Unknown')}")
                    return organization
                else:
                    logger.info(f"No organization data for EIN: {clean_ein}")
                    return None
                    
            elif response.status_code == 404:
                logger.info(f"Organization not found for EIN: {clean_ein}")
                return None
                
            else:
                logger.error(f"CharityAPI lookup failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"CharityAPI request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in CharityAPI lookup: {str(e)}")
            return None

    def get_organizations_since(self, since_date: str) -> List[Dict[str, Any]]:
        """
        Get organizations added to IRS database since a specific date
        
        Args:
            since_date: Date in YYYY-MM-DD format
            
        Returns:
            List of organization dictionaries
        """
        try:
            url = f"{self.base_url}/api/organizations"
            params = {'since': since_date}
            
            logger.info(f"Getting organizations since: {since_date}")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                organizations = data.get('data', [])
                
                logger.info(f"Found {len(organizations)} new organizations since {since_date}")
                return organizations
                
            else:
                logger.error(f"CharityAPI bulk request failed: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"CharityAPI bulk request failed: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in CharityAPI bulk request: {str(e)}")
            return []

    def verify_public_charity(self, ein: str) -> bool:
        """
        Verify if an organization is a public charity (501c3 with tax-deductible status)
        
        Args:
            ein: Employer Identification Number
            
        Returns:
            True if public charity, False otherwise
        """
        try:
            organization = self.get_organization_by_ein(ein)
            
            if organization:
                # Check if it's a 501(c)(3) public charity
                classification = organization.get('classification')
                deductibility = organization.get('deductibility')
                
                # Classification 1000 = 501(c)(3), Deductibility 1 = tax-deductible
                is_public_charity = classification == 1000 and deductibility == 1
                
                logger.info(f"EIN {ein} public charity status: {is_public_charity}")
                return is_public_charity
                
            return False
            
        except Exception as e:
            logger.error(f"Error verifying public charity status: {str(e)}")
            return False

    def get_schema(self) -> Dict[str, Any]:
        """
        Get the data schema/field definitions from CharityAPI
        
        Returns:
            Schema dictionary with field explanations
        """
        try:
            url = f"{self.base_url}/api/organizations/schema"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"CharityAPI schema request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting CharityAPI schema: {str(e)}")
            return {}

    def test_connection(self) -> bool:
        """
        Test the CharityAPI connection and API key
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test with a known EIN (American Red Cross)
            test_ein = "530196605"
            result = self.get_organization_by_ein(test_ein)
            
            if result:
                logger.info("CharityAPI connection test successful")
                return True
            else:
                logger.warning("CharityAPI connection test failed - no data returned")
                return False
                
        except Exception as e:
            logger.error(f"CharityAPI connection test failed: {str(e)}")
            return False

    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get current rate limit information (if available in response headers)
        
        Returns:
            Dictionary with rate limit info
        """
        try:
            # Make a simple request to get headers
            url = f"{self.base_url}/api/organizations/530196605"  # American Red Cross
            response = requests.get(url, headers=self.headers, timeout=10)
            
            rate_limit_info = {}
            
            # Check for common rate limit headers
            if 'X-RateLimit-Limit' in response.headers:
                rate_limit_info['limit'] = response.headers['X-RateLimit-Limit']
            if 'X-RateLimit-Remaining' in response.headers:
                rate_limit_info['remaining'] = response.headers['X-RateLimit-Remaining']
            if 'X-RateLimit-Reset' in response.headers:
                rate_limit_info['reset'] = response.headers['X-RateLimit-Reset']
                
            return rate_limit_info
            
        except Exception as e:
            logger.error(f"Error getting rate limit info: {str(e)}")
            return {}

# Utility functions for NTEE codes and classifications

def get_ntee_categories() -> Dict[str, str]:
    """Get mapping of NTEE major group codes to category names"""
    return {
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

def get_classification_types() -> Dict[int, str]:
    """Get mapping of IRS classification codes to descriptions"""
    return {
        1000: '501(c)(3) Public Charity',
        2000: '501(c)(3) Private Foundation',
        3000: '501(c)(4) Social Welfare',
        4000: '501(c)(5) Labor Union',
        5000: '501(c)(6) Business League',
        6000: '501(c)(7) Social Club',
        7000: '501(c)(8) Fraternal Beneficiary',
        8000: '501(c)(9) Voluntary Employee Beneficiary',
        9000: '501(c)(10) Domestic Fraternal',
        10000: '501(c)(11) Teachers\' Retirement Fund',
        11000: '501(c)(12) Benevolent Life Insurance',
        12000: '501(c)(13) Cemetery Company',
        13000: '501(c)(14) Credit Union',
        14000: '501(c)(15) Mutual Insurance',
        15000: '501(c)(19) Veterans\' Organization'
    }

