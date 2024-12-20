from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QLabel, QMessageBox, QApplication
)
from PySide6.QtCore import Qt

class LoginDialog(QDialog):
    def __init__(self, provider_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{provider_name} Login")
        self.setModal(True)
        self._setup_ui(provider_name)
        
    def _setup_ui(self, provider_name):
        layout = QVBoxLayout(self)
        
        # Add provider logo or icon
        info_label = QLabel(f"Please enter your {provider_name} credentials:")
        layout.addWidget(info_label)
        
        # Create form
        form = QFormLayout()
        
        self.email = QLineEdit()
        self.email.setPlaceholderText("email@yahoo.com")
        form.addRow("Email:", self.email)
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Password or App Password")
        form.addRow("Password:", self.password)
        
        layout.addLayout(form)
        
        # Add help text for app passwords
        help_text = QLabel(
            "Note: If you have 2FA enabled, you'll need to use an App Password.\n"
            "You can generate one in your Yahoo Account Security settings.\n\n"
            "To generate an App Password:\n"
            "1. Go to Yahoo Account Security settings\n"
            "2. Click on 'Generate app password'\n"
            "3. Select 'Other app' and give it a name\n"
            "4. Use the generated password here"
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Add buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Set minimum width
        self.setMinimumWidth(400)
    
    def show_status(self, message: str, is_error: bool = False):
        """Show status message"""
        self.status_label.setText(message)
        if is_error:
            self.status_label.setStyleSheet("color: red")
        else:
            self.status_label.setStyleSheet("color: green")
        QApplication.processEvents()
    
    def validate_and_accept(self):
        """Validate inputs before accepting"""
        if not self.email.text().strip():
            self.show_status("Email is required", True)
            return
        if not self.password.text().strip():
            self.show_status("Password is required", True)
            return
        
        self.show_status("Validating credentials...")
        self.button_box.setEnabled(False)
        self.accept()
    
    def get_credentials(self):
        """Get the entered credentials"""
        return {
            'username': self.email.text().strip(),
            'password': self.password.text().strip()
        } 