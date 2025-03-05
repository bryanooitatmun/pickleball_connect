// app/static/js/coach/availability.js
// Calculate and preview availability slots
function calculateAvailabilitySlots() {
    const startDate = new Date(document.getElementById('bulk-start-date').value);
    const endDate = new Date(document.getElementById('bulk-end-date').value);
    const selectedDays = Array.from(document.querySelectorAll('input[name="days[]"]:checked')).map(cb => parseInt(cb.value));
    const startTime = document.getElementById('bulk-start-time').value;
    const endTime = document.getElementById('bulk-end-time').value;
    const increment = parseInt(document.getElementById('bulk-increment').value);
    const duration = document.getElementById('bulk-duration').value === 'custom' 
      ? parseInt(document.getElementById('custom-duration').value) 
      : parseInt(document.getElementById('bulk-duration').value);
    
    // Selected courts
    const courts = Array.from(document.getElementById('bulk-courts').selectedOptions).map(option => ({
      id: option.value,
      name: option.textContent
    }));
    
    const slots = [];
    
    // Convert start/end times to minutes since midnight for easier calculation
    const startMinutes = timeStringToMinutes(startTime);
    const endMinutes = timeStringToMinutes(endTime);
    
    // Generate slots
    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
      const dayOfWeek = date.getDay(); // 0 = Sunday, 1 = Monday, etc.
      
      // Skip if this day of week is not selected
      if (!selectedDays.includes(dayOfWeek)) continue;
      
      // For each court
      for (const court of courts) {
        // Generate time slots
        for (let timeMinutes = startMinutes; timeMinutes + duration <= endMinutes; timeMinutes += increment) {
          const slotStartTime = minutesToTimeString(timeMinutes);
          const slotEndTime = minutesToTimeString(timeMinutes + duration);
          
          slots.push({
            date: date.toISOString().split('T')[0],
            court_id: court.id,
            court_name: court.name,
            start_time: slotStartTime,
            end_time: slotEndTime
          });
        }
      }
    }
    
    return slots;
  }
  
  // Initialize bulk availability functionality
  function initBulkAvailability() {
    // Show/hide custom duration field
    document.getElementById('bulk-duration')?.addEventListener('change', function() {
      const customDurationContainer = document.getElementById('custom-duration-container');
      if (this.value === 'custom') {
        customDurationContainer.classList.remove('hidden');
      } else {
        customDurationContainer.classList.add('hidden');
      }
    });
  
    // Preview button
    document.getElementById('preview-availability-btn')?.addEventListener('click', function() {
      const slots = calculateAvailabilitySlots();
      const previewContainer = document.getElementById('preview-container');
      const previewSlots = document.getElementById('preview-slots');
      const slotCount = document.getElementById('slot-count');
      const previewCount = document.getElementById('preview-count');
      
      // Update count
      slotCount.textContent = slots.length;
      previewCount.classList.remove('hidden');
      
      if (slots.length === 0) {
        previewContainer.classList.add('hidden');
        return;
      }
      
      // Show preview
      previewContainer.classList.remove('hidden');
      previewSlots.innerHTML = '';
      
      // Group by date
      const slotsByDate = {};
      slots.forEach(slot => {
        if (!slotsByDate[slot.date]) {
          slotsByDate[slot.date] = [];
        }
        slotsByDate[slot.date].push(slot);
      });
      
      // Create preview items
      for (const [date, dateSlots] of Object.entries(slotsByDate)) {
        const dateHeader = document.createElement('div');
        dateHeader.className = 'font-medium mb-2 mt-4';
        dateHeader.textContent = formatDate(date);
        previewSlots.appendChild(dateHeader);
        
        for (const slot of dateSlots) {
          const slotItem = document.createElement('div');
          slotItem.className = 'text-sm mb-1 ml-4';
          slotItem.textContent = `${slot.court_name}: ${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}`;
          previewSlots.appendChild(slotItem);
        }
      }
    });
  
    // Submit bulk availability form
    document.getElementById('bulk-availability-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const slots = calculateAvailabilitySlots();
      if (slots.length === 0) {
        showToast('Error', 'No availability slots to create. Please check your settings.', 'error');
        return;
      }
      
      try {
        showLoading(this);
        const response = await addBulkAvailability({ slots });
        hideLoading(this);
        
        showToast('Success', `Created ${slots.length} availability slots successfully.`, 'success');
        this.reset();
        
        // Hide preview
        document.getElementById('preview-container').classList.add('hidden');
        document.getElementById('preview-count').classList.add('hidden');
        
        // Reload availability view
        loadAvailability();
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to create availability slots: ${error.message}`, 'error');
      }
    });
  }
  
  // Load availability data
  async function loadAvailability() {
    try {
      const availability = await getAvailability();
      
      // Store the original data
      originalAvailabilityData = availability;
      
      // Display the availability
      displayAvailability(availability);
      
    } catch (error) {
      console.error('Error loading availability:', error);
      showToast('Error', 'Failed to load availability data.', 'error');
    }
  }
  
  // Display availability data
  function displayAvailability(availability) {
    const container = document.getElementById('availability-container');
    if (!container) return;
    
    if (!availability || availability.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No availability slots added yet</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    // Group availability by date
    const groupedByDate = {};
    
    availability.forEach(slot => {
      const date = slot.date;
      
      if (!groupedByDate[date]) {
        groupedByDate[date] = [];
      }
      
      groupedByDate[date].push(slot);
    });
    
    // Sort dates
    const sortedDates = Object.keys(groupedByDate).sort();
    
    sortedDates.forEach(date => {
      const dateHeader = document.createElement('div');
      dateHeader.className = 'bg-gray-100 p-3 font-medium';
      dateHeader.textContent = formatDate(date);
      dateHeader.dataset.date = date; // Store the original date
      container.appendChild(dateHeader);
      
      const slots = groupedByDate[date];
      
      // Sort slots by start time
      slots.sort((a, b) => a.start_time.localeCompare(b.start_time));
      
      slots.forEach(slot => {
        const slotItem = document.createElement('div');
        slotItem.className = 'flex justify-between items-center p-3 border-b border-gray-200';
        slotItem.dataset.courtId = slot.court.id;
        slotItem.dataset.date = slot.date;
        
        // Format time
        const startTime = formatTime(slot.start_time);
        const endTime = formatTime(slot.end_time);
        
        slotItem.innerHTML = `
          <div>
            <span class="font-medium">${startTime} - ${endTime}</span>
            <p class="text-gray-500 text-sm">${slot.court.name}</p>
          </div>
          <div class="flex items-center">
            <span class="mr-3 ${slot.is_booked ? 'text-green-600' : 'text-gray-600'}">
              ${slot.is_booked ? 'Booked' : 'Available'}
            </span>
            ${!slot.is_booked ? `
              <button class="text-red-600 hover:text-red-700 delete-availability-btn" data-availability-id="${slot.id}">
                <i class="fas fa-trash"></i>
              </button>
            ` : ''}
            </div>
            `;
      
      container.appendChild(slotItem);
    });
  });
  
  // Add event listeners for delete buttons
  document.querySelectorAll('.delete-availability-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const availabilityId = this.getAttribute('data-availability-id');
      document.getElementById('delete-availability-id').value = availabilityId;
      document.getElementById('delete-availability-modal').classList.remove('hidden');
    });
  });
}

// Filter availability based on criteria
function filterAvailability() {
  const courtFilter = document.getElementById('availability-filter-court');
  const dateFilter = document.getElementById('availability-filter-date');
  
  if (!courtFilter || !dateFilter) return;
  
  const courtId = courtFilter.value;
  const filterDate = dateFilter.value;
  
  // If no filters, show all data
  if (!courtId && !filterDate) {
    displayAvailability(originalAvailabilityData);
    return;
  }
  
  // Filter the original data
  const filteredData = originalAvailabilityData.filter(slot => {
    const matchesCourt = !courtId || slot.court.id.toString() === courtId;
    const matchesDate = !filterDate || slot.date === filterDate;
    
    return matchesCourt && matchesDate;
  });
  
  // Display the filtered data
  displayAvailability(filteredData);
}

// Load and display templates
async function loadAndDisplayTemplates() {
  try {
    const templates = await loadAvailabilityTemplates();
    const container = document.getElementById('templates-container');
    
    if (!container) return;
    
    if (!templates || templates.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No templates created yet</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    templates.forEach(template => {
      const templateItem = document.createElement('div');
      templateItem.className = 'bg-gray-50 rounded-lg p-4';
      templateItem.innerHTML = `
        <div class="flex justify-between items-center mb-2">
          <h4 class="font-medium">${template.name}</h4>
          <div class="flex space-x-2">
            <button class="text-blue-600 hover:text-blue-800 apply-template-btn" data-template-id="${template.id}">
              <i class="fas fa-play mr-1"></i> Apply
            </button>
            <button class="text-red-600 hover:text-red-800 delete-template-btn" data-template-id="${template.id}">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
        <p class="text-gray-600 text-sm">${template.description || 'No description provided'}</p>
      `;
      container.appendChild(templateItem);
    });
    
    // Add event listeners
    document.querySelectorAll('.apply-template-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const templateId = this.getAttribute('data-template-id');
        showApplyTemplateModal(templateId);
      });
    });
    
    document.querySelectorAll('.delete-template-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const templateId = this.getAttribute('data-template-id');
        showDeleteTemplateModal(templateId);
      });
    });
    
  } catch (error) {
    console.error('Error loading templates:', error);
    showToast('Error', 'Failed to load availability templates.', 'error');
  }
}

// Export functions
export {
  calculateAvailabilitySlots,
  initBulkAvailability,
  loadAvailability,
  displayAvailability,
  filterAvailability,
  loadAndDisplayTemplates
};