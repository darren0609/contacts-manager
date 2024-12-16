from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QMessageBox
)

class ContactDialog(QDialog):
    def __init__(self, parent=None, contact=None):
        super().__init__(parent)
        self.setWindowTitle("Contact" if contact else "New Contact")
        self.contact = contact
        self._setup_ui()
        
        if contact:
            self._load_contact(contact)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Create input fields
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        
        # Add fields to form
        form.addRow("First Name:", self.first_name)
        form.addRow("Last Name:", self.last_name)
        form.addRow("Email:", self.email)
        form.addRow("Phone:", self.phone)
        
        layout.addLayout(form)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_contact(self, contact):
        """Load contact data into fields"""
        self.first_name.setText(contact.first_name or "")
        self.last_name.setText(contact.last_name or "")
        self.email.setText(contact.email or "")
        self.phone.setText(contact.phone or "")
    
    def get_contact_data(self):
        """Get the contact data from fields"""
        return {
            'first_name': self.first_name.text(),
            'last_name': self.last_name.text(),
            'email': self.email.text(),
            'phone': self.phone.text()
        } 