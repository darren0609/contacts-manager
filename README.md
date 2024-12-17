# Contact Manager

A powerful desktop application for managing contacts from multiple sources, with support for merging duplicates and synchronizing across different platforms.

## Features

- **Multiple Source Support**
  - Gmail Contacts Import
  - CSV File Import
  - Yahoo Contacts Import (planned)
  - CardDAV Support (planned)

- **Contact Management**
  - View all contacts in a unified interface
  - Add, edit, and delete contacts
  - Search and filter contacts
  - View detailed contact information
  - Source tracking for each contact

- **Duplicate Management**
  - Automatic duplicate detection
  - Confidence scoring for potential matches
  - Detailed matching reasons
  - Merge duplicate contacts
  - Undo/Redo support for merges

- **Data Organization**
  - Filter contacts by source
  - Advanced search capabilities
  - Sort contacts by any field
  - Group contacts by source

## Installation

### Prerequisites

#### Windows
- Python 3.8 or higher (from python.org)
- pip (included with Python)

#### macOS
Using Homebrew:
```
# Install Python if not already installed
brew install python

# Install Qt (required for PySide6)
brew install qt

# Ensure python/pip are in your PATH
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Installing Dependencies

#### Using pip (Windows/macOS)
```
pip install -r requirements.txt
```

#### Using Homebrew (macOS)
```
# Core dependencies
brew install pyside@6
brew install sqlite

# Python packages (still needed even with brew)
pip install google-auth-oauthlib google-auth google-api-python-client
pip install aiosqlite SQLAlchemy aiohttp
```

Note for macOS users: If you encounter any issues with PySide6 after installing via brew, try:
```
pip uninstall PySide6  # Remove any pip version
brew link --force pyside@6
```

The requirements.txt includes:
- PySide6
- google-auth-oauthlib
- google-auth
- google-api-python-client
- aiosqlite
- SQLAlchemy

### Google API Setup

1. Visit the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google People API
4. Create OAuth 2.0 credentials
5. Download the credentials file and save as `credentials.json` in the project root directory

## Usage

### Starting the Application

```
python src/main.py
```

### Importing Contacts

1. Click the "Import Source" button in the toolbar
2. Select the source type (Gmail or CSV)
3. Enter a name for the source (e.g., "Work Gmail", "Personal Contacts")
4. Follow the authentication prompts if required

### Finding and Merging Duplicates

1. Click "Find Duplicates" in the toolbar
2. Review the suggested duplicate pairs
3. Select pairs to merge
4. Choose which information to keep from each contact
5. Confirm the merge

### Searching Contacts

- Use the search bar for quick searches
- Click the advanced search button (▼) for more options
- Filter by source using the dropdown menu

### Managing Contacts

- Double-click a contact to view details
- Right-click for context menu options
- Use toolbar buttons for common actions
- Ctrl+Z/Ctrl+Y for undo/redo

## Project Structure

```
contacts-manager/
├── src/
│   ├── core/           # Core business logic
│   ├── db/            # Database models and management
│   ├── gui/           # User interface components
│   ├── sources/       # Contact source implementations
│   └── main.py        # Application entry point
├── logs/             # Application logs
├── credentials.json  # Google API credentials
└── requirements.txt  # Python dependencies
```

## Development

### Adding New Sources

1. Create a new source class in `src/sources/`
2. Inherit from `ContactSource` base class
3. Implement required methods:
   - `fetch_contacts()`
   - `push_contacts()` (optional)

### Logging

- Logs are stored in the `logs/` directory
- Separate logs for each import source
- Timestamp-based log files

## Troubleshooting

### Common Issues

1. **Google Authentication Failed**
   - Ensure `credentials.json` is in the correct location
   - Check that the Google People API is enabled
   - Verify OAuth consent screen configuration

2. **CSV Import Issues**
   - Verify CSV format matches expected headers
   - Check file encoding (UTF-8 recommended)
   - Ensure required columns are present

3. **Database Errors**
   - Check write permissions in application directory
   - Verify SQLite installation
   - Check database file integrity

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- Google People API
- PySide6 (Qt for Python)
- SQLAlchemy