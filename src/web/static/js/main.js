let contactsTable;
let currentContacts = [];
const contactModal = new bootstrap.Modal(document.getElementById('contactModal'));
let currentSort = {
    column: null,
    direction: 'asc'
};
let currentContactId = null;
let mergeDialog;
let currentDuplicates = [];
let selectedPair = null;
let taskCheckInterval;

async function loadContacts() {
    try {
        const response = await fetch('/api/contacts');
        const data = await response.json();
        currentContacts = data.contacts;
        renderContacts();
        updateSourceFilter();
    } catch (error) {
        showAlert('Error loading contacts: ' + error.message, 'danger');
    }
}

function renderContacts(filtered = currentContacts) {
    if (currentSort.column) {
        filtered = sortContacts(filtered, currentSort.column, currentSort.direction);
    }
    
    const tbody = document.getElementById('contactsList');
    tbody.innerHTML = '';
    
    filtered.forEach(contact => {
        const tr = document.createElement('tr');
        tr.addEventListener('click', (e) => {
            if (!e.target.closest('.action-buttons')) {
                showContactDetails(contact);
            }
        });
        tr.innerHTML = `
            <td>${contact.first_name || ''}</td>
            <td>${contact.last_name || ''}</td>
            <td>${contact.email || ''}</td>
            <td>${contact.phone || ''}</td>
            <td><span class="source-badge bg-secondary">${contact.source}</span></td>
            <td class="action-buttons">
                <button class="btn btn-sm btn-outline-primary" onclick="editContact('${contact.id}')">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteContact('${contact.id}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateSourceFilter() {
    const sources = new Set(currentContacts.map(c => c.source));
    const select = document.getElementById('sourceFilter');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">All Sources</option>';
    sources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        select.appendChild(option);
    });
    
    if (sources.has(currentValue)) {
        select.value = currentValue;
    }
}

async function syncAllSources() {
    const button = document.getElementById('syncButton');
    button.classList.add('syncing');
    
    try {
        const response = await fetch('/api/sync', { method: 'POST' });
        const result = await response.json();
        
        if (result.success) {
            showAlert('Sync completed successfully', 'success');
            await loadContacts();
        } else {
            showAlert('Sync failed: ' + result.error, 'danger');
        }
    } catch (error) {
        showAlert('Error during sync: ' + error.message, 'danger');
    } finally {
        button.classList.remove('syncing');
    }
}

async function saveContact(event) {
    event.preventDefault();
    
    const contactData = {
        id: document.getElementById('contactId').value,
        first_name: document.getElementById('firstName').value,
        last_name: document.getElementById('lastName').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value
    };
    
    try {
        const method = contactData.id ? 'PUT' : 'POST';
        const url = contactData.id ? `/api/contacts/${contactData.id}` : '/api/contacts';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(contactData)
        });
        
        if (response.ok) {
            contactModal.hide();
            await loadContacts();
            showAlert('Contact saved successfully', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save contact');
        }
    } catch (error) {
        showAlert('Error saving contact: ' + error.message, 'danger');
    }
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => alertDiv.remove(), 5000);
}

function sortContacts(contacts, column, direction) {
    return [...contacts].sort((a, b) => {
        let aVal = (a[column] || '').toLowerCase();
        let bVal = (b[column] || '').toLowerCase();
        
        if (direction === 'asc') {
            return aVal.localeCompare(bVal);
        } else {
            return bVal.localeCompare(aVal);
        }
    });
}

function handleSort(column) {
    const headers = document.querySelectorAll('.sortable');
    headers.forEach(header => {
        if (header.dataset.sort !== column) {
            header.classList.remove('asc', 'desc');
        }
    });

    const header = document.querySelector(`[data-sort="${column}"]`);
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        header.classList.toggle('asc');
        header.classList.toggle('desc');
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
        header.classList.add('asc');
        header.classList.remove('desc');
    }

    const sortedContacts = sortContacts(currentContacts, column, currentSort.direction);
    renderContacts(sortedContacts);
}

function showContactDetails(contact) {
    currentContactId = contact.id;
    const overlay = document.getElementById('contactOverlay');
    
    const initials = getInitials(contact.first_name, contact.last_name);
    overlay.querySelector('.initials').textContent = initials;
    overlay.querySelector('.contact-name').textContent = 
        `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || 'No Name';
    
    overlay.querySelector('.email span').textContent = contact.email || 'No email';
    overlay.querySelector('.phone span').textContent = contact.phone || 'No phone';
    overlay.querySelector('.source span').textContent = contact.source;
    
    const metadataList = overlay.querySelector('.metadata-list');
    metadataList.innerHTML = '';
    
    if (contact.metadata) {
        Object.entries(contact.metadata).forEach(([key, value]) => {
            if (value && typeof value !== 'object') {
                const div = document.createElement('div');
                div.className = 'metadata-item';
                div.innerHTML = `<strong>${key}:</strong> ${value}`;
                metadataList.appendChild(div);
            }
        });
    }
    
    overlay.classList.add('active');
}

function closeContactOverlay() {
    const overlay = document.getElementById('contactOverlay');
    overlay.classList.remove('active');
    currentContactId = null;
}

function editCurrentContact() {
    if (currentContactId) {
        editContact(currentContactId);
        closeContactOverlay();
    }
}

function deleteCurrentContact() {
    if (currentContactId) {
        if (confirm('Are you sure you want to delete this contact?')) {
            deleteContact(currentContactId);
            closeContactOverlay();
        }
    }
}

function getInitials(firstName, lastName) {
    const first = (firstName || '').charAt(0);
    const last = (lastName || '').charAt(0);
    return (first + last).toUpperCase() || '?';
}

document.addEventListener('click', (e) => {
    const overlay = document.getElementById('contactOverlay');
    const card = overlay.querySelector('.contact-card');
    
    if (overlay.classList.contains('active') && 
        !card.contains(e.target) && 
        !e.target.closest('tr')) {
        closeContactOverlay();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeContactOverlay();
    }
});

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadContacts();
    
    document.getElementById('searchInput').addEventListener('input', e => {
        const search = e.target.value.toLowerCase();
        const filtered = currentContacts.filter(contact => 
            `${contact.first_name} ${contact.last_name} ${contact.email} ${contact.phone}`
                .toLowerCase()
                .includes(search)
        );
        renderContacts(filtered);
    });
    
    document.getElementById('sourceFilter').addEventListener('change', e => {
        const source = e.target.value;
        const filtered = source 
            ? currentContacts.filter(c => c.source === source)
            : currentContacts;
        renderContacts(filtered);
    });
    
    document.getElementById('syncButton').addEventListener('click', syncAllSources);
    document.getElementById('saveContact').addEventListener('click', saveContact);
    
    // Add click handlers for sortable columns
    document.querySelectorAll('.sortable').forEach(header => {
        header.addEventListener('click', () => {
            handleSort(header.dataset.sort);
        });
    });
    
    // Initialize merge dialog
    mergeDialog = new bootstrap.Modal(document.getElementById('mergeDialog'));
    
    // Add duplicate finder button handler
    const findDuplicatesBtn = document.getElementById('findDuplicatesBtn');
    console.log("Find duplicates button:", findDuplicatesBtn);
    if (findDuplicatesBtn) {
        findDuplicatesBtn.addEventListener('click', () => {
            console.log("Find duplicates button clicked");
            findDuplicates();
        });
    }
    
    // Add merge button handler
    document.getElementById('mergeContactsBtn').addEventListener('click', mergeSelectedContacts);
    
    // Start checking for background tasks
    taskCheckInterval = setInterval(checkBackgroundTasks, 1000);
});

