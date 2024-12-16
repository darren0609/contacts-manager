from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QHBoxLayout, QMessageBox, QApplication
)
import asyncio

class DuplicateFinderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Duplicate Contacts")
        self.setMinimumWidth(800)
        self.duplicate_groups = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Add status/count label at the top with system-aware styling
        self.status_label = QLabel("Click 'Find Duplicates' to start search")
        self.status_label.setStyleSheet("""
            font-weight: bold;
            padding: 10px;
            background-color: palette(alternate-base);
            color: palette(text);
            border-radius: 5px;
            margin: 5px;
            border: 1px solid palette(mid);
        """)
        layout.addWidget(self.status_label)
        
        # Duplicates list
        self.duplicates_list = QListWidget()
        layout.addWidget(self.duplicates_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.find_button = QPushButton("Find Duplicates")
        self.find_button.clicked.connect(self._handle_find)
        button_layout.addWidget(self.find_button)
        
        self.merge_button = QPushButton("Merge Selected")
        self.merge_button.clicked.connect(self._handle_merge)
        self.merge_button.setEnabled(False)
        button_layout.addWidget(self.merge_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)

    def _handle_find(self):
        """Handle Find Duplicates button click"""
        self.find_button.setEnabled(False)
        self.merge_button.setEnabled(False)
        self.duplicates_list.clear()
        asyncio.create_task(self.find_duplicates())

    async def find_duplicates(self):
        """Find and display duplicate contacts."""
        try:
            self.status_label.setText("Searching for duplicates...")
            QApplication.processEvents()
            
            # Get duplicates from parent window
            duplicate_pairs = self.parent().duplicate_groups
            
            # Debug print the pairs
            print(f"Number of duplicate pairs: {len(duplicate_pairs)}")
            for i, (contact1, contact2, confidence, reasons) in enumerate(duplicate_pairs, 1):
                print(f"Pair {i}: {confidence*100:.1f}% confidence")
                print(f"  Reasons: {reasons}")
            
            # Update status with count
            total_pairs = len(duplicate_pairs)
            
            status_text = f"Found {total_pairs} potential duplicate pairs"
            print(f"Setting status text to: {status_text}")
            self.status_label.setText(status_text)
            
            # Clear and repopulate the list
            self.duplicates_list.clear()
            
            for i, (contact1, contact2, confidence, reasons) in enumerate(duplicate_pairs, 1):
                self.duplicates_list.addItem(
                    f"Duplicate Pair {i} (Confidence: {confidence*100:.1f}%):"
                )
                
                # First contact
                name1 = f"{contact1.first_name} {contact1.last_name}".strip() or "No Name"
                email1 = contact1.email or "No Email"
                phone1 = contact1.phone or "No Phone"
                source1 = contact1.source or "Unknown Source"
                self.duplicates_list.addItem(
                    f"    • [{source1}] {name1} | {email1} | {phone1}"
                )
                
                # Second contact
                name2 = f"{contact2.first_name} {contact2.last_name}".strip() or "No Name"
                email2 = contact2.email or "No Email"
                phone2 = contact2.phone or "No Phone"
                source2 = contact2.source or "Unknown Source"
                self.duplicates_list.addItem(
                    f"    • [{source2}] {name2} | {email2} | {phone2}"
                )
                
                # Add reasons for the match
                if reasons:
                    self.duplicates_list.addItem(f"    Matched because: {', '.join(reasons)}")
                
                self.duplicates_list.addItem("")  # Add spacing between groups
            
            self.find_button.setEnabled(True)
            if duplicate_pairs:
                self.merge_button.setEnabled(True)

        except Exception as e:
            self.status_label.setText("Error finding duplicates")
            QMessageBox.critical(self, "Error", f"Failed to find duplicates: {str(e)}")
            self.find_button.setEnabled(True)

    def _handle_merge(self):
        """Handle Merge Selected button click"""
        # ... existing merge handling code ...