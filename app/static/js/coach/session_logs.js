// app/static/js/coach/session_logs.js
// Load session logs
async function loadSessionLogs() {
    try {
      const sessionLogs = await getSessionLogs();
      
      sessionLogs.sort((a, b) => {
        const dateA = new Date(a.booking.date);
        const dateB = new Date(b.booking.date);
        
        if (document.getElementById(`session-logs-sort`)?.value === 'date-asc') {
          return dateA - dateB;
        } else {
          return dateB - dateA;
        }
      });
  
      // Store the original data
      originalSessionLogsData = sessionLogs;
      
      // Display the session logs
      displaySessionLogs(sessionLogs);
      
    } catch (error) {
      console.error('Error loading session logs:', error);
      showToast('Error', 'Failed to load session logs.', 'error');
    }
  }
  
  // Display session logs
  function displaySessionLogs(sessionLogs) {
    const container = document.getElementById('session-logs-container');
    
    if (!container) return;
    
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
      
      logCard.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${log.title}</h3>
            <p class="text-gray-500 text-sm">Session with ${log.student.first_name} ${log.student.last_name}</p>
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
    
    // Update recent logs on dashboard
    if (sessionLogs.length > 0) {
      updateRecentLogsList(sessionLogs.slice(0, 3));
    }
  }
  
  // Update recent logs list on dashboard
  function updateRecentLogsList(logs) {
    const container = document.getElementById('recent-logs-list');
    if (!container) return;
    
    if (logs.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No recent session logs</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    logs.forEach(log => {
      const logItem = document.createElement('div');
      logItem.className = 'p-3 bg-gray-50 rounded-lg';
      
      // Format date
      const logDate = formatDate(log.booking.date);
      
      logItem.innerHTML = `
        <div class="flex justify-between mb-1">
          <h4 class="font-medium">${log.title}</h4>
          <span class="text-sm text-gray-500">${logDate}</span>
        </div>
        <p class="text-gray-600 text-sm line-clamp-2">${log.notes || 'No notes added'}</p>
      `;
      
      container.appendChild(logItem);
    });
  }
  
  // Open session log modal
  function openSessionLogModal(bookingId, logId) {
    const modal = document.getElementById('session-log-modal');
    const form = document.getElementById('session-log-form');
    
    if (!modal || !form) return;
    
    // Reset form
    form.reset();
    
    // Set booking ID
    document.getElementById('session-log-booking-id').value = bookingId;
    
    // Set modal title
    document.getElementById('session-log-modal-title').textContent = logId ? 'Edit Session Log' : 'Add Session Log';
    
    if (logId) {
      try {
        // Show loading indicator
        modal.classList.add('loading');
        
        // Get session log data asynchronously
        getSessionLog(logId)
          .then(logData => {
            // Populate form
            document.getElementById('session-log-id').value = logData.id;
            document.getElementById('session-log-title').value = logData.title || '';
            document.getElementById('session-log-notes').value = logData.notes || '';
            document.getElementById('session-log-coach-notes').value = logData.coach_notes || '';
            
            // Hide loading indicator
            modal.classList.remove('loading');
          })
          .catch(error => {
            console.error('Error loading session log:', error);
            showToast('Error', 'Failed to load session log data.', 'error');
            modal.classList.remove('loading');
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
  
  // Filter session logs
  function filterSessionLogs() {
    const searchInput = document.getElementById('session-logs-search');
    const courtFilter = document.getElementById('session-logs-filter-court');
    const sortSelect = document.getElementById('session-logs-sort');
    
    if (!searchInput || !courtFilter || !sortSelect) return;
    
    const search = searchInput.value.toLowerCase();
    const courtId = courtFilter.value;
    const sortBy = sortSelect.value;
    
    // If no filters and default sort, show original data
    if (!search && !courtId && sortBy === 'date-desc') {
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
        const notes = log.notes?.toLowerCase() || '';
        const courtName = log.booking.court.name?.toLowerCase() || '';
        
        return title.includes(search) || 
              studentName.includes(search) || 
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
  
  // Export functions
  export {
    loadSessionLogs,
    displaySessionLogs,
    updateRecentLogsList,
    openSessionLogModal,
    filterSessionLogs
  };