async function findDuplicates() {
    const button = document.getElementById('findDuplicatesBtn');
    if (!button) return;
    
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';

    try {
        const response = await fetch('/api/contacts/duplicates?full=1');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (data.not_ready) {
            showAlert('Still analyzing contacts for duplicates, please try again in a moment...', 'info');
            return;
        }

        if (!data.duplicates || data.duplicates.length === 0) {
            showAlert('No duplicate contacts found', 'info');
            return;
        }
        
        currentDuplicates = data.duplicates;
        showDuplicatesList(currentDuplicates);
        mergeDialog.show();
    } catch (error) {
        console.error("Error finding duplicates:", error);
        showAlert('Error finding duplicates: ' + error.message, 'danger');
    } finally {
        button.disabled = false;
        button.innerHTML = originalContent;
    }
}

function showDuplicatesList(duplicates) {
    const listContainer = document.querySelector('.duplicate-list');
    listContainer.innerHTML = '';
    document.querySelector('.merge-form').style.display = 'none';
    document.getElementById('mergeContactsBtn').style.display = 'none';
    
    duplicates.forEach((pair, index) => {
        const item = document.createElement('div');
        item.className = 'duplicate-item p-3 border-bottom';
        
        const contact1 = pair.contact1;
        const contact2 = pair.contact2;
        
        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                    <h6 class="mb-1">Potential Match (${(pair.confidence * 100).toFixed(1)}% confidence)</h6>
                    <small class="text-muted">${pair.reasons.join(', ')}</small>
                </div>
                <button class="btn btn-sm btn-primary merge-pair-btn" data-index="${index}">
                    Review & Merge
                </button>
            </div>
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h6>${contact1.first_name} ${contact1.last_name}</h6>
                            <p class="mb-1"><small>${contact1.email || 'No email'}</small></p>
                            <p class="mb-1"><small>${contact1.phone || 'No phone'}</small></p>
                            <small class="text-muted">${contact1.source}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-body">
                            <h6>${contact2.first_name} ${contact2.last_name}</h6>
                            <p class="mb-1"><small>${contact2.email || 'No email'}</small></p>
                            <p class="mb-1"><small>${contact2.phone || 'No phone'}</small></p>
                            <small class="text-muted">${contact2.source}</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        listContainer.appendChild(item);
    });
    
    // Add click handlers for merge buttons
    document.querySelectorAll('.merge-pair-btn').forEach(button => {
        button.addEventListener('click', () => {
            const index = parseInt(button.dataset.index);
            showMergeForm(currentDuplicates[index]);
        });
    });
}

