from typing import List, Optional
from core.contact_manager import ContactSource, Contact
import csv
from PySide6.QtWidgets import QFileDialog, QMessageBox
import uuid
import logging
from datetime import datetime
import os

class CSVContactSource(ContactSource):
    def __init__(self, provider='yahoo'):
        """Initialize CSV contact source."""
        self.provider = provider
        self.last_file = None
        
        # Create logs directory if it doesn't exist
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Setup logging with more detailed format
        log_filename = os.path.join(logs_dir, f'csv_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*80)
        self.logger.info("CSV Import Session Started")
        self.logger.info("="*80)
    
    async def fetch_contacts(self) -> List[Contact]:
        """Import contacts from a CSV file."""
        try:
            self.logger.info("-"*40)
            self.logger.info(f"Starting {self.provider} CSV import")
            self.logger.info("-"*40)
            contacts = []
            
            # Show file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Import Contacts from CSV",
                "",
                "CSV Files (*.csv);;All Files (*.*)"
            )
            
            if not file_path:
                self.logger.warning("Import cancelled - No file selected")
                return contacts
            
            self.last_file = file_path
            self.logger.info(f"Selected file: {file_path}")
            
            # Read CSV file
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Log headers
                headers = reader.fieldnames
                self.logger.info("CSV Headers:")
                for i, header in enumerate(headers):
                    self.logger.info(f"  {i+1}. {header}")
                
                # Map headers
                header_maps = {
                    'first_name': ['First Name', 'FirstName', 'Given Name', 'GivenName', 'First', 'Given'],
                    'last_name': ['Last Name', 'LastName', 'Family Name', 'FamilyName', 'Surname', 'Last'],
                    'email': ['Email', 'E-mail', 'Email Address', 'Primary Email', 'E-Mail 1 - Value'],
                    'phone': ['Phone', 'Phone Number', 'Mobile', 'Primary Phone', 'Mobile Phone', 
                             'Home Phone', 'Business Phone', 'Phone 1 - Value', 'Mobile Phone 1']
                }
                
                # Find the actual column names in the CSV
                field_mapping = {}
                self.logger.info("\nField Mapping Results:")
                for field, variations in header_maps.items():
                    for header in headers:
                        if any(var.lower() == header.lower() for var in variations):
                            field_mapping[field] = header
                            self.logger.info(f"  {field:10} -> {header}")
                            break
                    if field not in field_mapping:
                        self.logger.warning(f"  {field:10} -> No match found")
                
                if not field_mapping:
                    self.logger.error("No valid column mappings found!")
                    self.logger.error(f"Available headers: {headers}")
                    raise ValueError("Could not identify any valid columns in the CSV file")
                
                # Process rows
                row_num = 0
                for row in reader:
                    row_num += 1
                    try:
                        self.logger.info(f"\nProcessing Row {row_num}:")
                        self.logger.debug("Raw data:")
                        for key, value in row.items():
                            self.logger.debug(f"  {key:20}: {value}")
                        
                        # Extract phone numbers
                        phone = None
                        additional_phones = []
                        phone_fields = {
                            'mobile': ['Mobile', 'Cell', 'Mobile Phone'],
                            'work': ['Work', 'Business', 'Work Phone', 'Business Phone'],
                            'home': ['Home', 'Home Phone'],
                            'other': ['Other', 'Other Phone', 'Phone']
                        }
                        
                        # First try to find a mobile number as primary
                        for key in row.keys():
                            if row[key] and row[key].strip():  # Check if there's a value
                                if any(mobile_key.lower() in key.lower() for mobile_key in phone_fields['mobile']):
                                    phone = row[key]
                                    self.logger.info(f"Found primary (mobile) phone: {phone}")
                                    break
                        
                        # If no mobile, try work number
                        if not phone:
                            for key in row.keys():
                                if row[key] and row[key].strip():  # Check if there's a value
                                    if any(work_key.lower() in key.lower() for work_key in phone_fields['work']):
                                        phone = row[key]
                                        self.logger.info(f"Found primary (work) phone: {phone}")
                                        break
                        
                        # If still no number, try any other phone field
                        if not phone:
                            for key in row.keys():
                                if row[key] and row[key].strip():  # Check if there's a value
                                    if any(phone_key.lower() in key.lower() for phone_key in ['phone', 'mobile', 'cell', 'work', 'home']):
                                        phone = row[key]
                                        self.logger.info(f"Found primary phone from {key}: {phone}")
                                        break
                        
                        # Collect ALL additional phone numbers
                        for key in row.keys():
                            if row[key] and row[key].strip():  # Check if there's a value
                                if any(phone_key.lower() in key.lower() for phone_key in ['phone', 'mobile', 'cell', 'work', 'home']):
                                    current_number = row[key].strip()
                                    if current_number != phone:  # Don't add the primary phone again
                                        additional_phones.append({
                                            'type': key,
                                            'number': current_number
                                        })
                                        self.logger.info(f"Found additional phone ({key}): {current_number}")
                        
                        # Create contact
                        contact = Contact(
                            id=f"csv_{self.provider}_{uuid.uuid4()}",
                            first_name=row.get(field_mapping.get('first_name', ''), '').strip(),
                            last_name=row.get(field_mapping.get('last_name', ''), '').strip(),
                            email=row.get(field_mapping.get('email', ''), '').strip(),
                            phone=phone,
                            source=f"csv_{self.provider}",
                            source_id=str(uuid.uuid4()),
                            metadata={
                                'original_row': row,
                                'additional_phones': additional_phones
                            }
                        )
                        
                        self.logger.info("Created contact:")
                        self.logger.info(f"  Name: {contact.first_name} {contact.last_name}")
                        self.logger.info(f"  Email: {contact.email}")
                        self.logger.info(f"  Phone: {contact.phone}")
                        if additional_phones:
                            self.logger.info(f"  Additional phones: {additional_phones}")
                        
                        contacts.append(contact)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing row {row_num}:")
                        self.logger.error(f"  Error: {str(e)}")
                        self.logger.error(f"  Row data: {row}")
                        continue
            
            self.logger.info("\nImport Summary:")
            self.logger.info(f"Total rows processed: {row_num}")
            self.logger.info(f"Contacts created: {len(contacts)}")
            self.logger.info("="*40)
            
            return contacts
            
        except Exception as e:
            self.logger.error("Import failed with error:")
            self.logger.error(str(e))
            self.logger.error(traceback.format_exc())
            raise
    
    async def push_contacts(self, contacts: List[Contact]) -> bool:
        """Export contacts to CSV file."""
        try:
            # Show save file dialog
            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Export Contacts to CSV",
                "",
                "CSV Files (*.csv);;All Files (*.*)"
            )
            
            if not file_path:
                return False
            
            # Write contacts to CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write headers
                writer.writerow(['First Name', 'Last Name', 'Email', 'Phone'])
                
                # Write contacts
                for contact in contacts:
                    writer.writerow([
                        contact.first_name or '',
                        contact.last_name or '',
                        contact.email or '',
                        contact.phone or ''
                    ])
            
            QMessageBox.information(
                None,
                "Export Successful",
                f"Successfully exported {len(contacts)} contacts to CSV file."
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export contacts: {str(e)}")
            QMessageBox.critical(
                None,
                "Export Error",
                f"Failed to export contacts: {str(e)}"
            )
            return False 