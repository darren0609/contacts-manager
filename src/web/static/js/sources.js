let sourceModals = {
    gmail: new bootstrap.Modal(document.getElementById('gmailConfigModal')),
    csv: new bootstrap.Modal(document.getElementById('csvConfigModal')),
    carddav: new bootstrap.Modal(document.getElementById('carddavConfigModal'))
};

const syncInfoModal = new bootstrap.Modal(document.getElementById('syncInfoModal'));
let pendingSyncSource = null;

async function loadSources() {
    try {
        const response = await fetch('/api/sources');
        const data = await response.json();
        renderSources(data.sources);
        updateSourceCount(data.sources.length);
    } catch (error) {
        showAlert('Error loading sources: ' + error.message, 'danger');
    }
}

function renderSources(sources) {
    const sourcesList = document.getElementById('sourcesList');
    if (!sourcesList) {
        console.error('Sources list container not found');
        return;
    }
    
    sourcesList.innerHTML = '';
    
    if (sources.length === 0) {
        sourcesList.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> No sources configured yet. 
                    Click "Add Source" to get started.
                </div>
            </div>
        `;
        return;
    }
    
    sources.forEach(source => {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-4';
        col.innerHTML = `
            <div class="card h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h5 class="card-title mb-0">${source.name}</h5>
                        <span class="badge bg-${source.status === 'Connected' ? 'success' : 'secondary'}">
                            ${source.status}
                        </span>
                    </div>
                    <p class="card-text text-muted">
                        <i class="bi bi-people"></i> ${source.contact_count} contacts
                    </p>
                    ${source.last_sync ? `
                        <p class="card-text small text-muted">
                            <i class="bi bi-clock"></i> Last synced: ${new Date(source.last_sync).toLocaleString()}
                        </p>
                    ` : ''}
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary me-2" data-source="${source.name}">
                            <i class="bi bi-arrow-repeat"></i> Sync
                        </button>
                        <button class="btn btn-sm btn-outline-secondary me-2" onclick="editSource('${source.name}')">
                            <i class="bi bi-gear"></i> Configure
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="disconnectSource('${source.name}')">
                            <i class="bi bi-x-lg"></i> Disconnect
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add click handler after the element is added to DOM
        const syncButton = col.querySelector('[data-source]');
        syncButton.addEventListener('click', (event) => syncSource(source.name, event));
        
        sourcesList.appendChild(col);
    });
}

function updateSourceCount(count) {
    const badge = document.getElementById('sourcesCount');
    if (badge) {
        badge.textContent = count;
    }
}

function showAlert(message, type = 'info', modal = null) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.style.zIndex = '1060';
    
    if (modal) {
        alertDiv.style.position = 'absolute';
        alertDiv.style.top = '0';
        alertDiv.style.left = '0';
        alertDiv.style.right = '0';
        alertDiv.style.borderRadius = '0';
        alertDiv.style.border = 'none';
    }
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    if (modal) {
        const modalBody = modal._element.querySelector('.modal-body');
        modalBody.insertBefore(alertDiv, modalBody.firstChild);
    } else {
        const container = document.querySelector('.container');
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    const words = message.split(' ').length;
    const baseTime = 8000;
    const timePerWord = 200;
    const displayTime = Math.max(baseTime, words * timePerWord);
    
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.style.opacity = '0';
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 300);
        }
    }, displayTime);
}