function showMergeForm(pair) {
    selectedPair = pair;
    document.querySelector('.duplicate-list').style.display = 'none';
    document.querySelector('.merge-form').style.display = 'block';
    document.getElementById('mergeContactsBtn').style.display = 'block';
    
    // Populate contact cards
    const contact1Card = document.querySelector('.contact-1 .card-body');
    const contact2Card = document.querySelector('.contact-2 .card-body');
    
    contact1Card.innerHTML = createContactCardContent(pair.contact1);
    contact2Card.innerHTML = createContactCardContent(pair.contact2);
    
    // Populate merge form selects
    populateMergeSelects(pair.contact1, pair.contact2);
}

function createContactCardContent(contact) {
    return `
        <p class="mb-1"><strong>Name:</strong> ${contact.first_name} ${contact.last_name}</p>
        <p class="mb-1"><strong>Email:</strong> ${contact.email || 'None'}</p>
        <p class="mb-1"><strong>Phone:</strong> ${contact.phone || 'None'}</p>
        <p class="mb-0"><strong>Source:</strong> ${contact.source}</p>
    `;
}

function populateMergeSelects(contact1, contact2) {
    const fields = ['first_name', 'last_name', 'email', 'phone'];
    
    fields.forEach(field => {
        const select = document.querySelector(`select[name="${field}"]`);
        select.innerHTML = '';
        
        if (contact1[field]) {
            const option = document.createElement('option');
            option.value = `1:${contact1[field]}`;
            option.textContent = `${contact1[field]} (${contact1.source})`;
            select.appendChild(option);
        }
        
        if (contact2[field]) {
            const option = document.createElement('option');
            option.value = `2:${contact2[field]}`;
            option.textContent = `${contact2[field]} (${contact2.source})`;
            select.appendChild(option);
        }
        
        // Select the non-empty value or the first one
        if (contact1[field] && !contact2[field]) {
            select.value = `1:${contact1[field]}`;
        } else if (!contact1[field] && contact2[field]) {
            select.value = `2:${contact2[field]}`;
        }
    });
}

