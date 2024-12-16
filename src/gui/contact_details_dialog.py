from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class ContactDetailsDialog(QDialog):
    def __init__(self, contact_data, parent=None):
        super().__init__(parent)
        self.contact_data = contact_data
        self.setWindowTitle("Contact Details")
        self.setMinimumWidth(500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create scroll area for potentially long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        
        # Header with name
        name_layout = QHBoxLayout()
        name = f"{self.contact_data.get('first_name', '')} {self.contact_data.get('last_name', '')}".strip()
        name_label = QLabel(name or "No Name")
        name_font = QFont()
        name_font.setPointSize(16)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_layout.addWidget(name_label)
        content_layout.addLayout(name_layout)
        
        # Source information
        source_label = QLabel(f"Source: {self.contact_data.get('source', 'Unknown')}")
        source_label.setStyleSheet("color: gray;")
        content_layout.addWidget(source_label)
        
        content_layout.addSpacing(20)
        
        # Contact details grid
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)  # Make value column stretch
        row = 0
        
        # Basic contact information
        if self.contact_data.get('email'):
            self._add_field(grid, row, "Email:", self.contact_data['email'])
            row += 1
        
        if self.contact_data.get('phone'):
            self._add_field(grid, row, "Phone:", self.contact_data['phone'])
            row += 1
        
        # Additional metadata fields
        metadata = self.contact_data.get('metadata', {})
        if metadata:
            content_layout.addSpacing(10)
            section_label = QLabel("Additional Information")
            section_font = QFont()
            section_font.setBold(True)
            section_label.setFont(section_font)
            content_layout.addWidget(section_label)
            
            # Process metadata fields
            for key, value in self._process_metadata(metadata).items():
                if value:  # Only show non-empty values
                    self._add_field(grid, row, f"{key}:", value)
                    row += 1
        
        content_layout.addLayout(grid)
        content_layout.addStretch()
        
        # Add scroll area to main layout
        layout.addWidget(scroll)
        
        # Add buttons
        button_layout = QHBoxLayout()
        edit_button = QPushButton("Edit")
        edit_button.clicked.connect(self._edit_contact)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(edit_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def _add_field(self, grid, row, label_text, value_text):
        """Add a field to the grid layout"""
        label = QLabel(label_text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet("font-weight: bold;")
        
        value = QLabel(str(value_text))
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        grid.addWidget(label, row, 0)
        grid.addWidget(value, row, 1)
    
    def _process_metadata(self, metadata):
        """Process metadata into user-friendly format"""
        processed = {}
        
        # Handle different metadata formats based on source
        if isinstance(metadata, dict):
            # Process additional phone numbers
            additional_phones = metadata.get('additional_phones', [])
            if additional_phones:
                phone_lines = []
                for phone in additional_phones:
                    if isinstance(phone, dict):
                        phone_lines.append(f"{phone['type']}: {phone['number']}")
                    else:
                        phone_lines.append(f"Additional: {phone}")
                if phone_lines:
                    processed['Additional Phones'] = '\n'.join(phone_lines)
            
            # Process addresses from Google format
            addresses = metadata.get('addresses', [])
            if addresses:
                address_lines = []
                for addr in addresses:
                    addr_type = addr.get('type', 'Other')
                    formatted = addr.get('formattedValue', '')  # Google's formatted address
                    if formatted:
                        address_lines.append(f"{addr_type}:\n{formatted}")
                    else:
                        # Fallback to building address from components
                        parts = []
                        if addr.get('streetAddress'):
                            parts.append(addr['streetAddress'])
                        if addr.get('city'):
                            parts.append(addr['city'])
                        if addr.get('region'):  # State/Province
                            parts.append(addr['region'])
                        if addr.get('postalCode'):
                            parts.append(addr['postalCode'])
                        if addr.get('country'):
                            parts.append(addr['country'])
                        if parts:
                            address_lines.append(f"{addr_type}:\n{', '.join(parts)}")
                
                if address_lines:
                    processed['Addresses'] = '\n\n'.join(address_lines)
            
            # Process other common fields
            field_mappings = {
                'company': 'Company',
                'title': 'Job Title',
                'department': 'Department',
                'birthday': 'Birthday',
                'notes': 'Notes',
                'website': 'Website',
                'nickname': 'Nickname'
            }
            
            for key, label in field_mappings.items():
                if key in metadata and metadata[key]:
                    processed[label] = metadata[key]
            
            # Handle multiple emails
            additional_emails = metadata.get('additional_emails', [])
            if additional_emails:
                email_lines = []
                for email in additional_emails:
                    if isinstance(email, dict):
                        email_lines.append(f"{email['type']}: {email['value']}")
                    else:
                        email_lines.append(str(email))
                if email_lines:
                    processed['Additional Emails'] = '\n'.join(email_lines)
            
            # Handle websites
            websites = metadata.get('websites', [])
            if websites:
                website_lines = []
                for site in websites:
                    site_type = site.get('type', 'Website')
                    url = site.get('value', '')
                    if url:
                        website_lines.append(f"{site_type}: {url}")
                if website_lines:
                    processed['Websites'] = '\n'.join(website_lines)
        
        return processed
    
    def _edit_contact(self):
        """Open the edit contact dialog"""
        from src.gui.contact_dialog import ContactDialog
        dialog = ContactDialog(self, self.contact_data)
        if dialog.exec_():
            updated_data = dialog.get_contact_data()
            # Signal the parent window to update the contact
            self.parent()._update_contact(self.contact_data['id'], updated_data)
            self.accept() 