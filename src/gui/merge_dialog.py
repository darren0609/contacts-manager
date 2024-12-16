from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QLabel, QGridLayout,
    QRadioButton, QButtonGroup
)

class MergeContactsDialog(QDialog):
    def __init__(self, parent=None, contact1=None, contact2=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Contacts")
        self.contact1 = contact1
        self.contact2 = contact2
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create grid for comparing fields
        grid = QGridLayout()
        
        # Headers
        grid.addWidget(QLabel("Field"), 0, 0)
        grid.addWidget(QLabel("Contact 1"), 0, 1)
        grid.addWidget(QLabel("Contact 2"), 0, 2)
        
        # Fields to merge
        fields = [
            ('first_name', "First Name"),
            ('last_name', "Last Name"),
            ('email', "Email"),
            ('phone', "Phone")
        ]
        
        self.field_groups = {}
        
        for row, (field, label) in enumerate(fields, 1):
            grid.addWidget(QLabel(label), row, 0)
            
            # Create radio buttons for each field
            group = QButtonGroup(self)
            self.field_groups[field] = group
            
            # Contact 1 value
            value1 = self.contact1[field]
            btn1 = QRadioButton(value1 or "(empty)")
            btn1.setProperty("value", value1)
            group.addButton(btn1)
            grid.addWidget(btn1, row, 1)
            
            # Contact 2 value
            value2 = self.contact2[field]
            btn2 = QRadioButton(value2 or "(empty)")
            btn2.setProperty("value", value2)
            group.addButton(btn2)
            grid.addWidget(btn2, row, 2)
            
            # Select non-empty value by default
            if value1 and not value2:
                btn1.setChecked(True)
            elif value2 and not value1:
                btn2.setChecked(True)
            elif value1:  # Both have values, select first one
                btn1.setChecked(True)
        
        layout.addLayout(grid)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_merged_data(self):
        """Get the merged contact data based on selections"""
        merged = {}
        for field, group in self.field_groups.items():
            selected = group.checkedButton()
            merged[field] = selected.property("value") if selected else ""
        return merged 