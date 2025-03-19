document.addEventListener('DOMContentLoaded', function() {
    // Initialize availability functionality
    initAvailabilityManagement();
  
    // Set today's date as min for date inputs
    const today = new Date().toISOString().split('T')[0];
    document.querySelectorAll('input[type="date"]').forEach(input => {
      if (!input.min) {
        input.min = today;
      }
    });
  
    // Show/hide custom duration field
    // document.getElementById('bulk-duration')?.addEventListener('change', function() {
    //   const customDurationContainer = document.getElementById('custom-duration-container');
    //   if (this.value === 'custom') {
    //     customDurationContainer.classList.remove('hidden');
    //   } else {
    //     customDurationContainer.classList.add('hidden');
    //   }
    // });
  
    // Academy coach selection for academy managers
    document.getElementById('apply-coach-filter')?.addEventListener('click', function() {
      const coachId = document.getElementById('academy-coach-select').value;
      const currentUrl = new URL(window.location.href);
      
      if (coachId) {
        currentUrl.searchParams.set('coach_id', coachId);
      } else {
        currentUrl.searchParams.delete('coach_id');
      }
      
      window.location.href = currentUrl.toString();
    });
  });
  
  // Initialize availability management
  function initAvailabilityManagement() {
    loadAndDisplayTemplates();

    // Add availability form submission
    const availabilityForm = document.getElementById('availability-form');
    if (availabilityForm) {
      availabilityForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const courtId = formData.get('court_id');
        const date = formData.get('date');
        const startTime = formData.get('start_time');
        const endTime = formData.get('end_time');
        const studentBooksCourt = true;
        
        if (!courtId || !date || !startTime || !endTime) {
          showToast('Error', 'Please fill in all required fields', 'error');
          return;
        }
        
        if (startTime >= endTime) {
          showToast('Error', 'End time must be after start time', 'error');
          return;
        }
        
        try {
          showLoading(this);
          
          await fetchAPI('/coach/availability/add', {
            method: 'POST',
            body: JSON.stringify({
              court_id: courtId,
              date: date,
              start_time: startTime,
              end_time: endTime,
              student_books_court: studentBooksCourt
            })
          });
          
          hideLoading(this);
          showToast('Success', 'Availability slot added successfully', 'success');
          this.reset();
          
          // Reload calendar if visible
          if (document.getElementById('availability-calendar').innerHTML !== '') {
            const calendar = document.getElementById('calendar-month-year').textContent;
            const [month, year] = calendar.split(' ');
            const monthIndex = getMonthIndex(month);
            
            if (monthIndex !== -1) {
              const availabilityData = await getAvailability();
              generateAvailabilityCalendarView(monthIndex, parseInt(year), availabilityData);
            }
          }
          
        } catch (error) {
          hideLoading(this);
          showToast('Error', `Failed to add availability: ${error.message}`, 'error');
        }
      });
    }
    
    // Bulk availability form submission
    const bulkAvailabilityForm = document.getElementById('bulk-availability-form');
    if (bulkAvailabilityForm) {
      bulkAvailabilityForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const slots = calculateAvailabilitySlots();
        
        if (slots.length === 0) {
          showToast('Error', 'No availability slots to create. Please check your settings.', 'error');
          return;
        }
        
        try {
          showLoading(this);
          
          await fetchAPI('/coach/availability/add-bulk', {
            method: 'POST',
            body: JSON.stringify({ slots })
          });
          
          hideLoading(this);
          showToast('Success', `Created ${slots.length} availability slots successfully.`, 'success');
          
          // Hide preview
          document.getElementById('preview-container').classList.add('hidden');
          document.getElementById('preview-count').classList.add('hidden');
          
          // Reset form
          this.reset();
          
          // Reload calendar if visible
          if (document.getElementById('availability-calendar').innerHTML !== '') {
            const calendar = document.getElementById('calendar-month-year').textContent;
            const [month, year] = calendar.split(' ');
            const monthIndex = getMonthIndex(month);
            
            if (monthIndex !== -1) {
              const availabilityData = await getAvailability();
              generateAvailabilityCalendarView(monthIndex, parseInt(year), availabilityData);
            }
          }
          
        } catch (error) {
          hideLoading(this);
          showToast('Error', `Failed to create availability slots: ${error.message}`, 'error');
        }
      });
    }
    
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
            slotItem.className = 'text-sm mb-1 ml-4 flex justify-between';
            
            const bookingResponsibility = slot.student_books_court 
              ? '<span class="text-orange-600">(Student books)</span>' 
              : '<span class="text-green-600">(Coach books)</span>';
              
            slotItem.innerHTML = `
              <span>${formatTime(slot.start_time)} - ${formatTime(slot.end_time)}</span>
              ${bookingResponsibility}
            `;
            
            previewSlots.appendChild(slotItem);
          });
        }
      }
    });

    document.getElementById('confirm-delete-availability-btn').addEventListener('click', async function() {
      const availabilityId = document.getElementById('delete-availability-id').value;
      
      try {
        document.getElementById('delete-availability-modal').classList.add('hidden');
        await deleteAvailability(availabilityId);
        showToast('Success', 'Availability deleted successfully.', 'success');

        // Reload calendar if visible
        if (document.getElementById('availability-calendar').innerHTML !== '') {
          const calendar = document.getElementById('calendar-month-year').textContent;
          const [month, year] = calendar.split(' ');
          const monthIndex = getMonthIndex(month);
          
          if (monthIndex !== -1) {
            const availabilityData = await getAvailability();
            generateAvailabilityCalendarView(monthIndex, parseInt(year), availabilityData);
          }
        }

      } catch (error) {
        showToast('Error', 'Failed to delete availability. Please try again.', 'error');
      }
    });
  }
  
  // Calculate availability slots based on bulk form inputs
  function calculateAvailabilitySlots() {
    const startDate = new Date(document.getElementById('bulk-start-date').value);
    const endDate = new Date(document.getElementById('bulk-end-date').value);
    const selectedDays = Array.from(document.querySelectorAll('input[name="days[]"]:checked')).map(cb => parseInt(cb.value));
    const startTime = document.getElementById('bulk-start-time').value;
    const endTime = document.getElementById('bulk-end-time').value;
    const studentBooksCourt = true;
    
    // Get time slot increment selection
    //const incrementSelect = document.getElementById('bulk-increment');
    let increment = 60;
    
    // If "Based on session duration" is selected, get the duration value
    // if (incrementSelect.value === 'duration') {
    //   const durationSelect = document.getElementById('bulk-duration');
    //   if (durationSelect.value === 'custom') {
    //     increment = parseInt(document.getElementById('custom-duration').value);
    //   } else {
    //     increment = parseInt(durationSelect.value);
    //   }
    // }
    
    // Get session duration
    //const durationSelect = document.getElementById('bulk-duration');
    const duration = 60;
    
    // Selected courts
    const courts = Array.from(document.getElementById('bulk-courts').selectedOptions).map(option => ({
      id: option.value,
      name: option.textContent
    }));
    
    const slots = [];
    
    // Convert start/end times to minutes for calculation
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
            end_time: slotEndTime,
            student_books_court: studentBooksCourt
          });
        }
      }
    }
    
    return slots;
  }
  
  // Helper functions
  function timeStringToMinutes(timeString) {
    const [hours, minutes] = timeString.split(':').map(part => parseInt(part));
    return hours * 60 + minutes;
  }
  
  function minutesToTimeString(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
  }
  
  function getMonthIndex(monthName) {
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    return months.indexOf(monthName);
  }
  
  function formatDate(dateString) {
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
  }
  
  function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const hour12 = hour % 12 || 12;
    return `${hour12}:${minutes} ${ampm}`;
  }