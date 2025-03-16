// Session Logs Management
let originalSessionLogsData = [];

// Initialize the session logs tab
function initSessionLogsTab() {
  loadSessionLogs();
  setupSessionLogsEventListeners();
}

// Load session logs data
async function loadSessionLogs() {
  try {
    const endpoint = IS_ACADEMY_MANAGER ? '/academy/session-logs' : '/coach/session-logs';
    const sessionLogs = await fetchAPI(endpoint);
    
    // Sort logs by date (newest first by default)
    sessionLogs.sort((a, b) => {
      const dateA = new Date(a.booking.date);
      const dateB = new Date(b.booking.date);
      return dateB - dateA;
    });

    // Store the original data
    originalSessionLogsData = sessionLogs;
    
    // Display the session logs
    displaySessionLogs(sessionLogs);
    
    // If academy manager, populate coach filter
    if (IS_ACADEMY_MANAGER) {
      populateCoachFilter(document.getElementById('session-logs-filter-coach'));
    }
    
  } catch (error) {
    console.error('Error loading session logs:', error);
    showToast('Error', 'Failed to load session logs.', 'error');
  }
}

// Display session logs
function displaySessionLogs(sessionLogs) {
  const container = document.getElementById('session-logs-container');
  
  if (!sessionLogs || sessionLogs.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-gray-500">
        <p>No session logs found</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  sessionLogs.forEach(log => {
    const logCard = document.createElement('div');
    logCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
    
    // Format date
    const logDate = formatDate(log.booking.date);
    
    // Add coach name if academy manager
    const coachInfo = IS_ACADEMY_MANAGER 
      ? `<span class="inline-block bg-blue-100 text-blue-700 rounded-lg px-2 py-1 text-xs ml-2">
           <i class="fas fa-user-tie mr-1"></i> ${log.coach.first_name} ${log.coach.last_name}
         </span>`
      : '';
    
    logCard.innerHTML = `
      <div class="flex justify-between">
        <div>
          <h3 class="font-semibold">${log.title}</h3>
          <p class="text-gray-500 text-sm">Session with ${log.student.first_name} ${log.student.last_name} ${coachInfo}</p>
        </div>
        <div class="text-right">
          <span class="text-gray-600">${logDate}</span>
        </div>
      </div>
      
      <div class="mt-2">
        <span class="inline-block bg-gray-100 text-gray-700 rounded-lg px-2 py-1 text-xs">
          <i class="fas fa-map-marker-alt mr-1"></i> ${log.booking.court.name}
        </span>
      </div>
      
      <div class="mt-3">
        <h4 class="text-sm font-medium text-gray-700">Public Notes</h4>
        <p class="text-gray-600 mt-1">${log.notes || 'No notes added'}</p>
      </div>

      <div class="mt-3">
        <h4 class="text-sm font-medium text-gray-700">Private Coach Notes</h4>
        <p class="text-gray-600 mt-1">${log.coach_notes || 'No notes added'}</p>
      </div>          
      
      <div class="flex justify-end mt-4">
        <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 edit-log-btn" data-log-id="${log.id}" data-booking-id="${log.booking_id}">
          Edit Log
        </button>
      </div>
    `;
    
    container.appendChild(logCard);
  });
  
  // Add event listeners for edit buttons
  document.querySelectorAll('.edit-log-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const logId = this.getAttribute('data-log-id');
      const bookingId = this.getAttribute('data-booking-id');
      
      openSessionLogModal(bookingId, logId);
    });
  });
}

// Set up event listeners for session logs
function setupSessionLogsEventListeners() {
  // Session log search input
  document.getElementById('session-logs-search')?.addEventListener('input', function() {
    filterSessionLogs();
  });

  // Session log court filter
  document.getElementById('session-logs-filter-court')?.addEventListener('change', function() {
    filterSessionLogs();
  });

  // Session log coach filter (for academy manager)
  document.getElementById('session-logs-filter-coach')?.addEventListener('change', function() {
    filterSessionLogs();
  });

  // Session log sort options
  document.getElementById('session-logs-sort')?.addEventListener('change', function() {
    filterSessionLogs();
  });

  // Reset filters button
  document.getElementById('reset-session-logs-filters')?.addEventListener('click', function() {
    const searchInput = document.getElementById('session-logs-search');
    const courtFilter = document.getElementById('session-logs-filter-court');
    const coachFilter = document.getElementById('session-logs-filter-coach');
    const sortSelect = document.getElementById('session-logs-sort');
    
    if (searchInput) searchInput.value = '';
    if (courtFilter) courtFilter.value = '';
    if (coachFilter) coachFilter.value = '';
    if (sortSelect) sortSelect.value = 'date-desc';
    
    displaySessionLogs(originalSessionLogsData);
  });
}