async function showSyncInfo(sourceName) {
    pendingSyncSource = sourceName;
    const infoContent = document.getElementById('syncInfoContent');
    
    try {
        const response = await fetch(`/api/sources/${encodeURIComponent(sourceName)}/info`);
        const data = await response.json();
        
        let content = '';
        if (sourceName.startsWith('csv_')) {
            content = `
                <div class="alert alert-info">
                    <h6>CSV Source Sync</h6>
                    <p>This source requires the original CSV file to be re-uploaded for syncing.</p>
                    <div class="mb-3">
                        <label class="form-label">Upload CSV File</label>
                        <input type="file" class="form-control" accept=".csv" id="syncCsvFile">
                    </div>
                    <p class="mb-0">
                        <small>
                            <i class="bi bi-info-circle"></i> 
                            The file will be processed using the existing field mapping:
                            <ul class="mb-0">
                                ${Object.entries(data.field_mapping).map(([field, column]) => 
                                    `<li>${field}: ${column}</li>`
                                ).join('')}
                            </ul>
                        </small>
                    </p>
                </div>
            `;
        } else {
            content = `
                <div class="alert alert-info">
                    <h6>Sync Details</h6>
                    <p>This will synchronize contacts from ${sourceName}:</p>
                    <ul>
                        <li>Last sync: ${data.last_sync ? new Date(data.last_sync).toLocaleString() : 'Never'}</li>
                        <li>Current contacts: ${data.contact_count}</li>
                    </ul>
                    <p class="mb-0">
                        <small>
                            <i class="bi bi-info-circle"></i> 
                            New contacts will be added and existing contacts will be updated.
                        </small>
                    </p>
                </div>
            `;
        }
        
        infoContent.innerHTML = content;
        syncInfoModal.show();
        
    } catch (error) {
        showAlert('Error getting sync info: ' + error.message, 'danger');
    }
}

async function syncSource(sourceName, event) {
    if (event) {
        event.preventDefault();
    }
    await showSyncInfo(sourceName);
}

document.getElementById('confirmSyncBtn').addEventListener('click', async () => {
    if (!pendingSyncSource) return;
    
    const button = event.currentTarget;
    const originalContent = button.innerHTML;
    
    try {
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Syncing...';
        
        let formData = new FormData();
        
        // Handle CSV file upload if present
        if (pendingSyncSource.startsWith('csv_')) {
            const fileInput = document.getElementById('syncCsvFile');
            if (!fileInput?.files?.length) {
                throw new Error('Please select a CSV file');
            }
            formData.append('file', fileInput.files[0]);
        }
        
        const response = await fetch(`/api/sources/${encodeURIComponent(pendingSyncSource)}/sync`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Sync failed');
        }
        
        const result = await response.json();
        
        if (result.success) {
            syncInfoModal.hide();
            if (result.message) {
                showAlert(result.message, 'info');
            } else {
                showAlert(`Successfully synced ${result.synced} contacts`, 'success');
            }
            await loadSources();
        } else {
            throw new Error(result.error || 'Sync failed');
        }
    } catch (error) {
        showAlert('Error syncing source: ' + error.message, 'danger');
    } finally {
        button.disabled = false;
        button.innerHTML = originalContent;
        pendingSyncSource = null;
    }
});

async function disconnectSource(sourceName) {
    if (!confirm(`Are you sure you want to disconnect ${sourceName}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/sources/${encodeURIComponent(sourceName)}/disconnect`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showAlert('Source disconnected successfully', 'success');
            await loadSources();
        } else {
            throw new Error(result.error || 'Disconnect failed');
        }
    } catch (error) {
        showAlert('Error disconnecting source: ' + error.message, 'danger');
    }
}

function configureSource(sourceType) {
    const modal = sourceModals[sourceType];
    if (modal) {
        // Store original button text
        const buttons = modal._element.querySelectorAll('button[type="button"]');
        buttons.forEach(button => {
            button.dataset.originalText = button.innerHTML;
        });
        modal.show();
    }
}

