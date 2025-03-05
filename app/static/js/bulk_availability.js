let currentCalendarView = 'month'; // Track current view state globally

// Add these API functions to your existing API calls
async function addBulkAvailability(bulkData) {
    return fetchAPI('/coach/availability/add-bulk', {
      method: 'POST',
      body: JSON.stringify(bulkData)
    });
  }
  
async function saveAvailabilityTemplate(templateData) {
    data = fetchAPI('/coach/availability/templates/save', {
        method: 'POST',
        body: JSON.stringify(templateData)
    });
    await loadAndDisplayTemplates();
    return data;
}
  
  async function loadAvailabilityTemplates() {
    return fetchAPI('/coach/availability/templates');
  }
  
  async function applyTemplate(templateId, dateRange) {
    try{    
        return fetchAPI('/coach/availability/templates/apply', {
            method: 'POST',
            body: JSON.stringify({
            template_id: templateId,
            start_date: dateRange.start,
            end_date: dateRange.end
            })
        });}
    catch (error){
        debugger;
        console.error('Error loading dashboard data:', error);
        showToast('Error', error, 'error');
    }
  }
  
  // Helper functions for time and date calculations
  function timeStringToMinutes(timeString) {
    const [hours, minutes] = timeString.split(':').map(part => parseInt(part));
    return hours * 60 + minutes;
  }
  
  function minutesToTimeString(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  }
  
  // Function to calculate availability slots based on form inputs
  function calculateAvailabilitySlots() {
    const startDate = new Date(document.getElementById('bulk-start-date').value);
    const endDate = new Date(document.getElementById('bulk-end-date').value);
    const selectedDays = Array.from(document.querySelectorAll('input[name="days[]"]:checked')).map(cb => parseInt(cb.value));
    const startTime = document.getElementById('bulk-start-time').value;
    const endTime = document.getElementById('bulk-end-time').value;
    
    // Get time slot increment selection
    const incrementSelect = document.getElementById('bulk-increment');
    let increment = parseInt(incrementSelect.value);
    
    // If "Based on session duration" is selected, get the duration value
    if (incrementSelect.value === 'duration') {
      const durationSelect = document.getElementById('bulk-duration');
      if (durationSelect.value === 'custom') {
        increment = parseInt(document.getElementById('custom-duration').value);
      } else {
        increment = parseInt(durationSelect.value);
      }
    }
    
    // Get session duration
    const durationSelect = document.getElementById('bulk-duration');
    const duration = durationSelect.value === 'custom' 
      ? parseInt(document.getElementById('custom-duration').value) 
      : parseInt(durationSelect.value);
    
    // Selected courts
    const courts = Array.from(document.getElementById('bulk-courts').selectedOptions).map(option => ({
      id: option.value,
      name: option.textContent
    }));
    
    const slots = [];
    
    // Convert start/end times to minutes since midnight for easier calculation
    const startMinutes = timeStringToMinutes(startTime);
    const endMinutes = timeStringToMinutes(endTime);
    
    // Check if inputs are valid
    if (!startDate || !endDate || selectedDays.length === 0 || !startTime || !endTime || courts.length === 0) {
      return slots; // Return empty array if inputs are invalid
    }
    
    if (startDate > endDate) {
      showToast('Error', 'Start date must be before or equal to end date', 'error');
      return slots;
    }
    
    if (startMinutes >= endMinutes) {
      showToast('Error', 'Start time must be before end time', 'error');
      return slots;
    }
    
    // Generate slots
    for (let date = new Date(startDate); date <= endDate; date.setDate(date.getDate() + 1)) {
      const dayOfWeek = date.getDay(); // 0 = Sunday, 1 = Monday, etc.
      
      // Skip if this day of week is not selected
      if (!selectedDays.includes(dayOfWeek)) continue;
      
      // For each court
      for (const court of courts) {
        // Generate time slots based on increment
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
  
  // Function to generate calendar view
  function generateAvailabilityCalendarView(month, year, availabilityData) {
    const calendarContainer = document.getElementById('availability-calendar');
    calendarContainer.innerHTML = '';
    
    // Update month/year display
    const monthYearDisplay = document.getElementById('calendar-month-year');
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    monthYearDisplay.textContent = `${monthNames[month]} ${year}`;
    
    // Create calendar grid
    const table = document.createElement('table');
    table.className = 'w-full border-collapse';
    
    // Create header row with day names
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    dayNames.forEach(day => {
      const th = document.createElement('th');
      th.className = 'p-2 border border-gray-200 text-center';
      th.textContent = day;
      headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create calendar body
    const tbody = document.createElement('tbody');
    
    // Get first day of month and number of days in month
    const firstDayOfMonth = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    // Group availability data by date
    const availabilityByDate = {};
    if (availabilityData && availabilityData.length > 0) {
      availabilityData.forEach(slot => {
        const slotDate = slot.date;
        if (!availabilityByDate[slotDate]) {
          availabilityByDate[slotDate] = [];
        }
        availabilityByDate[slotDate].push(slot);
      });
    }
    
    let date = 1;
    let dayCount = 0;
    
    // Create rows for each week
    for (let i = 0; i < 6; i++) {
      const row = document.createElement('tr');
      row.className = 'h-24';
      
      // Create cells for each day
      for (let j = 0; j < 7; j++) {
        const cell = document.createElement('td');
        cell.className = 'p-2 border border-gray-200 align-top';
        
        // Add date number if we're in the current month
        if ((i === 0 && j < firstDayOfMonth) || date > daysInMonth) {
          cell.className += ' bg-gray-50';
        } else {
          const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
          
          // Date number
          const dateNumber = document.createElement('div');
          dateNumber.className = 'text-right mb-1';
          dateNumber.textContent = date;
          cell.appendChild(dateNumber);
          
          // Add availability info if any exists for this date
          if (availabilityByDate[dateStr] && availabilityByDate[dateStr].length > 0) {
            const availabilityCount = document.createElement('div');
            availabilityCount.className = 'text-xs bg-blue-100 rounded p-1 mb-1 text-center text-blue-800';
            availabilityCount.textContent = `${availabilityByDate[dateStr].length} slots`;
            cell.appendChild(availabilityCount);
            
            // Add a View button if there are slots
            const viewButton = document.createElement('button');
            viewButton.className = 'text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700 w-full';
            viewButton.textContent = 'View Details';
            viewButton.setAttribute('data-date', dateStr);
            viewButton.addEventListener('click', function() {
              showDateAvailability(dateStr, availabilityByDate[dateStr]);
            });
            cell.appendChild(viewButton);
          }
          
          date++;
        }
        
        row.appendChild(cell);
        dayCount++;
      }
      
      tbody.appendChild(row);
      
      // If we've displayed all days in the month, break
      if (date > daysInMonth) {
        break;
      }
    }
    
    table.appendChild(tbody);
    calendarContainer.appendChild(table);
  }
  
  // Function to show availability details for a specific date
  function showDateAvailability(date, slots) {
    // Create a modal to show the details
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50';
    
    const content = document.createElement('div');
    content.className = 'bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4';
    
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-4';
    header.innerHTML = `
      <h3 class="text-lg font-semibold">Availability for ${formatDate(date)}</h3>
      <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    content.appendChild(header);
    
    // Group slots by court
    const slotsByCourt = {};

    slots.forEach(slot => {
      if (!slotsByCourt[slot.court.name]) {
        slotsByCourt[slot.court.name] = [];
      }
      slotsByCourt[slot.court.name].push(slot);
    });
    
    // Create list of slots grouped by court
    const slotsList = document.createElement('div');
    slotsList.className = 'max-h-96 overflow-y-auto';
    
    for (const [courtName, courtSlots] of Object.entries(slotsByCourt)) {
      const courtHeader = document.createElement('h4');
      courtHeader.className = 'font-medium text-gray-800 mt-4 mb-2';
      courtHeader.textContent = courtName;
      slotsList.appendChild(courtHeader);
      
      const slotItems = document.createElement('div');
      slotItems.className = 'space-y-2';
      
      // Sort slots by start time
      courtSlots.sort((a, b) => {
        return a.start_time.localeCompare(b.start_time);
      });
      
      courtSlots.forEach(slot => {
        const slotItem = document.createElement('div');
        slotItem.className = 'flex justify-between items-center bg-gray-50 p-2 rounded';
        
        slotItem.innerHTML = `
          <span>${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}</span>
          <button class="text-red-600 hover:text-red-700 delete-availability-btn" data-availability-id="${slot.id}">
            <i class="fas fa-trash"></i>
          </button>
        `;
        
        slotItems.appendChild(slotItem);
      });
      
      slotsList.appendChild(slotItems);
    }
    
    content.appendChild(slotsList);
    
    // Add close button
    const footer = document.createElement('div');
    footer.className = 'mt-6 flex justify-end';
    footer.innerHTML = `
      <button class="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg font-medium hover:bg-gray-300 close-modal">
        Close
      </button>
    `;
    
    content.appendChild(footer);
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Add event listeners to close buttons
    modal.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.body.removeChild(modal);
      });
    });
    
    // Add event listeners to delete buttons
    modal.querySelectorAll('.delete-availability-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const availabilityId = this.getAttribute('data-availability-id');
        document.getElementById('delete-availability-id').value = availabilityId;
        document.getElementById('delete-availability-modal').classList.remove('hidden');
        document.body.removeChild(modal);
      });
    });
  }
  
// Initialize bulk availability functionality
function initBulkAvailability() {
    // Today's date for min attribute on date inputs
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('bulk-start-date').min = today;
    document.getElementById('bulk-end-date').min = today;
    
    // Set default values
    document.getElementById('bulk-start-date').value = today;
    const twoWeeksLater = new Date();
    twoWeeksLater.setDate(twoWeeksLater.getDate() + 14);
    document.getElementById('bulk-end-date').value = twoWeeksLater.toISOString().split('T')[0];
    
    // Default times
    document.getElementById('bulk-start-time').value = '08:00';
    document.getElementById('bulk-end-time').value = '17:00';
    
    // Populate courts select for bulk creation
    populateBulkCourtsSelect();
    
    // Preview button event listener
    document.getElementById('preview-availability-btn').addEventListener('click', function() {
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
        showToast('Warning', 'No slots would be created with current settings. Please check your inputs.', 'error');
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
        
        // Group by court
        const slotsByCourt = {};
        dateSlots.forEach(slot => {
          if (!slotsByCourt[slot.court_name]) {
            slotsByCourt[slot.court_name] = [];
          }
          slotsByCourt[slot.court_name].push(slot);
        });
        
        // Display by court
        for (const [courtName, courtSlots] of Object.entries(slotsByCourt)) {
          const courtHeader = document.createElement('div');
          courtHeader.className = 'text-sm font-medium text-gray-700 ml-2 mb-1';
          courtHeader.textContent = courtName;
          previewSlots.appendChild(courtHeader);
          
          // Sort slots by time
          courtSlots.sort((a, b) => a.start_time.localeCompare(b.start_time));
          
          // Display slots
          courtSlots.forEach(slot => {
            const slotItem = document.createElement('div');
            slotItem.className = 'text-sm mb-1 ml-4';
            slotItem.textContent = `${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}`;
            previewSlots.appendChild(slotItem);
          });
        }
      }
    });
    
    // Show/hide custom duration field
    document.getElementById('bulk-duration').addEventListener('change', function() {
      const customDurationContainer = document.getElementById('custom-duration-container');
      if (this.value === 'custom') {
        customDurationContainer.classList.remove('hidden');
      } else {
        customDurationContainer.classList.add('hidden');
      }
    });
    
    // Bulk availability form submission
    document.getElementById('bulk-availability-form').addEventListener('submit', async function(e) {
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
        
        // Hide preview
        document.getElementById('preview-container').classList.add('hidden');
        document.getElementById('preview-count').classList.add('hidden');
        
        // Reload availability view
        loadAvailability();
        
        // Update calendar view if it's visible
        const calendarContainer = document.getElementById('availability-calendar');
        if (calendarContainer.innerHTML !== '') {
          const currentDate = new Date();
          generateAvailabilityCalendarView(currentDate.getMonth(), currentDate.getFullYear(), await getAvailability());
        }
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to create availability slots: ${error.message}`, 'error');
      }
    });
    
    // Create template button click handler
    document.getElementById('create-template-btn').addEventListener('click', function() {
      // Show template modal
      document.getElementById('template-modal').classList.remove('hidden');
    });
    
    // Close template modal
    document.querySelectorAll('.close-template-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('template-modal').classList.add('hidden');
      });
    });
    
    // Template form submission
    document.getElementById('template-form').addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const templateName = document.getElementById('template-name').value;
      const templateDescription = document.getElementById('template-description').value;
      
      // Get current form settings
      const formData = {
        name: templateName,
        description: templateDescription,
        settings: {
          days: Array.from(document.querySelectorAll('input[name="days[]"]:checked')).map(cb => parseInt(cb.value)),
          courts: Array.from(document.getElementById('bulk-courts').selectedOptions).map(option => ({
            id: option.value,
            name: option.textContent
          })),
          start_time: document.getElementById('bulk-start-time').value,
          end_time: document.getElementById('bulk-end-time').value,
          duration: document.getElementById('bulk-duration').value === 'custom' 
            ? parseInt(document.getElementById('custom-duration').value) 
            : parseInt(document.getElementById('bulk-duration').value),
          increment: document.getElementById('bulk-increment').value
        }
      };
      
      try {
        showLoading(this);
        await saveAvailabilityTemplate(formData);
        hideLoading(this);
        
        // Close modal
        document.getElementById('template-modal').classList.add('hidden');
        
        showToast('Success', 'Template saved successfully.', 'success');
        
        // Reload templates
        loadAvailabilityTemplates();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to save template: ${error.message}`, 'error');
      }
    });
    
    // Helper function to convert month short name to number (0-based index)
    function getMonthNumberFromShortName(shortName) {
        const months = {
        'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
        'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
        };
        return months[shortName] || 0;
    }

    // Calendar navigation buttons
    document.getElementById('prev-month-btn').addEventListener('click', async function() {
        if (currentCalendarView === 'month') {
        // Existing month navigation code
        const monthYearText = document.getElementById('calendar-month-year').textContent;
        const [monthName, year] = monthYearText.split(' ');
        
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        const monthIndex = monthNames.indexOf(monthName);
        
        let newMonth = monthIndex - 1;
        let newYear = parseInt(year);
        
        if (newMonth < 0) {
            newMonth = 11;
            newYear -= 1;
        }
        
        generateAvailabilityCalendarView(newMonth, newYear, await getAvailability());
        } else {
        // New week navigation code
        const dateRangeText = document.getElementById('calendar-month-year').textContent;
        const startDateStr = dateRangeText.split(' - ')[0];
        
        // Parse the start date
        const dateParts = startDateStr.split(' ');
        const month = getMonthNumberFromShortName(dateParts[0]);
        const day = parseInt(dateParts[1]);
        const year = new Date().getFullYear(); // Assuming current year if not in the string
        
        // Create date object and go back 7 days
        const currentStartDate = new Date(year, month, day);
        currentStartDate.setDate(currentStartDate.getDate() - 7);
        
        // Generate new week view
        generateAvailabilityWeekView(await getAvailability(), currentStartDate);
        }
    });
    
    document.getElementById('next-month-btn').addEventListener('click', async function() {
        if (currentCalendarView === 'month') {
        // Existing month navigation code
        const monthYearText = document.getElementById('calendar-month-year').textContent;
        const [monthName, year] = monthYearText.split(' ');
        
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
        const monthIndex = monthNames.indexOf(monthName);
        
        let newMonth = monthIndex + 1;
        let newYear = parseInt(year);
        
        if (newMonth > 11) {
            newMonth = 0;
            newYear += 1;
        }
        
        generateAvailabilityCalendarView(newMonth, newYear, await getAvailability());
        } else {
        // New week navigation code
        const dateRangeText = document.getElementById('calendar-month-year').textContent;
        const startDateStr = dateRangeText.split(' - ')[0];
        
        // Parse the start date
        const dateParts = startDateStr.split(' ');
        const month = getMonthNumberFromShortName(dateParts[0]);
        const day = parseInt(dateParts[1]);
        const year = new Date().getFullYear(); // Assuming current year if not in the string
        
        // Create date object and go forward 7 days
        const currentStartDate = new Date(year, month, day);
        currentStartDate.setDate(currentStartDate.getDate() + 7);
        
        // Generate new week view
        generateAvailabilityWeekView(await getAvailability(), currentStartDate);
        }
    });
    
    // Toggle between month and week view
    document.getElementById('toggle-calendar-view').addEventListener('click', async function() {
        const calendarContainer = document.getElementById('availability-calendar');

        currentCalendarView = currentCalendarView === 'month' ? 'week' : 'month';
      
        if (currentCalendarView === 'week') {
            this.textContent = 'Switch to Month View';
            // Generate week view
            generateAvailabilityWeekView(await getAvailability());
          } else {
            this.textContent = 'Switch to Week View';
            // Generate month view
            const currentDate = new Date();
            generateAvailabilityCalendarView(currentDate.getMonth(), currentDate.getFullYear(), await getAvailability());
          }
    });
    
    // Initialize calendar view with current month
    document.getElementById('availability-calendar').addEventListener('click', async function() {
      if (this.innerHTML === '') {
        const currentDate = new Date();
        generateAvailabilityCalendarView(currentDate.getMonth(), currentDate.getFullYear(), await getAvailability());
      }
    });
  }
  
  // Function to generate week view
  function generateAvailabilityWeekView(availabilityData, customStartDate = null) {
    const calendarContainer = document.getElementById('availability-calendar');
    calendarContainer.innerHTML = '';
    
    // Get current week
    const today = new Date();

      // Use custom start date if provided, otherwise use start of current week
    let startOfWeek;

    if (customStartDate) {
        startOfWeek = new Date(customStartDate);
    } else {
        const currentDay = today.getDay(); // 0 = Sunday, 1 = Monday, etc.
        startOfWeek = new Date(today);
        startOfWeek.setDate(today.getDate() - currentDay);
    }

    // Calculate end of week (Saturday)
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    // Update month/year display to show week range
    const monthYearDisplay = document.getElementById('calendar-month-year');
    monthYearDisplay.textContent = `${startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
    
    // Create week view table
    const table = document.createElement('table');
    table.className = 'w-full border-collapse';
    
    // Create header row with day names and dates
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    // Add time column header
    const timeHeader = document.createElement('th');
    timeHeader.className = 'p-2 border border-gray-200 bg-gray-50 w-16';
    timeHeader.textContent = 'Time';
    headerRow.appendChild(timeHeader);
    
    // Add day columns headers
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      
      const dayName = day.toLocaleDateString('en-US', { weekday: 'short' });
      const dayDate = day.getDate();
      
      const th = document.createElement('th');
      th.className = 'p-2 border border-gray-200 text-center';
      
      // Highlight today
      if (day.toDateString() === today.toDateString()) {
        th.className += ' bg-blue-50';
      }
      
      th.innerHTML = `${dayName}<br>${dayDate}`;
      headerRow.appendChild(th);
    }
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create table body with time slots
    const tbody = document.createElement('tbody');
    
    // Generate time slots from 6:00 to 22:00 in 30-minute increments
    for (let hour = 6; hour < 22; hour++) {
      for (let minute = 0; minute < 60; minute += 30) {
        const row = document.createElement('tr');
        row.className = 'h-12';
        
        // Time column
        const timeCell = document.createElement('td');
        timeCell.className = 'p-1 border border-gray-200 text-center text-xs bg-gray-50';
        
        const timeStr = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
        timeCell.textContent = timeStr;
        row.appendChild(timeCell);
        
        // Day columns
        for (let day = 0; day < 7; day++) {
          const currentDate = new Date(startOfWeek);
          currentDate.setDate(startOfWeek.getDate() + day);
          
          const dateStr = currentDate.toISOString().split('T')[0];
          
          const cell = document.createElement('td');
          cell.className = 'p-1 border border-gray-200';
          
          // Highlight today's column
          if (currentDate.toDateString() === today.toDateString()) {
            cell.className += ' bg-blue-50';
          }
          
          // Check if there are any availability slots for this date and time
          if (availabilityData && availabilityData.length > 0) {
            const slotsForDateAndTime = availabilityData.filter(slot => {
              return slot.date === dateStr && 
                     slot.start_time <= timeStr && 
                     slot.end_time > timeStr;
            });
            
            if (slotsForDateAndTime.length > 0) {
              cell.className += ' bg-green-100';
              
              // Group by court
              const courts = {};
              slotsForDateAndTime.forEach(slot => {
                if (!courts[slot.court.name]) {
                  courts[slot.court.name] = [];
                }
                courts[slot.court.name].push(slot);
              });
              
              const courtsList = document.createElement('div');
              courtsList.className = 'text-xs';
              
              for (const courtName in courts) {
                const courtBadge = document.createElement('div');
                courtBadge.className = 'bg-green-200 rounded px-1 text-green-800 mb-1 truncate';
                courtBadge.textContent = courtName;
                courtsList.appendChild(courtBadge);
              }
              
              cell.appendChild(courtsList);
              
              // Add click handler to show details
              cell.style.cursor = 'pointer';
              cell.addEventListener('click', () => {
                showTimeSlotDetails(dateStr, timeStr, slotsForDateAndTime);
              });
            }
          }
          
          row.appendChild(cell);
        }
        
        tbody.appendChild(row);
      }
    }
    
    table.appendChild(tbody);
    calendarContainer.appendChild(table);
  }
  
  // Show time slot details in a modal
  function showTimeSlotDetails(date, time, slots) {
    // Create modal to show details
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50';
    
    const content = document.createElement('div');
    content.className = 'bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4';
    
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-4';
    header.innerHTML = `
      <h3 class="text-lg font-semibold">Availability for ${formatDate(date)} at ${formatTime(time)}</h3>
      <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    content.appendChild(header);
    
    // Group slots by court
    const slotsByCourt = {};
    slots.forEach(slot => {
      if (!slotsByCourt[slot.court.name]) {
        slotsByCourt[slot.court.name] = [];
      }
      slotsByCourt[slot.court.name].push(slot);
    });
    
    // Create list of slots
    const slotsList = document.createElement('div');
    slotsList.className = 'max-h-96 overflow-y-auto';
    
    for (const [courtName, courtSlots] of Object.entries(slotsByCourt)) {
      const courtHeader = document.createElement('h4');
      courtHeader.className = 'font-medium text-gray-800 mt-4 mb-2';
      courtHeader.textContent = courtName;
      slotsList.appendChild(courtHeader);
      
      const slotItems = document.createElement('div');
      slotItems.className = 'space-y-2';
      
      courtSlots.forEach(slot => {
        const slotItem = document.createElement('div');
        slotItem.className = 'flex justify-between items-center bg-gray-50 p-2 rounded';
        
        slotItem.innerHTML = `
          <span>${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}</span>
          <button class="text-red-600 hover:text-red-700 delete-availability-btn" data-availability-id="${slot.id}">
            <i class="fas fa-trash"></i>
          </button>
        `;
        
        slotItems.appendChild(slotItem);
      });
      
      slotsList.appendChild(slotItems);
    }
    
    content.appendChild(slotsList);
    
    // Add close button
    const footer = document.createElement('div');
    footer.className = 'mt-6 flex justify-end';
    footer.innerHTML = `
      <button class="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg font-medium hover:bg-gray-300 close-modal">
        Close
      </button>
    `;
    
    content.appendChild(footer);
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Add event listeners to close buttons
    modal.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.body.removeChild(modal);
      });
    });
    
    // Add event listeners to delete buttons
    modal.querySelectorAll('.delete-availability-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const availabilityId = this.getAttribute('data-availability-id');
        document.getElementById('delete-availability-id').value = availabilityId;
        document.getElementById('delete-availability-modal').classList.remove('hidden');
        document.body.removeChild(modal);
      });
    });
  }
  
  // Populate courts select for bulk creation
  function populateBulkCourtsSelect() {
    getCoachCourts().then(courts => {
      const bulkCourtsSelect = document.getElementById('bulk-courts');
      bulkCourtsSelect.innerHTML = '';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        bulkCourtsSelect.appendChild(option);
      });
    }).catch(error => {
      console.error('Error loading courts for bulk select:', error);
    });
  }
  
  // Load and display templates
  async function loadAndDisplayTemplates() {
    try {
      const templates = await loadAvailabilityTemplates();
      const container = document.getElementById('templates-container');
      
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
        const templateCard = document.createElement('div');
        templateCard.className = 'bg-white border border-gray-200 rounded-lg p-4 shadow-sm';
        
        // Format the days
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const days = template.settings.days.map(day => dayNames[day]).join(', ');
        
        // Format courts
        const courts = template.settings.courts.map(court => court.name).join(', ');
        
        templateCard.innerHTML = `
          <div class="flex justify-between">
            <div>
              <h4 class="font-medium">${template.name}</h4>
              <p class="text-gray-500 text-sm">${template.description || 'No description'}</p>
            </div>
            <div class="flex">
              <button class="text-blue-600 hover:text-blue-800 mr-3 apply-template-btn" data-template-id="${template.id}">
                <i class="fas fa-play mr-1"></i> Apply
              </button>
              <button class="text-red-600 hover:text-red-800 delete-template-btn" data-template-id="${template.id}">
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          
          <div class="mt-3 grid grid-cols-2 gap-2 text-sm">
            <div>
              <span class="text-gray-700">Days:</span>
              <span class="ml-1">${days}</span>
            </div>
            <div>
              <span class="text-gray-700">Time:</span>
              <span class="ml-1">${formatTime(template.settings.start_time)} - ${formatTime(template.settings.end_time)}</span>
            </div>
            <div>
              <span class="text-gray-700">Courts:</span>
              <span class="ml-1">${courts}</span>
            </div>
            <div>
              <span class="text-gray-700">Duration:</span>
              <span class="ml-1">${template.settings.duration} min</span>
            </div>
          </div>
        `;
        
        container.appendChild(templateCard);
      });
      
      // Add event listeners to template buttons
      container.querySelectorAll('.apply-template-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const templateId = this.getAttribute('data-template-id');
          showApplyTemplateModal(templateId, templates.find(t => t.id == templateId));
        });
      });
      
      container.querySelectorAll('.delete-template-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const templateId = this.getAttribute('data-template-id');
          if (confirm('Are you sure you want to delete this template?')) {
            deleteTemplate(templateId);
          }
        });
      });
      
    } catch (error) {
      console.error('Error loading templates:', error);
      showToast('Error', 'Failed to load templates.', 'error');
    }
  }
  
  // Show modal to apply template
  function showApplyTemplateModal(templateId, template) {
    // Create modal to select date range
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50';
    
    const content = document.createElement('div');
    content.className = 'bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4';
    
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-4';
    header.innerHTML = `
      <h3 class="text-lg font-semibold">Apply Template: ${template.name}</h3>
      <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    content.appendChild(header);
    
    // Form with date range
    const form = document.createElement('form');
    form.id = 'apply-template-form';
    form.className = 'space-y-4';
    
    const today = new Date().toISOString().split('T')[0];
    
    form.innerHTML = `
      <div>
        <label class="block text-gray-700 font-medium mb-2">Date Range*</label>
        <div class="flex space-x-2">
          <input type="date" id="template-start-date" name="start_date" class="w-full px-4 py-2 border border-gray-300 rounded-lg" required min="${today}" value="${today}" />
          <span class="flex items-center">to</span>
          <input type="date" id="template-end-date" name="end_date" class="w-full px-4 py-2 border border-gray-300 rounded-lg" required min="${today}" />
        </div>
      </div>
      
      <input type="hidden" id="template-id" name="template_id" value="${templateId}" />
      
      <div class="flex justify-end space-x-3 mt-6">
        <button type="button" class="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 focus:outline-none close-modal">
          Cancel
        </button>
        <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none">
          Apply Template
        </button>
      </div>
    `;
    
    content.appendChild(form);
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // Set default end date to 2 weeks later
    const twoWeeksLater = new Date();
    twoWeeksLater.setDate(twoWeeksLater.getDate() + 14);
    document.getElementById('template-end-date').value = twoWeeksLater.toISOString().split('T')[0];
    
    // Add event listeners to close buttons
    modal.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.body.removeChild(modal);
      });
    });
    
    // Add form submit handler
    document.getElementById('apply-template-form').addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const templateId = document.getElementById('template-id').value;
      const startDate = document.getElementById('template-start-date').value;
      const endDate = document.getElementById('template-end-date').value;
      
      try {
        showLoading(this);
        const response = await applyTemplate(templateId, { start: startDate, end: endDate });
        hideLoading(this);
        
        document.body.removeChild(modal);
        
        showToast('Success', `Template applied successfully. Created ${response.created_count} availability slots.`, 'success');
        
        // Reload availability view
        loadAvailability();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to apply template: ${error.message}`, 'error');
      }
    });
  }
  
  // Delete template
  async function deleteTemplate(templateId) {
    try {
      await fetchAPI('/coach/availability/templates/delete', {
        method: 'POST',
        body: JSON.stringify({ template_id: templateId })
      });
      
      showToast('Success', 'Template deleted successfully.', 'success');
      
      // Reload templates
      loadAndDisplayTemplates();
      
    } catch (error) {
      console.error('Error deleting template:', error);
      showToast('Error', `Failed to delete template: ${error.message}`, 'error');
    }
  }
  