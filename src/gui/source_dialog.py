from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QLabel, QComboBox
)

class SourceSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Contact Source")
        self.setModal(True)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # Source type selection
        self.source_type = QComboBox()
        self.source_type.addItems(['Gmail', 'CSV Import'])
        form.addRow("Source Type:", self.source_type)
        
        # Source name input
        self.source_name = QLineEdit()
        self.source_name.setPlaceholderText("e.g., Work Gmail, Personal Contacts")
        form.addRow("Source Name:", self.source_name)
        
        layout.addLayout(form)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def validate_and_accept(self):
        if not self.source_name.text().strip():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Please enter a source name")
            return
        self.accept()
    
    def get_source_info(self):
        return {
            'type': self.source_type.currentText(),
            'name': self.source_name.text().strip()
        } 