async function handleCSVUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const button = document.getElementById('importCsvBtn');
        const isUpdate = button.textContent === 'Update';
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
        
        const response = await fetch('/api/sources/csv/preview', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to process CSV file');
        }
        
        const data = await response.json();
        
        // Show field mapping UI
        const mappingDiv = document.getElementById('csvFieldMapping');
        
        // Keep any existing info alert
        const existingInfo = mappingDiv.querySelector('.alert-info');
        
        mappingDiv.innerHTML = existingInfo ? existingInfo.outerHTML : '';
        
        // Add field mapping controls
        const fields = [
            { id: 'first_name', label: 'First Name' },
            { id: 'last_name', label: 'Last Name' },
            { id: 'email', label: 'Email' },
            { id: 'phone', label: 'Phone' }
        ];
        
        fields.forEach(field => {
            const div = document.createElement('div');
            div.className = 'mb-3';
            div.innerHTML = `
                <label class="form-label">${field.label}</label>
                <select class="form-select" name="${field.id}" required>
                    <option value="">-- Select Column --</option>
                    ${data.headers.map(header => 
                        `<option value="${header}">${header}</option>`
                    ).join('')}
                </select>
            `;
            mappingDiv.appendChild(div);
        });
        
        // Try to auto-map fields based on header names
        data.headers.forEach(header => {
            const lowerHeader = header.toLowerCase();
            fields.forEach(field => {
                if (lowerHeader.includes(field.id.toLowerCase())) {
                    mappingDiv.querySelector(`select[name="${field.id}"]`).value = header;
                }
            });
        });
        
        // Show preview
        const previewDiv = document.createElement('div');
        previewDiv.className = 'mt-4';
        previewDiv.innerHTML = `
            <h6>Preview (first 3 rows):</h6>
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            ${data.headers.map(h => `<th>${h}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${data.preview.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${cell}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        mappingDiv.appendChild(previewDiv);
        
        button.disabled = false;
        button.innerHTML = isUpdate ? 'Update' : 'Import';
        
    } catch (error) {
        showAlert('Error processing CSV: ' + error.message, 'danger');
        const button = document.getElementById('importCsvBtn');
        button.disabled = false;
        button.innerHTML = button.textContent === 'Update' ? 'Update' : 'Import';
    }
}

async function importCSV() {
    const fileInput = document.querySelector('#csvUploadForm input[type="file"]');
    const file = fileInput.files[0];
    if (!file) {
        showAlert('Please select a file', 'warning');
        return;
    }
    
    // Get field mapping
    const mapping = {};
    let missingRequired = false;
    
    document.querySelectorAll('#csvFieldMapping select').forEach(select => {
        if (select.required && !select.value) {
            missingRequired = true;
            select.classList.add('is-invalid');
        } else {
            select.classList.remove('is-invalid');
            if (select.value) {
                mapping[select.name] = select.value;
            }
        }
    });
    
    if (missingRequired) {
        showAlert('Please map all required fields', 'warning');
        return;
    }
    
    const button = document.getElementById('importCsvBtn');
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Importing...';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('field_mapping', JSON.stringify(mapping));
        
        const response = await fetch('/api/sources/csv/import', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Import failed');
        }
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(`Successfully imported ${result.imported} contacts`, 'success');
            sourceModals.csv.hide();
            await loadSources();
        } else {
            throw new Error(result.error || 'Import failed');
        }
    } catch (error) {
        showAlert('Error importing contacts: ' + error.message, 'danger');
    } finally {
        button.disabled = false;
        button.innerHTML = 'Import';
    }
}