async function mergeSelectedContacts() {
    if (!selectedPair) return;
    
    const mergedData = {};
    const form = document.getElementById('mergeForm');
    const formData = new FormData(form);
    
    for (const [field, value] of formData.entries()) {
        mergedData[field] = value.split(':')[1];
    }
    
    try {
        const response = await fetch('/api/contacts/merge', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                source_id: selectedPair.contact1.id,
                target_id: selectedPair.contact2.id,
                merged_data: mergedData
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('Contacts merged successfully', 'success');
            mergeDialog.hide();
            loadContacts();  // Refresh the contacts list
        } else {
            throw new Error(result.error || 'Failed to merge contacts');
        }
    } catch (error) {
        showAlert('Error merging contacts: ' + error.message, 'danger');
    }
}

async function checkBackgroundTasks() {
    try {
        const response = await fetch('/api/tasks/status');
        const data = await response.json();
        
        const activeTasks = Object.values(data.tasks)
            .filter(task => task.status === 'running');
        
        if (activeTasks.length > 0) {
            // Show task progress
            updateTaskProgress(activeTasks);
        } else {
            // Hide progress indicator
            hideTaskProgress();
            clearInterval(taskCheckInterval);
            
            // Check for duplicates and add button if found
            await addDuplicatesButton();
        }
    } catch (error) {
        console.error('Error checking tasks:', error);
    }
}

async function addDuplicatesButton() {
    console.log("Checking for duplicates...");
    try {
        // First check if button already exists
        if (document.getElementById('findDuplicatesBtn')) {
            return;
        }

        // Check cache status first
        const statusResponse = await fetch('/api/cache/status');
        const statusData = await statusResponse.json();
        
        if (!statusData.ready) {
            console.log("Cache not ready yet");
            return;
        }

        // Get duplicate count
        const response = await fetch('/api/contacts/duplicates');
        const data = await response.json();
        console.log("Duplicates response:", data);
        
        if (!data || data.not_ready) {
            console.log("Cache not ready yet");
            return;
        }
        
        const count = data.count || 0;
        console.log(`Found ${count} duplicates`);
        
        // Create duplicates nav item
        const navList = document.querySelector('.navbar-nav');
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = `
            <a class="nav-link" href="#" id="findDuplicatesBtn">
                <i class="bi bi-people-fill"></i> Duplicates
                <span class="badge ${count > 0 ? 'bg-warning' : 'bg-light text-dark'}">${count}</span>
            </a>
        `;
        
        // Add click handler
        const link = li.querySelector('#findDuplicatesBtn');
        link.addEventListener('click', (e) => {
            e.preventDefault();
            findDuplicates();
        });
        
        // Add to navigation
        navList.appendChild(li);
        
    } catch (error) {
        console.error('Error checking duplicates:', error);
        console.error('Error details:', error.stack);
    }
}

function updateTaskProgress(tasks) {
    let progressBar = document.getElementById('taskProgress');
    if (!progressBar) {
        progressBar = createProgressBar();
    }
    
    const task = tasks[0]; // Show the first active task
    progressBar.querySelector('.progress-description').textContent = task.description;
    progressBar.querySelector('.progress-bar').style.width = `${task.progress}%`;
}

function createProgressBar() {
    const div = document.createElement('div');
    div.id = 'taskProgress';
    div.className = 'task-progress';
    div.innerHTML = `
        <div class="progress-description"></div>
        <div class="progress">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                 role="progressbar" style="width: 0%"></div>
        </div>
    `;
    document.querySelector('.container').prepend(div);
    return div;
}

function hideTaskProgress() {
    const progressBar = document.getElementById('taskProgress');
    if (progressBar) {
        progressBar.remove();
    }
} 