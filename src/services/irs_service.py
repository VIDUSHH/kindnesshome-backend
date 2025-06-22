import os
import requests
import pandas as pd
import json
from datetime import datetime
from src.models.database import db
from src.models.organization import Organization, NTEECode, Category
from flask import current_app

class IRSDataService:
    """Service for integrating with IRS tax-exempt organization data"""
    
    def __init__(self):
        self.irs_base_url = "https://www.irs.gov/pub/irs-soi"
        self.compliancely_api_key = os.getenv('COMPLIANCELY_API_KEY')
        self.compliancely_base_url = "https://api.compliancely.com/v1"
    
    def download_irs_bulk_data(self, state='all'):
        """Download IRS bulk data for organizations"""
        try:
            if state == 'all':
                # Download Publication 78 data (all eligible organizations)
                url = f"{self.irs_base_url}/eo_pub78_data.zip"
            else:
                # Download state-specific data
                url = f"{self.irs_base_url}/eo_{state.lower()}.zip"
            
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            filename = f"irs_data_{state}_{datetime.now().strftime('%Y%m%d')}.zip"
            filepath = os.path.join('/tmp', filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
        except Exception as e:
            current_app.logger.error(f"Error downloading IRS data: {str(e)}")
            return None
    
    def process_irs_csv_data(self, csv_file_path):
        """Process IRS CSV data and update database"""
        try:
            # Read CSV with proper encoding
            df = pd.read_csv(csv_file_path, encoding='latin-1', low_memory=False)
            
            # Expected columns in IRS data
            required_columns = ['EIN', 'NAME', 'CITY', 'STATE', 'ZIP', 'NTEE_CD', 'SUBSECTION']
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                current_app.logger.warning(f"Missing columns: {missing_columns}")
            
            processed_count = 0
            
            for index, row in df.iterrows():
                try:
                    # Extract organization data
                    ein = str(row.get('EIN', '')).zfill(9)  # Ensure 9 digits
                    name = row.get('NAME', '').strip()
                    city = row.get('CITY', '').strip()
                    state = row.get('STATE', '').strip()
                    zip_code = str(row.get('ZIP', '')).strip()
                    ntee_code = row.get('NTEE_CD', '').strip()
                    subsection = row.get('SUBSECTION', '').strip()
                    
                    # Skip if essential data is missing
                    if not ein or not name or len(ein) != 9:
                        continue
                    
                    # Check if organization already exists
                    existing_org = Organization.query.filter_by(ein=ein).first()
                    
                    if existing_org:
                        # Update existing organization
                        existing_org.name = name
                        existing_org.city = city
                        existing_org.state = state
                        existing_org.zip_code = zip_code
                        existing_org.ntee_code = ntee_code
                        existing_org.is_verified = True
                        existing_org.verification_date = datetime.utcnow()
                        existing_org.updated_at = datetime.utcnow()
                    else:
                        # Create new organization
                        new_org = Organization(
                            ein=ein,
                            name=name,
                            city=city,
                            state=state,
                            zip_code=zip_code,
                            ntee_code=ntee_code,
                            is_verified=True,
                            verification_date=datetime.utcnow(),
                            tax_exempt_status='501(c)(3)' if subsection == '03' else f'501(c)({subsection})',
                            description=f"Tax-exempt organization verified through IRS database."
                        )
                        db.session.add(new_org)
                    
                    processed_count += 1
                    
                    # Commit in batches to avoid memory issues
                    if processed_count % 1000 == 0:
                        db.session.commit()
                        current_app.logger.info(f"Processed {processed_count} organizations")
                
                except Exception as e:
                    current_app.logger.error(f"Error processing row {index}: {str(e)}")
                    continue
            
            # Final commit
            db.session.commit()
            current_app.logger.info(f"Successfully processed {processed_count} organizations")
            return processed_count
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing IRS CSV data: {str(e)}")
            return 0
    
    def verify_organization_with_compliancely(self, ein):
        """Verify organization using Compliancely API"""
        if not self.compliancely_api_key:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.compliancely_api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.compliancely_base_url}/tax-exempt/verify"
            data = {'ein': ein}
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            current_app.logger.error(f"Error verifying EIN {ein} with Compliancely: {str(e)}")
            return None
    
    def validate_ein_format(self, ein):
        """Validate EIN format (XX-XXXXXXX)"""
        import re
        
        # Remove any formatting
        clean_ein = re.sub(r'[^0-9]', '', ein)
        
        # Check if it's 9 digits
        if len(clean_ein) != 9:
            return False
        
        # Check if it starts with valid prefixes
        valid_prefixes = [
            '01', '02', '03', '04', '05', '06', '10', '11', '12', '13', '14', '15', '16',
            '20', '21', '22', '23', '24', '25', '26', '27', '30', '31', '32', '33', '34',
            '35', '36', '37', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47',
            '48', '50', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '61',
            '62', '63', '64', '65', '66', '67', '68', '71', '72', '73', '74', '75', '76',
            '77', '80', '81', '82', '83', '84', '85', '86', '87', '88', '90', '91', '92',
            '93', '94', '95', '98', '99'
        ]
        
        return clean_ein[:2] in valid_prefixes
    
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
    
    def sync_organization_data(self):
        """Sync organization data with IRS database"""
        try:
            current_app.logger.info("Starting IRS data synchronization")
            
            # Download latest IRS data
            data_file = self.download_irs_bulk_data()
            if not data_file:
                return False
            
            # Process the data
            processed_count = self.process_irs_csv_data(data_file)
            
            # Clean up temporary file
            if os.path.exists(data_file):
                os.remove(data_file)
            
            current_app.logger.info(f"IRS data sync completed. Processed {processed_count} organizations")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error in IRS data sync: {str(e)}")
            return False

