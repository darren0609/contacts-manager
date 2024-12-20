from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QLabel, QMessageBox, QHeaderView, QApplication,
    QSizePolicy, QLineEdit, QComboBox, QMenu,
    QToolButton, QDialog, QFormLayout, QCheckBox,
    QDialogButtonBox, QListWidget, QRadioButton,
    QButtonGroup
)
from PySide6.QtCore import Qt, QSize, QTimer, QSettings
from PySide6.QtGui import QKeySequence, QAction
import asyncio
from src.core.contact_manager import ContactManager, Contact
from src.sources.gmail_source import GmailContactSource
from src.db.database import init_db
from sqlalchemy import select, delete
import re
from src.gui.contact_dialog import ContactDialog
from src.gui.merge_dialog import MergeContactsDialog
from src.gui.duplicate_finder_dialog import DuplicateFinderDialog
from src.core.commands import MergeCommand
from src.core.command_manager import CommandManager
from src.sources.carddav_source import CardDAVSource
from src.sources.imap_source import IMAPContactSource
from src.sources.yahoo_source import YahooContactSource
from src.sources.csv_source import CSVContactSource
from src.gui.source_dialog import SourceSelectionDialog
from datetime import datetime
from src.gui.contact_details_dialog import ContactDetailsDialog

class AdvancedSearchDialog(QDialog):
    def __init__(self, parent=None, search_history=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Search")
        layout = QVBoxLayout(self)
        
        # Search type selection
        search_type_layout = QHBoxLayout()
        self.search_type_group = QButtonGroup(self)
        
        self.normal_search = QRadioButton("Normal")
        self.regex_search = QRadioButton("Regex")
        self.search_type_group.addButton(self.normal_search)
        self.search_type_group.addButton(self.regex_search)
        self.normal_search.setChecked(True)
        
        search_type_layout.addWidget(self.normal_search)
        search_type_layout.addWidget(self.regex_search)
        layout.addLayout(search_type_layout)
        
        # Search fields
        form_layout = QFormLayout()
        self.first_name = QLineEdit()
        self.last_name = QLineEdit()
        self.email = QLineEdit()
        self.phone = QLineEdit()
        
        form_layout.addRow("First Name:", self.first_name)
        form_layout.addRow("Last Name:", self.last_name)
        form_layout.addRow("Email:", self.email)
        form_layout.addRow("Phone:", self.phone)
        layout.addLayout(form_layout)
        
        # Search history
        if search_history:
            history_label = QLabel("Search History:")
            layout.addWidget(history_label)
            
            self.history_list = QListWidget()
            self.history_list.addItems(search_history)
            self.history_list.itemClicked.connect(self._apply_history_item)
            layout.addWidget(self.history_list)
        
        # Search options
        self.case_sensitive = QCheckBox("Case Sensitive")
        layout.addWidget(self.case_sensitive)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _apply_history_item(self, item):
        """Apply selected history item to search fields"""
        try:
            # Assuming history items are stored as JSON strings
            import json
            data = json.loads(item.text())
            self.first_name.setText(data.get('first_name', ''))
            self.last_name.setText(data.get('last_name', ''))
            self.email.setText(data.get('email', ''))
            self.phone.setText(data.get('phone', ''))
            self.case_sensitive.setChecked(data.get('case_sensitive', False))
            self.regex_search.setChecked(data.get('is_regex', False))
        except:
            pass

class ContactManagerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Contact Manager")
        self.setMinimumSize(QSize(800, 600))
        
        # Initialize components
        self.db_session = None
        self.contact_manager = None
        self.command_manager = CommandManager()
        
        # Setup UI
        self._setup_ui()
        
        # Initialize backend with a slight delay to let the window show
        QTimer.singleShot(100, lambda: self._initialize_backend_wrapper())
    
    def _setup_ui(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create top button bar
        button_layout = QHBoxLayout()
        
        # Sync button
        self.sync_button = QPushButton("Sync Contacts")
        self.sync_button.clicked.connect(self._handle_sync)
        button_layout.addWidget(self.sync_button)
        
        # Status label
        self.status_label = QLabel("Ready")
        button_layout.addWidget(self.status_label)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Search bar with advanced options
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search contacts... (Ctrl+F)")
        self.search_input.textChanged.connect(self._handle_search)
        # Add keyboard shortcut
        shortcut = QKeySequence(QKeySequence.Find)
        self.search_action = QAction("Search", self)
        self.search_action.setShortcut(shortcut)
        self.search_action.triggered.connect(lambda: self.search_input.setFocus())
        self.addAction(self.search_action)
        
        # Advanced search button
        advanced_button = QToolButton()
        advanced_button.setText("▼")
        advanced_button.clicked.connect(self._show_advanced_search)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(advanced_button)
        
        # Source filter with save/restore
        self.source_filter = QComboBox()
        self.source_filter.addItem("All Sources")
        self.source_filter.currentTextChanged.connect(self._handle_filter)
        search_layout.addWidget(self.source_filter)
        
        layout.addLayout(search_layout)
        
        # Load saved filter settings
        self._load_filter_settings()
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "First Name", "Last Name", "Email", "Phone", "Source"
        ])
        
        # Set table properties with better colors for both light and dark modes
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: rgba(128, 128, 128, 0.1);
            }
            QHeaderView::section {
                padding: 4px;
                border: none;
                border-bottom: 1px solid palette(mid);
            }
        """)
        
        # Set table properties
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        
        # Set column stretching
        header = self.table.horizontalHeader()
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        # Make sure table takes up available space
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.table, stretch=1)
        
        # Set layout margins and spacing
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Add more keyboard shortcuts
        self.addAction(self._create_shortcut("Ctrl+R", self._show_advanced_search))
        self.addAction(self._create_shortcut("Esc", self.search_input.clear))
        self.addAction(self._create_shortcut("Ctrl+H", self._show_search_history))
        
        # Add toolbar
        toolbar = self.addToolBar("Contact Actions")
        toolbar.setMovable(False)
        
        # Add contact button
        add_action = QAction("Add Contact", self)
        add_action.setShortcut(QKeySequence.New)  # Usually Ctrl+N
        add_action.triggered.connect(self._show_add_contact_dialog)
        toolbar.addAction(add_action)
        
        # Edit contact button
        edit_action = QAction("Edit Contact", self)
        edit_action.setShortcut(QKeySequence("Ctrl+E"))
        edit_action.triggered.connect(self._edit_selected_contact)
        toolbar.addAction(edit_action)
        
        # Delete contact button
        delete_action = QAction("Delete Contact", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._delete_selected_contacts)
        toolbar.addAction(delete_action)
        
        # Merge contacts button
        merge_action = QAction("Merge Contacts", self)
        merge_action.setShortcut(QKeySequence("Ctrl+M"))
        merge_action.triggered.connect(self._show_merge_dialog)
        toolbar.addAction(merge_action)
        
        # Add Find Duplicates button
        find_duplicates_action = QAction("Find Duplicates", self)
        find_duplicates_action.setShortcut(QKeySequence("Ctrl+D"))
        find_duplicates_action.triggered.connect(self._show_duplicates)
        toolbar.addAction(find_duplicates_action)
        
        # Add Undo/Redo buttons
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.Undo)  # Usually Ctrl+Z
        undo_action.triggered.connect(self._handle_undo)
        undo_action.setEnabled(False)
        self.undo_action = undo_action
        toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.Redo)  # Usually Ctrl+Y or Ctrl+Shift+Z
        redo_action.triggered.connect(self._handle_redo)
        redo_action.setEnabled(False)
        self.redo_action = redo_action
        toolbar.addAction(redo_action)
        
        # Add Import and Clear buttons to toolbar
        toolbar.addSeparator()
        
        import_action = QAction("Import Source", self)
        import_action.triggered.connect(self._show_import_dialog)
        toolbar.addAction(import_action)
        
        clear_action = QAction("Clear Database", self)
        clear_action.triggered.connect(self._show_clear_dialog)
        toolbar.addAction(clear_action)
        
        # Enable context menu for the table
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        # Connect double-click handler
        self.table.itemDoubleClicked.connect(self._show_contact_details)
    
    def _initialize_backend_wrapper(self):
        """Wrapper to run async initialization"""
        asyncio.create_task(self._initialize_backend())
    
    async def _initialize_backend(self):
        """Initialize database and contact manager"""
        try:
            print("Initializing database...")
            self.db_session = await init_db("sqlite+aiosqlite:///contacts.db")
            print("Database initialized")
            
            async with self.db_session() as session:
                print("Creating contact manager...")
                self.contact_manager = ContactManager(session)
                
                # Add Gmail source
                print("Creating Gmail source...")
                gmail_source = GmailContactSource()
                await self.contact_manager.add_source(gmail_source)
                print("Gmail source added")
                
                # Add Yahoo source
                print("Creating Yahoo source...")
                yahoo_source = YahooContactSource()
                await self.contact_manager.add_source(yahoo_source)
                print("Yahoo source added")
                
                # Add Yahoo CSV source
                print("Creating Yahoo CSV source...")
                yahoo_source = CSVContactSource(provider='yahoo')
                await self.contact_manager.add_source(yahoo_source)
                print("Yahoo source added")
            
            # Load existing contacts
            print("Loading existing contacts...")
            await self._load_contacts()
            print("Existing contacts loaded")
            
        except Exception as e:
            print(f"Error in _initialize_backend: {str(e)}")
            import traceback
            print(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"Failed to initialize: {str(e)}\n\n{traceback.format_exc()}")
    
    async def _load_contacts(self):
        """Load contacts from database into table"""
        from src.models.contact_model import ContactModel
        from sqlalchemy import select
        from PySide6.QtCore import Qt
        
        self.table.setRowCount(0)  # Clear existing rows
        self.table.setSortingEnabled(False)  # Disable sorting while updating
        
        async with self.db_session() as session:
            stmt = select(ContactModel)
            result = await session.execute(stmt)
            contacts = result.scalars().all()
            
            # Pre-allocate rows
            self.table.setRowCount(len(contacts))
            
            for row, contact in enumerate(contacts):
                # Create items with proper flags
                items = [
                    QTableWidgetItem(str(contact.first_name or "")),
                    QTableWidgetItem(str(contact.last_name or "")),
                    QTableWidgetItem(str(contact.email or "")),
                    QTableWidgetItem(str(contact.phone or "")),
                    QTableWidgetItem(str(contact.source or ""))
                ]
                
                # Set flags and items
                for col, item in enumerate(items):
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    # Store contact ID in the first column's item
                    if col == 0:
                        item.setData(Qt.UserRole, contact.id)
                    self.table.setItem(row, col, item)
                
                # Force update every 100 rows
                if row % 100 == 0:
                    QApplication.processEvents()
        
        self.table.setSortingEnabled(True)  # Re-enable sorting
        
        # Update source filter
        self._update_source_filter()
    
    def _handle_sync(self):
        """Handle sync button click"""
        self.sync_button.setEnabled(False)
        self.status_label.setText("Starting sync process...")
        print("Starting sync process...")
        # Use QTimer to ensure UI updates
        QTimer.singleShot(0, lambda: asyncio.create_task(self._do_sync()))
    
    async def _do_sync(self):
        """Perform contact synchronization"""
        try:
            self.status_label.setText("Starting sync...")
            print("Starting sync...")
            async with self.db_session() as session:
                self.contact_manager.db = session
                self.status_label.setText("Fetching contacts from Gmail...")
                print("Fetching contacts from Gmail...")
                contacts = await self.contact_manager.sync_all_sources()
                print(f"Fetched {len(contacts)} contacts")
                self.status_label.setText("Loading contacts into table...")
                print("Loading contacts into table...")
                await self._load_contacts()
                msg = f"Synced {len(contacts)} contacts"
                print(msg)
                self.status_label.setText(msg)
        except Exception as e:
            import traceback
            error_msg = f"Sync failed: {str(e)}\n\n{traceback.format_exc()}"
            print(error_msg)
            self.status_label.setText("Sync failed")
            QMessageBox.critical(self, "Error", error_msg)
        finally:
            self.sync_button.setEnabled(True) 
    
    def _handle_search(self, search_text: str):
        """Filter contacts based on search text"""
        search_text = search_text.lower()
        for row in range(self.table.rowCount()):
            matches = False
            # Search across all columns
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and search_text in item.text().lower():
                    matches = True
                    break
            # Show/hide row based on match
            self.table.setRowHidden(row, not matches)
    
    def _handle_filter(self, source: str):
        """Filter contacts based on source"""
        show_all = source == "All Sources"
        for row in range(self.table.rowCount()):
            source_item = self.table.item(row, 4)  # Source is in column 4
            if source_item:
                source_matches = show_all or source_item.text() == source
                # Only show/hide if row isn't already hidden by search
                if not self.table.isRowHidden(row) or source_matches:
                    self.table.setRowHidden(row, not source_matches)
    
    def _show_advanced_search(self):
        """Show advanced search dialog"""
        dialog = AdvancedSearchDialog(self)
        if dialog.exec_():
            # Get search criteria
            criteria = {
                'first_name': dialog.first_name.text(),
                'last_name': dialog.last_name.text(),
                'email': dialog.email.text(),
                'phone': dialog.phone.text(),
                'case_sensitive': dialog.case_sensitive.isChecked()
            }
            self._handle_advanced_search(criteria)
    
    def _handle_advanced_search(self, criteria):
        """Handle advanced search with multiple fields and regex support"""
        for row in range(self.table.rowCount()):
            matches = True
            fields = ['first_name', 'last_name', 'email', 'phone']
            
            for field, col in zip(fields, range(4)):
                if criteria[field]:
                    item = self.table.item(row, col)
                    if not self._text_matches(
                        item,
                        criteria[field],
                        criteria['case_sensitive'],
                        criteria.get('is_regex', False)
                    ):
                        matches = False
                        break
            
            self.table.setRowHidden(row, not matches)
    
    def _text_matches(self, item, search_text: str, case_sensitive: bool, is_regex: bool = False) -> bool:
        """Check if item text matches search text using normal or regex search"""
        if not item:
            return False
            
        item_text = item.text()
        if not case_sensitive:
            item_text = item_text.lower()
            search_text = search_text.lower()
        
        if is_regex:
            try:
                pattern = re.compile(search_text, flags=0 if case_sensitive else re.IGNORECASE)
                return bool(pattern.search(item_text))
            except re.error:
                return False
        else:
            return search_text in item_text
    
    def _save_filter_settings(self):
        """Save current filter settings"""
        settings = QSettings('ContactManager', 'Filters')
        settings.setValue('source_filter', self.source_filter.currentText())
        settings.setValue('search_text', self.search_input.text())
    
    def _load_filter_settings(self):
        """Load saved filter settings"""
        settings = QSettings('ContactManager', 'Filters')
        source = settings.value('source_filter', 'All Sources')
        search_text = settings.value('search_text', '')
        
        # Apply saved settings after contacts are loaded
        QTimer.singleShot(500, lambda: self._apply_saved_settings(source, search_text))
    
    def _apply_saved_settings(self, source: str, search_text: str):
        """Apply saved filter settings"""
        if source != 'All Sources':
            index = self.source_filter.findText(source)
            if index >= 0:
                self.source_filter.setCurrentIndex(index)
        
        if search_text:
            self.search_input.setText(search_text)
    
    def closeEvent(self, event):
        """Save settings when window is closed"""
        self._save_filter_settings()
        super().closeEvent(event)
    
    def _create_shortcut(self, key, slot):
        """Create a keyboard shortcut"""
        action = QAction(self)
        action.setShortcut(QKeySequence(key))
        action.triggered.connect(slot)
        return action
    
    def _show_search_history(self):
        """Show search history in advanced search dialog"""
        dialog = AdvancedSearchDialog(self, self.search_history)
        if dialog.exec_():
            criteria = {
                'first_name': dialog.first_name.text(),
                'last_name': dialog.last_name.text(),
                'email': dialog.email.text(),
                'phone': dialog.phone.text(),
                'case_sensitive': dialog.case_sensitive.isChecked(),
                'is_regex': dialog.regex_search.isChecked()
            }
            self._add_to_search_history(criteria)
            self._handle_advanced_search(criteria)
    
    def _add_to_search_history(self, criteria):
        """Add search criteria to history"""
        import json
        history_item = json.dumps(criteria)
        if history_item not in self.search_history:
            self.search_history.insert(0, history_item)
            if len(self.search_history) > self.max_history_items:
                self.search_history.pop()
    
    def _show_context_menu(self, position):
        """Show context menu for table"""
        menu = QMenu(self)
        
        # Add menu items
        edit_action = menu.addAction("Edit Contact")
        delete_action = menu.addAction("Delete Contact")
        merge_action = menu.addAction("Merge with...")
        
        # Show menu and handle selection
        action = menu.exec_(self.table.viewport().mapToGlobal(position))
        if action == edit_action:
            self._edit_selected_contact()
        elif action == delete_action:
            self._delete_selected_contacts()
        elif action == merge_action:
            self._show_merge_dialog()
    
    def _show_add_contact_dialog(self):
        """Show dialog to add a new contact"""
        dialog = ContactDialog(self)
        if dialog.exec_():
            contact_data = dialog.get_contact_data()
            asyncio.create_task(self._add_contact(contact_data))
    
    def _edit_selected_contact(self):
        """Edit the selected contact"""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a contact to edit.")
            return
        
        row = selected[0].row()
        contact_data = {
            'id': self.table.item(row, 0).data(Qt.UserRole),
            'first_name': self.table.item(row, 0).text(),
            'last_name': self.table.item(row, 1).text(),
            'email': self.table.item(row, 2).text(),
            'phone': self.table.item(row, 3).text(),
            'source': self.table.item(row, 4).text()
        }
        
        dialog = ContactDialog(self, contact_data)
        if dialog.exec_():
            updated_data = dialog.get_contact_data()
            asyncio.create_task(self._update_contact(contact_data['id'], updated_data))
    
    def _delete_selected_contacts(self):
        """Delete selected contacts"""
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select contacts to delete.")
            return
        
        if QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected)//5} contact(s)?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        
        rows = set(item.row() for item in selected)
        contact_ids = [self.table.item(row, 0).data(Qt.UserRole) for row in rows]
        asyncio.create_task(self._delete_contacts(contact_ids))
    
    def _show_merge_dialog(self):
        """Show dialog to merge contacts"""
        selected = self.table.selectedItems()
        if not selected or len(set(item.row() for item in selected)) < 2:
            QMessageBox.warning(
                self,
                "Selection Required",
                "Please select at least two contacts to merge."
            )
            return
        
        # Get unique rows
        rows = sorted(set(item.row() for item in selected))
        if len(rows) > 2:
            QMessageBox.warning(
                self,
                "Too Many Selected",
                "Please select exactly two contacts to merge."
            )
            return
        
        # Get contact data for both contacts
        contacts = []
        for row in rows:
            contact_data = {
                'id': self.table.item(row, 0).data(Qt.UserRole),
                'first_name': self.table.item(row, 0).text(),
                'last_name': self.table.item(row, 1).text(),
                'email': self.table.item(row, 2).text(),
                'phone': self.table.item(row, 3).text(),
                'source': self.table.item(row, 4).text()
            }
            contacts.append(contact_data)
        
        # Show merge dialog
        dialog = MergeContactsDialog(self, contacts[0], contacts[1])
        if dialog.exec_():
            merged_data = dialog.get_merged_data()
            asyncio.create_task(self._merge_contacts(
                contacts[0]['id'],
                contacts[1]['id'],
                merged_data
            ))
    
    async def _merge_contacts(self, source_id: str, target_id: str, merged_data: dict):
        """Merge two contacts using the command pattern"""
        try:
            command = MergeCommand(self.contact_manager, source_id, target_id, merged_data)
            await self.command_manager.execute(command)
            await self._load_contacts()  # Refresh the table
            self.status_label.setText("Contacts merged successfully")
            self._update_undo_redo_actions()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to merge contacts: {str(e)}")
    
    async def _find_duplicates(self):
        """Find potential duplicate contacts"""
        try:
            async with self.db_session() as session:
                self.contact_manager.db = session
                duplicates = await self.contact_manager.find_duplicates()
                if duplicates:
                    dialog = DuplicateFinderDialog(self)
                    self.duplicate_groups = duplicates
                    await dialog.find_duplicates()
                    dialog.exec_()
                else:
                    QMessageBox.information(
                        self,
                        "No Duplicates",
                        "No potential duplicate contacts were found."
                    )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to find duplicates: {str(e)}")
    
    def _show_duplicates(self):
        """Show duplicate finder dialog"""
        self.status_label.setText("Finding duplicates...")
        asyncio.create_task(self._find_duplicates())
    
    def _update_undo_redo_actions(self):
        """Update the enabled state of undo/redo actions"""
        self.undo_action.setEnabled(self.command_manager.can_undo())
        self.redo_action.setEnabled(self.command_manager.can_redo())
        
        if self.command_manager.can_undo():
            self.undo_action.setToolTip(f"Undo {self.command_manager.get_undo_description()}")
        else:
            self.undo_action.setToolTip("Nothing to undo")
            
        if self.command_manager.can_redo():
            self.redo_action.setToolTip(f"Redo {self.command_manager.get_redo_description()}")
        else:
            self.redo_action.setToolTip("Nothing to redo")
    
    async def _handle_undo(self):
        """Handle undo action"""
        if await self.command_manager.undo():
            await self._load_contacts()  # Refresh the table
            self._update_undo_redo_actions()
    
    async def _handle_redo(self):
        """Handle redo action"""
        if await self.command_manager.redo():
            await self._load_contacts()  # Refresh the table
            self._update_undo_redo_actions()
    
    def _show_import_dialog(self):
        """Show dialog to select and import a contact source"""
        dialog = SourceSelectionDialog(self)
        if dialog.exec_():
            source_info = dialog.get_source_info()
            asyncio.create_task(self._import_source(source_info))
    
    def _show_clear_dialog(self):
        """Show confirmation dialog for clearing database"""
        result = QMessageBox.warning(
            self,
            "Clear Database",
            "Are you sure you want to clear all contacts from the database?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            asyncio.create_task(self._clear_database())
    
    async def _clear_database(self):
        """Clear all contacts from the database"""
        try:
            self.status_label.setText("Clearing database...")
            async with self.db_session() as session:
                from src.models.contact_model import ContactModel
                await session.execute(delete(ContactModel))
                await session.commit()
            
            await self._load_contacts()  # Refresh the table
            self.status_label.setText("Database cleared successfully")
            
        except Exception as e:
            self.status_label.setText("Failed to clear database")
            QMessageBox.critical(self, "Error", f"Failed to clear database: {str(e)}")
    
    async def _import_source(self, source_info):
        """Import contacts from selected source"""
        try:
            self.status_label.setText(f"Importing from {source_info['type']}...")
            
            async with self.db_session() as session:
                self.contact_manager.db = session
                
                if source_info['type'] == 'Gmail':
                    source = GmailContactSource()
                    source.source_name = source_info['name']
                elif source_info['type'] == 'CSV Import':
                    source = CSVContactSource(provider=source_info['name'])
                else:
                    raise ValueError(f"Unknown source type: {source_info['type']}")
                
                contacts = await source.fetch_contacts()
                
                # Save contacts to database
                for contact in contacts:
                    contact.source = source_info['name']  # Override source name
                    await self._save_contact(contact)
                
                await self._load_contacts()  # Refresh the table
                self.status_label.setText(f"Imported {len(contacts)} contacts from {source_info['name']}")
                
        except Exception as e:
            self.status_label.setText("Import failed")
            QMessageBox.critical(self, "Error", f"Failed to import contacts: {str(e)}")
    
    def _update_source_filter(self):
        """Update source filter combobox with available sources"""
        # Get all unique sources
        sources = set()
        for row in range(self.table.rowCount()):
            source_item = self.table.item(row, 4)  # Source is in column 4
            if source_item:
                sources.add(source_item.text())
        
        # Update source filter while preserving current selection
        current_source = self.source_filter.currentText()
        self.source_filter.clear()
        self.source_filter.addItem("All Sources")
        self.source_filter.addItems(sorted(sources))
        
        # Restore previous selection or default to "All Sources"
        index = self.source_filter.findText(current_source)
        if index >= 0:
            self.source_filter.setCurrentIndex(index)
        else:
            self.source_filter.setCurrentIndex(0)  # Set to "All Sources"
    
    async def _save_contact(self, contact: Contact):
        """Save a contact to the database"""
        try:
            async with self.db_session() as session:
                from src.models.contact_model import ContactModel
                
                # Create new contact model
                contact_model = ContactModel(
                    id=contact.id,
                    first_name=contact.first_name,
                    last_name=contact.last_name,
                    email=contact.email,
                    phone=contact.phone,
                    source=contact.source,
                    source_id=contact.source_id,
                    contact_metadata=contact.metadata,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Add to database
                session.add(contact_model)
                await session.commit()
                
        except Exception as e:
            print(f"Error saving contact: {str(e)}")
            raise
    
    def _show_contact_details(self, item):
        """Show contact details when a contact is double-clicked"""
        row = item.row()
        contact_data = {
            'id': self.table.item(row, 0).data(Qt.UserRole),
            'first_name': self.table.item(row, 0).text(),
            'last_name': self.table.item(row, 1).text(),
            'email': self.table.item(row, 2).text(),
            'phone': self.table.item(row, 3).text(),
            'source': self.table.item(row, 4).text()
        }
        
        # Get additional metadata from database
        asyncio.create_task(self._show_contact_details_async(contact_data))
    
    async def _show_contact_details_async(self, contact_data):
        """Load contact metadata and show details dialog"""
        try:
            async with self.db_session() as session:
                from src.models.contact_model import ContactModel
                contact = await session.get(ContactModel, contact_data['id'])
                if contact:
                    contact_data['metadata'] = contact.contact_metadata
                    
                    dialog = ContactDetailsDialog(contact_data, self)
                    dialog.exec_()
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load contact details: {str(e)}")