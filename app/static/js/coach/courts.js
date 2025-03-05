// app/static/js/coach/courts.js
// Load courts data
async function loadCourts() {
    try {
      // Get all courts
      const courts = await getCourts();
      
      // Get coach courts
      const coachCourts = await getCoachCourts();
      
      // Populate court select in court modal
      const courtSelect = document.getElementById('court-select');
      if (courtSelect) {
        courtSelect.innerHTML = '<option value="">Select a court</option>';
        
        // Filter out courts the coach is already associated with
        const availableCourts = courts.filter(court => 
          !coachCourts.some(coachCourt => coachCourt.id === court.id)
        );
        
        availableCourts.forEach(court => {
          const option = document.createElement('option');
          option.value = court.id;
          option.textContent = `${court.name} - ${court.address}, ${court.city}`;
          courtSelect.appendChild(option);
        });
      }
      
      // Populate coach courts list
      const courtsContainer = document.getElementById('my-courts-list');
      if (!courtsContainer) return;
      
      if (coachCourts.length === 0) {
        courtsContainer.innerHTML = `
          <div class="text-center py-6 text-gray-500">
            <p>No courts added yet</p>
          </div>
        `;
        return;
      }
      
      courtsContainer.innerHTML = '';
      
      coachCourts.forEach(court => {
        const courtCard = document.createElement('div');
        courtCard.className = 'bg-gray-50 rounded-lg p-4 flex justify-between items-center';
        courtCard.innerHTML = `
          <div>
            <h4 class="font-medium">${court.name}</h4>
            <p class="text-gray-500 text-sm">${court.address}, ${court.city}, ${court.state} ${court.zip_code}</p>
          </div>
          <button class="text-red-600 hover:text-red-700 remove-court-btn" data-court-id="${court.id}">
            <i class="fas fa-trash"></i>
          </button>
        `;
        courtsContainer.appendChild(courtCard);
      });
      
      // Add event listeners to remove buttons
      document.querySelectorAll('.remove-court-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const courtId = this.getAttribute('data-court-id');
          document.getElementById('remove-court-id').value = courtId;
          document.getElementById('remove-court-modal').classList.remove('hidden');
        });
      });
      
      // Populate court filters in other forms
      populateCourtFilters(coachCourts);
      
    } catch (error) {
      console.error('Error loading courts:', error);
      showToast('Error', 'Failed to load courts data.', 'error');
    }
  }
  
  // Populate court filters in various forms
  function populateCourtFilters(courts) {
    // Availability court select
    const availabilityCourt = document.getElementById('availability-court');
    if (availabilityCourt) {
      availabilityCourt.innerHTML = '<option value="">Select a court</option>';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        availabilityCourt.appendChild(option);
      });
    }
    
    // Availability filter
    const availabilityFilter = document.getElementById('availability-filter-court');
    if (availabilityFilter) {
      availabilityFilter.innerHTML = '<option value="">All Courts</option>';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        availabilityFilter.appendChild(option);
      });
    }
    
    // Bookings filters
    const upcomingFilter = document.getElementById('upcoming-filter-court');
    const completedFilter = document.getElementById('completed-filter-court');
    const cancelledFilter = document.getElementById('cancelled-filter-court');
    
    [upcomingFilter, completedFilter, cancelledFilter].forEach(filter => {
      if (!filter) return;
      
      filter.innerHTML = '<option value="">All Courts</option>';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        filter.appendChild(option);
      });
    });
    
    // Session logs filter
    const sessionLogsFilter = document.getElementById('session-logs-filter-court');
    if (sessionLogsFilter) {
      sessionLogsFilter.innerHTML = '<option value="">All Courts</option>';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        sessionLogsFilter.appendChild(option);
      });
    }
    
    // Bulk add courts select
    const bulkCourts = document.getElementById('bulk-courts');
    if (bulkCourts) {
      bulkCourts.innerHTML = '';
      
      courts.forEach(court => {
        const option = document.createElement('option');
        option.value = court.id;
        option.textContent = court.name;
        bulkCourts.appendChild(option);
      });
    }
  }
  
  // Export functions
  export {
    loadCourts,
    populateCourtFilters
  };