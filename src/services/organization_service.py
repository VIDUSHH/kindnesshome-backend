"""
Organization service for KindnessHome platform
Business logic layer for managing charitable organization data
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Import our custom modules (these will be added to the backend)
from .charity_api_service import CharityAPIService
from ..models.organization import Organization, OrganizationCache

logger = logging.getLogger(__name__)

class OrganizationService:
    """Service for managing charitable organization data"""
    
    def __init__(self, charity_api_key: str = None):
        self.charity_api = CharityAPIService(charity_api_key)
        self.cache = OrganizationCache()
        
    def search_organizations(self, 
                           query: str, 
                           state: str = None, 
                           city: str = None,
                           category: str = None,
                           limit: int = 20,
                           use_cache: bool = True) -> List[Organization]:
        """
        Search for organizations with caching support
        
        Args:
            query: Search term for organization name
            state: Filter by state code (optional)
            city: Filter by city (optional) 
            category: Filter by NTEE category (optional)
            limit: Maximum number of results
            use_cache: Whether to check cache first
            
        Returns:
            List of Organization objects
        """
        try:
            organizations = []
            
            # First, try cache if enabled
            if use_cache:
                cached_results = self.cache.search_organizations(query, state, limit)
                if cached_results:
                    logger.info(f"Found {len(cached_results)} cached results for: {query}")
                    organizations.extend(cached_results)
                    
                    # If we have enough cached results, return them
                    if len(organizations) >= limit:
                        return organizations[:limit]
            
            # Search CharityAPI for additional results
            try:
                api_results = self.charity_api.search_organizations(
                    query=query,
                    city=city,
                    state=state,
                    limit=limit - len(organizations)
                )
                
                for org_data in api_results:
                    org = Organization.from_charity_api(org_data)
                    
                    # Filter by category if specified
                    if category and org.ntee_code:
                        if not org.ntee_code.upper().startswith(category.upper()):
                            continue
                    
                    organizations.append(org)
                    
                    # Cache the organization for future searches
                    self.cache.save_organization(org)
                    
                logger.info(f"Found {len(api_results)} API results for: {query}")
                
            except Exception as e:
                logger.error(f"CharityAPI search failed: {str(e)}")
                # Continue with cached results if API fails
            
            # Remove duplicates (by EIN) and limit results
            seen_eins = set()
            unique_orgs = []
            
            for org in organizations:
                if org.ein not in seen_eins:
                    seen_eins.add(org.ein)
                    unique_orgs.append(org)
                    
                if len(unique_orgs) >= limit:
                    break
            
            return unique_orgs
            
        except Exception as e:
            logger.error(f"Error in organization search: {str(e)}")
            return []

    def get_organization_by_ein(self, ein: str, use_cache: bool = True) -> Optional[Organization]:
        """
        Get organization by EIN with caching support
        
        Args:
            ein: Employer Identification Number
            use_cache: Whether to check cache first
            
        Returns:
            Organization object or None if not found
        """
        try:
            # Clean EIN
            clean_ein = ein.replace('-', '').replace(' ', '')
            
            # Check cache first if enabled
            if use_cache:
                cached_org = self.cache.get_organization(clean_ein)
                if cached_org:
                    # Check if cache is still fresh (30 days)
                    if cached_org.last_updated and \
                       (datetime.utcnow() - cached_org.last_updated).days < 30:
                        logger.info(f"Found cached organization: {cached_org.name}")
                        self.cache.increment_search_count(clean_ein)
                        return cached_org
            
            # Fetch from CharityAPI
            try:
                org_data = self.charity_api.get_organization_by_ein(clean_ein)
                
                if org_data:
                    org = Organization.from_charity_api(org_data)
                    
                    # Cache the organization
                    self.cache.save_organization(org)
                    self.cache.increment_search_count(clean_ein)
                    
                    logger.info(f"Found organization via API: {org.name}")
                    return org
                else:
                    logger.info(f"Organization not found for EIN: {clean_ein}")
                    return None
                    
            except Exception as e:
                logger.error(f"CharityAPI lookup failed: {str(e)}")
                
                # Return cached version even if stale, if available
                if use_cache:
                    cached_org = self.cache.get_organization(clean_ein)
                    if cached_org:
                        logger.warning(f"Returning stale cached data for EIN: {clean_ein}")
                        return cached_org
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting organization by EIN: {str(e)}")
            return None

    def verify_organization(self, ein: str) -> Dict[str, Any]:
        """
        Verify organization's charitable status and tax-deductible eligibility
        
        Args:
            ein: Employer Identification Number
            
        Returns:
            Dictionary with verification results
        """
        try:
            org = self.get_organization_by_ein(ein)
            
            if not org:
                return {
                    'verified': False,
                    'exists': False,
                    'message': 'Organization not found in IRS database'
                }
            
            verification = {
                'verified': True,
                'exists': True,
                'ein': org.ein,
                'name': org.name,
                'is_public_charity': org.is_public_charity(),
                'is_tax_deductible': org.is_tax_deductible(),
                'status': org.status,
                'classification': org.classification,
                'deductibility': org.deductibility
            }
            
            # Add status message
            if org.is_public_charity():
                verification['message'] = 'Verified 501(c)(3) public charity - donations are tax-deductible'
            elif org.is_tax_deductible():
                verification['message'] = 'Tax-exempt organization - donations may be tax-deductible'
            else:
                verification['message'] = 'Tax-exempt organization - donations may not be tax-deductible'
            
            return verification
            
        except Exception as e:
            logger.error(f"Error verifying organization: {str(e)}")
            return {
                'verified': False,
                'exists': False,
                'message': 'Error verifying organization status'
            }

    def get_popular_organizations(self, limit: int = 20) -> List[Organization]:
        """
        Get most popular/searched organizations
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of popular Organization objects
        """
        try:
            return self.cache.get_popular_organizations(limit)
        except Exception as e:
            logger.error(f"Error getting popular organizations: {str(e)}")
            return []

    def get_organizations_by_category(self, category: str, limit: int = 20) -> List[Organization]:
        """
        Get organizations by NTEE category
        
        Args:
            category: NTEE major group code (A-Z)
            limit: Maximum number of results
            
        Returns:
            List of Organization objects in the category
        """
        try:
            # This is a simplified implementation
            # In a full implementation, you might want to pre-populate
            # popular organizations by category
            
            # For now, we'll search for organizations with the category code
            # This could be enhanced with category-specific searches
            
            category_names = {
                'A': 'arts culture humanities',
                'B': 'education school university',
                'C': 'environment animals wildlife',
                'D': 'animal welfare pets',
                'E': 'health medical hospital',
                'F': 'mental health crisis',
                'G': 'disease medical research',
                'H': 'medical research',
                'I': 'crime legal justice',
                'J': 'employment job training',
                'K': 'food nutrition hunger',
                'L': 'housing shelter homeless',
                'M': 'disaster relief emergency',
                'N': 'recreation sports athletics',
                'O': 'youth development children',
                'P': 'human services social',
                'Q': 'international foreign',
                'R': 'civil rights advocacy',
                'S': 'community development',
                'T': 'philanthropy foundation',
                'U': 'science technology research',
                'V': 'social science research',
                'W': 'public benefit society',
                'X': 'religion religious',
                'Y': 'membership benefit',
                'Z': 'unknown'
            }
            
            search_term = category_names.get(category.upper(), 'charity')
            return self.search_organizations(search_term, category=category, limit=limit)
            
        except Exception as e:
            logger.error(f"Error getting organizations by category: {str(e)}")
            return []

    def get_categories(self) -> List[Dict[str, Any]]:
        """
        Get list of available organization categories (NTEE codes)
        
        Returns:
            List of category dictionaries
        """
        from .charity_api_service import get_ntee_categories
        
        categories = []
        ntee_map = get_ntee_categories()
        
        for code, name in ntee_map.items():
            categories.append({
                'code': code,
                'name': name,
                'description': f"Organizations focused on {name.lower()}"
            })
        
        return categories

    def sync_popular_organizations(self, limit: int = 100):
        """
        Background task to sync popular organizations from CharityAPI
        This could be run periodically to keep cache fresh
        
        Args:
            limit: Number of organizations to sync
        """
        try:
            logger.info("Starting popular organizations sync...")
            
            # Get a list of well-known charity EINs to pre-populate
            # This is a simplified approach - in production you might
            # use a curated list or analyze search patterns
            
            well_known_eins = [
                "530196605",  # American Red Cross
                "131624016",  # Salvation Army
                "541760264",  # Doctors Without Borders
                "237327031",  # United Way
                "521382983",  # Habitat for Humanity
                "363271564",  # St. Jude Children's Research Hospital
                "237327031",  # Goodwill Industries
                "131740204",  # YMCA
                "237327031",  # Boys & Girls Clubs
                "521382983"   # Feeding America
            ]
            
            synced_count = 0
            
            for ein in well_known_eins:
                try:
                    org = self.get_organization_by_ein(ein, use_cache=False)
                    if org:
                        synced_count += 1
                        logger.info(f"Synced: {org.name}")
                        
                except Exception as e:
                    logger.error(f"Error syncing EIN {ein}: {str(e)}")
                    continue
                    
                if synced_count >= limit:
                    break
            
            logger.info(f"Completed sync of {synced_count} popular organizations")
            
        except Exception as e:
            logger.error(f"Error in popular organizations sync: {str(e)}")

    def test_api_connection(self) -> Dict[str, Any]:
        """
        Test the CharityAPI connection and return status
        
        Returns:
            Dictionary with connection test results
        """
        try:
            is_connected = self.charity_api.test_connection()
            rate_limit_info = self.charity_api.get_rate_limit_info()
            
            return {
                'connected': is_connected,
                'api_key_valid': bool(self.charity_api.api_key),
                'rate_limit': rate_limit_info,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing API connection: {str(e)}")
            return {
                'connected': False,
                'api_key_valid': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