async function editSource(sourceName) {
    try {
        const response = await fetch(`/api/sources/${encodeURIComponent(sourceName)}/info`);
        const sourceInfo = await response.json();
        
        if (sourceName.startsWith('csv_')) {
            // Show CSV re-upload modal
            const modal = sourceModals.csv;
            const modalTitle = modal._element.querySelector('.modal-title');
            const importBtn = document.getElementById('importCsvBtn');
            
            modalTitle.textContent = 'Update CSV Source';
            importBtn.textContent = 'Update';
            
            // If we have existing field mapping, show it
            if (sourceInfo.field_mapping) {
                const mappingDiv = document.getElementById('csvFieldMapping');
                mappingDiv.innerHTML = `
                    <div class="alert alert-info">
                        <small>
                            <i class="bi bi-info-circle"></i> 
                            Current field mapping:
                            <ul class="mb-0">
                                ${Object.entries(sourceInfo.field_mapping).map(([field, column]) => 
                                    `<li>${field}: ${column}</li>`
                                ).join('')}
                            </ul>
                        </small>
                    </div>
                    <p>Upload a new CSV file to update contacts:</p>
                `;
            }
            
            modal.show();
        } else if (sourceName === "Gmail") {
            // Show Gmail configuration modal
            sourceModals.gmail.show();
        } else if (sourceName === "CardDAV") {
            // Show CardDAV configuration modal
            sourceModals.carddav.show();
        } else {
            showAlert(`Configuration for ${sourceName} is not yet supported`, 'info');
        }
    } catch (error) {
        showAlert('Error loading source configuration: ' + error.message, 'danger');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadSources();
    
    // Add source type handlers
    document.querySelectorAll('[data-source-type]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            configureSource(e.target.dataset.sourceType);
        });
    });
    
    // Gmail auth handler
    document.getElementById('gmailAuthBtn').addEventListener('click', async () => {
        const modal = sourceModals.gmail;
        const button = document.getElementById('gmailAuthBtn');
        
        try {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Authorizing...';
            
            // Start OAuth flow
            const response = await fetch('/api/sources/gmail/auth/start');
            const data = await response.json();
            
            if (data.auth_url) {
                // Open OAuth window
                const width = 600;
                const height = 700;
                const left = (window.innerWidth - width) / 2;
                const top = (window.innerHeight - height) / 2;
                
                const authWindow = window.open(
                    data.auth_url,
                    'Gmail Authorization',
                    `width=${width},height=${height},left=${left},top=${top}`
                );
                
                // Poll for completion
                const checkAuth = setInterval(async () => {
                    try {
                        const statusResponse = await fetch(`/api/sources/gmail/auth/check?state=${data.state}`);
                        const status = await statusResponse.json();
                        
                        if (status.completed) {
                            clearInterval(checkAuth);
                            authWindow.close();
                            
                            if (status.success) {
                                showAlert('Gmail account connected successfully', 'success');
                                modal.hide();
                                await loadSources();
                            } else {
                                throw new Error(status.error || 'Authorization failed');
                            }
                        }
                    } catch (error) {
                        clearInterval(checkAuth);
                        throw error;
                    }
                }, 1000);
                
            } else {
                throw new Error('Failed to start authorization');
            }
        } catch (error) {
            showAlert('Error authorizing Gmail: ' + error.message, 'danger', modal);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-google"></i> Authorize Gmail';
        }
    });
    
    // CSV import handler
    document.getElementById('importCsvBtn').addEventListener('click', importCSV);
    
    // CardDAV config handler
    document.getElementById('saveCarddavBtn').addEventListener('click', async () => {
        const modal = sourceModals.carddav;
        const form = document.getElementById('carddavConfigForm');
        const button = document.getElementById('saveCarddavBtn');
        
        try {
            // Basic form validation
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }
            
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
            
            const config = {
                type: 'carddav',
                server_url: form.querySelector('input[type="url"]').value,
                username: form.querySelector('input[type="text"]').value,
                password: form.querySelector('input[type="password"]').value
            };
            
            const response = await fetch('/api/sources/carddav/configure', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });
            
            if (!response.ok) {
                throw new Error('Failed to save configuration');
            }
            
            showAlert('CardDAV configuration saved successfully', 'success');
            modal.hide();
            await loadSources();
            
        } catch (error) {
            showAlert('Error saving configuration: ' + error.message, 'danger', modal);
        } finally {
            button.disabled = false;
            button.innerHTML = 'Save';
        }
    });
    
    // Add CSV file input handler
    document.querySelector('#csvUploadForm input[type="file"]')
        .addEventListener('change', handleCSVUpload);
    
    // Also update the "Sync All" button handler
    document.getElementById('syncButton').addEventListener('click', async () => {
        const button = document.getElementById('syncButton');
        const originalContent = button.innerHTML;
        
        try {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Syncing...';
            
            const response = await fetch('/api/sync', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                showAlert('All sources synced successfully', 'success');
                await loadSources();  // Refresh the sources list
            } else {
                throw new Error(result.error || 'Sync failed');
            }
        } catch (error) {
            showAlert('Error syncing sources: ' + error.message, 'danger');
        } finally {
            button.disabled = false;
            button.innerHTML = originalContent;
        }
    });
    
    // Add modal close handlers to reset state
    Object.values(sourceModals).forEach(modal => {
        modal._element.addEventListener('hidden.bs.modal', () => {
            // Remove any existing alerts
            const alerts = modal._element.querySelectorAll('.alert');
            alerts.forEach(alert => alert.remove());
            
            // Reset any forms
            const form = modal._element.querySelector('form');
            if (form) form.reset();
            
            // Reset buttons to default state
            const buttons = modal._element.querySelectorAll('button[type="button"]');
            buttons.forEach(button => {
                button.disabled = false;
                if (button.dataset.originalText) {
                    button.innerHTML = button.dataset.originalText;
                }
            });
            
            // Show sources list
            loadSources();
        });
    });
});