// Filter session logs
function filterSessionLogs() {
  const searchInput = document.getElementById('session-logs-search');
  const courtFilter = document.getElementById('session-logs-filter-court');
  const coachFilter = document.getElementById('session-logs-filter-coach');
  const sortSelect = document.getElementById('session-logs-sort');
  
  if (!searchInput || !courtFilter || !sortSelect) return;
  
  const search = searchInput.value.toLowerCase();
  const courtId = courtFilter.value;
  const coachId = coachFilter?.value || '';
  const sortBy = sortSelect.value;
  
  // If no filters and default sort, show original data
  if (!search && !courtId && !coachId && sortBy === 'date-desc') {
    displaySessionLogs(originalSessionLogsData);
    return;
  }
  
  // Clone the original data to avoid modifying it
  let filteredLogs = [...originalSessionLogsData];
  
  // Apply search filter
  if (search) {
    filteredLogs = filteredLogs.filter(log => {
      const title = log.title?.toLowerCase() || '';
      const studentName = `${log.student.first_name} ${log.student.last_name}`.toLowerCase();
      const coachName = `${log.coach.first_name} ${log.coach.last_name}`.toLowerCase();
      const notes = log.notes?.toLowerCase() || '';
      const courtName = log.booking.court.name?.toLowerCase() || '';
      
      return title.includes(search) || 
             studentName.includes(search) || 
             coachName.includes(search) || 
             notes.includes(search) ||
             courtName.includes(search);
    });
  }
  
  // Apply court filter
  if (courtId) {
    filteredLogs = filteredLogs.filter(log => {
      return log.booking.court.id.toString() === courtId;
    });
  }
  
  // Apply coach filter (for academy manager)
  if (coachId) {
    filteredLogs = filteredLogs.filter(log => {
      return log.coach.id.toString() === coachId;
    });
  }
  
  // Apply sorting
  filteredLogs.sort((a, b) => {
    const dateA = new Date(a.booking.date);
    const dateB = new Date(b.booking.date);
    
    if (sortBy === 'date-asc') {
      return dateA - dateB;
    } else {
      return dateB - dateA;
    }
  });
  
  // Display the filtered logs
  displaySessionLogs(filteredLogs);
}

// Open session log modal
function openSessionLogModal(bookingId, logId) {
  const modal = document.getElementById('session-log-modal');
  const form = document.getElementById('session-log-form');
  
  // Reset form
  form.reset();
  
  // Set booking ID
  document.getElementById('session-log-booking-id').value = bookingId;
  
  // Set modal title
  document.getElementById('session-log-modal-title').textContent = logId ? 'Edit Session Log' : 'Add Session Log';
  
  if (logId) {
    try {
      // Show loading indicator
      showLoading(modal);
      
      // Get session log data asynchronously
      const endpoint = IS_ACADEMY_MANAGER ? `/academy/session-logs/${logId}` : `/coach/session-logs/${logId}`;
      fetchAPI(endpoint)
        .then(logData => {
          // Populate form
          document.getElementById('session-log-id').value = logData.id;
          document.getElementById('session-log-title').value = logData.title || '';
          document.getElementById('session-log-notes').value = logData.notes || '';
          document.getElementById('session-log-coach-notes').value = logData.coach_notes || '';
          
          // Hide loading indicator
          hideLoading(modal);
        })
        .catch(error => {
          console.error('Error loading session log:', error);
          showToast('Error', 'Failed to load session log data.', 'error');
          hideLoading(modal);
          modal.classList.add('hidden');
        });
    } catch (error) {
      console.error('Error setting up session log modal:', error);
      showToast('Error', 'Failed to load session log data.', 'error');
      return;
    }
  } else {
    // Clear form fields
    document.getElementById('session-log-id').value = '';
    document.getElementById('session-log-title').value = 'Pickleball Session';
    document.getElementById('session-log-notes').value = '';
    document.getElementById('session-log-coach-notes').value = '';
  }
  
  // Show modal
  modal.classList.remove('hidden');
}

// Event delegation for modal close buttons
document.addEventListener('click', function(e) {
  if (e.target.closest('.close-session-log-modal')) {
    document.getElementById('session-log-modal').classList.add('hidden');
  }
});

// Submit session log form
document.getElementById('session-log-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const formData = new FormData(this);
  const logData = {
    log_id: formData.get('log_id'),
    booking_id: formData.get('booking_id'),
    title: formData.get('title'),
    notes: formData.get('notes'),
    coach_notes: formData.get('coach_notes')
  };
  
  try {
    showLoading(this);
    const endpoint = IS_ACADEMY_MANAGER ? '/academy/session-logs/update' : '/coach/session-logs/update';
    await fetchAPI(endpoint, {
      method: 'POST',
      body: JSON.stringify(logData)
    });
    hideLoading(this);
    document.getElementById('session-log-modal').classList.add('hidden');
    showToast('Success', 'Session log updated successfully.', 'success');
    loadSessionLogs();
  } catch (error) {
    hideLoading(this);
    showToast('Error', 'Failed to update session log. Please try again.', 'error');
  }
});