from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt

class DuplicateFinderDialog(QDialog):
    def __init__(self, parent=None, duplicates=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicate Contacts")
        self.setMinimumWidth(600)
        self.duplicates = duplicates or []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add explanation label
        label = QLabel(
            "The following contacts might be duplicates. "
            "Select a pair to merge them."
        )
        layout.addWidget(label)
        
        # Create list widget for duplicates
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._handle_merge)
        
        # Add duplicate pairs to list
        for contact1, contact2, confidence, reasons in self.duplicates:
            item = QListWidgetItem()
            widget = self._create_duplicate_item(contact1, contact2, confidence, reasons)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
        
        layout.addWidget(self.list_widget)
        
        # Add buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _create_duplicate_item(self, contact1, contact2, confidence, reasons):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Contact details
        details = QHBoxLayout()
        
        # First contact
        contact1_label = QLabel(
            f"Contact 1:\n"
            f"{contact1.first_name} {contact1.last_name}\n"
            f"{contact1.email}\n"
            f"{contact1.phone}"
        )
        details.addWidget(contact1_label)
        
        # Confidence and reasons
        middle_label = QLabel(
            f"\nConfidence: {confidence:.0%}\n"
            f"Reasons:\n" + "\n".join(f"• {r}" for r in reasons)
        )
        details.addWidget(middle_label)
        
        # Second contact
        contact2_label = QLabel(
            f"Contact 2:\n"
            f"{contact2.first_name} {contact2.last_name}\n"
            f"{contact2.email}\n"
            f"{contact2.phone}"
        )
        details.addWidget(contact2_label)
        
        layout.addLayout(details)
        
        # Add merge button
        merge_button = QPushButton("Merge These Contacts")
        merge_button.clicked.connect(
            lambda: self.parent()._show_merge_dialog_for_contacts(contact1, contact2)
        )
        layout.addWidget(merge_button)
        
        return widget
    
    def _handle_merge(self, item):
        """Handle double-click on duplicate pair"""
        widget = self.list_widget.itemWidget(item)
        if widget:
            widget.findChild(QPushButton).click() 