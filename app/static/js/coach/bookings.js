// app/static/js/coach/bookings.js
// Setup booking tabs
function setupBookingTabs() {
    const upcomingBtn = document.getElementById('upcoming-tab-btn');
    const completedBtn = document.getElementById('completed-tab-btn');
    const cancelledBtn = document.getElementById('cancelled-tab-btn');
    
    if (!upcomingBtn || !completedBtn || !cancelledBtn) return;
    
    const upcomingTab = document.getElementById('upcoming-bookings-tab');
    const completedTab = document.getElementById('completed-bookings-tab');
    const cancelledTab = document.getElementById('cancelled-bookings-tab');
    
    upcomingBtn.addEventListener('click', function() {
      // Update button styles
      upcomingBtn.classList.add('text-blue-600', 'border-blue-600');
      upcomingBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      completedBtn.classList.remove('text-blue-600', 'border-blue-600');
      completedBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      cancelledBtn.classList.remove('text-blue-600', 'border-blue-600');
      cancelledBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      // Show/hide tabs
      upcomingTab.classList.remove('hidden');
      upcomingTab.classList.add('active');
      
      completedTab.classList.add('hidden');
      completedTab.classList.remove('active');
      
      cancelledTab.classList.add('hidden');
      cancelledTab.classList.remove('active');
    });
    
    completedBtn.addEventListener('click', function() {
      // Update button styles
      completedBtn.classList.add('text-blue-600', 'border-blue-600');
      completedBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      upcomingBtn.classList.remove('text-blue-600', 'border-blue-600');
      upcomingBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      cancelledBtn.classList.remove('text-blue-600', 'border-blue-600');
      cancelledBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      // Show/hide tabs
      completedTab.classList.remove('hidden');
      completedTab.classList.add('active');
      
      upcomingTab.classList.add('hidden');
      upcomingTab.classList.remove('active');
      
      cancelledTab.classList.add('hidden');
      cancelledTab.classList.remove('active');
    });
    
    cancelledBtn.addEventListener('click', function() {
      // Update button styles
      cancelledBtn.classList.add('text-blue-600', 'border-blue-600');
      cancelledBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      upcomingBtn.classList.remove('text-blue-600', 'border-blue-600');
      upcomingBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      completedBtn.classList.remove('text-blue-600', 'border-blue-600');
      completedBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      // Show/hide tabs
      cancelledTab.classList.remove('hidden');
      cancelledTab.classList.add('active');
      
      upcomingTab.classList.add('hidden');
      upcomingTab.classList.remove('active');
      
      completedTab.classList.add('hidden');
      completedTab.classList.remove('active');
    });
  
    // Add search and filter functionality
    document.getElementById('upcoming-search')?.addEventListener('input', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('completed-search')?.addEventListener('input', function() {
      filterBookings('completed');
    });
    
    document.getElementById('cancelled-search')?.addEventListener('input', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('upcoming-filter-court')?.addEventListener('change', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('completed-filter-court')?.addEventListener('change', function() {
      filterBookings('completed');
    });
    
    document.getElementById('cancelled-filter-court')?.addEventListener('change', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('upcoming-sort')?.addEventListener('change', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('completed-sort')?.addEventListener('change', function() {
      filterBookings('completed');
    });
    
    document.getElementById('cancelled-sort')?.addEventListener('change', function() {
      filterBookings('cancelled');
    });
  }
  
  // Load bookings data
  async function loadBookings() {
    try {
      // Load upcoming bookings
      const upcomingBookings = await getBookings('upcoming');
  
      upcomingBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        
        if (document.getElementById(`upcoming-sort`).value === 'date-asc') {
          return dateA - dateB;
        } else {
          return dateB - dateA;
        }
      });
  
      originalBookingsData.upcoming = upcomingBookings;
      displayBookings(upcomingBookings, 'upcoming');
      
      // Load completed bookings
      const completedBookings = await getBookings('completed');
  
      completedBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        
        if (document.getElementById(`completed-sort`).value === 'date-asc') {
          return dateA - dateB;
        } else {
          return dateB - dateA;
        }
      });
  
      originalBookingsData.completed = completedBookings;
      displayBookings(completedBookings, 'completed');
      
      // Load cancelled bookings
      const cancelledBookings = await getBookings('cancelled');
  
      cancelledBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        
        if (document.getElementById(`cancelled-sort`).value === 'date-asc') {
          return dateA - dateB;
        } else {
          return dateB - dateA;
        }
      });
  
      originalBookingsData.cancelled = cancelledBookings;
      displayBookings(cancelledBookings, 'cancelled');
      
      // Update upcoming bookings on dashboard
      updateUpcomingBookingsList(upcomingBookings.slice(0, 3));
      
    } catch (error) {
      console.error('Error loading bookings:', error);
      showToast('Error', 'Failed to load bookings data.', 'error');
    }
  }
  
  // Display bookings in the respective containers
  function displayBookings(bookings, status) {
    const container = document.getElementById(`${status}-bookings-container`);
    
    if (!bookings || bookings.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No ${status} bookings found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    bookings.forEach(booking => {
      const bookingCard = document.createElement('div');
      bookingCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
      
      // Add data attributes for DOM filtering if needed later
      bookingCard.dataset.courtId = booking.court.id;
      bookingCard.dataset.date = booking.date;
      
      // Format date and time
      const bookingDate = formatDate(booking.date);
      const startTime = formatTime(booking.start_time);
      const endTime = formatTime(booking.end_time);
      
      // Handle venue confirmation status
      let venueStatusHtml = '';
      if (status === 'upcoming') {
        if (IS_COACH) {
          venueStatusHtml = booking.venue_confirmed ? 
            `<div class="mt-3 px-3 py-1.5 rounded-md bg-green-100 border border-green-300 text-green-700 text-sm"><i class="fas fa-check-circle mr-1"></i> Venue Confirmed</div>` : 
            `<button class="mt-3 px-3 py-1.5 rounded-md bg-red-100 border border-red-300 text-red-700 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 text-sm font-medium flex items-center space-x-1.5 transition-colors confirm-venue-btn" data-booking-id="${booking.id}">
              <i class="fas fa-exclamation-circle mr-1"></i>
              <span>Please Book and Confirm Venue</span>
            </button>`;
        }
      }
  
      let actionsHtml = '';
      
      if (status === 'upcoming') {
        actionsHtml = `
          <div class="flex flex-wrap gap-2 mt-4">
            <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 complete-session-btn" data-booking-id="${booking.id}">
              <i class="fas fa-check-circle mr-1"></i> Complete
            </button>
            <button class="bg-yellow-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-yellow-700 reschedule-session-btn" data-booking-id="${booking.id}">
              <i class="fas fa-clock mr-1"></i> Reschedule
            </button>
            <button class="bg-red-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-red-700 cancel-session-btn" data-booking-id="${booking.id}">
              <i class="fas fa-times-circle mr-1"></i> Cancel
            </button>
          </div>
        `;
      } 
      else if (status === 'completed') {
        const hasSessionLog = booking.session_log !== null;
        
        actionsHtml = `
          <div class="flex space-x-2 mt-4">
            <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 edit-log-btn" data-booking-id="${booking.id}" data-log-id="${hasSessionLog ? booking.session_log.id : ''}">
              <i class="fas fa-clipboard-list mr-1"></i> ${hasSessionLog ? 'Edit Log' : 'Add Log'}
            </button>
          </div>
        `;
      }
      
      bookingCard.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${booking.student.first_name} ${booking.student.last_name}</h3>
            <p class="text-gray-500 text-sm">Student</p>
          </div>
          <div class="text-right">
            <span class="font-semibold">${formatCurrency(booking.price)}</span>
            <p class="text-gray-500 text-sm">${booking.pricing_plan ? 'Discount Applied' : 'Regular Rate'}</p>
          </div>
        </div>
        
        <div class="flex items-center mt-3 text-gray-600">
          <i class="fas fa-calendar-day mr-2"></i>
          <span>${bookingDate}</span>
        </div>
        
        <div class="flex items-center mt-1 text-gray-600">
          <i class="fas fa-clock mr-2"></i>
          <span>${startTime} - ${endTime}</span>
        </div>
        
        <div class="flex items-center mt-1 text-gray-600">
          <i class="fas fa-map-marker-alt mr-2"></i>
          <span>${booking.court.name}</span>
        </div>
        
        ${venueStatusHtml}
        ${actionsHtml}
      `;
      
      container.appendChild(bookingCard);
    });
    
    // Add event listeners for action buttons
    if (status === 'upcoming') {
      // Venue confirmation buttons
      document.querySelectorAll('.confirm-venue-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          showConfirmVenueModal(bookingId);
        });
      });
  
      // Complete session buttons
      document.querySelectorAll('.complete-session-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          showCompleteBookingModal(bookingId);
        });
      });
          
      // Reschedule session buttons
      document.querySelectorAll('.reschedule-session-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          showDeferBookingModal(bookingId);
        });
      });
      
      // Cancel session buttons
      document.querySelectorAll('.cancel-session-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          document.getElementById('cancel-booking-id').value = bookingId;
          document.getElementById('cancel-session-modal').classList.remove('hidden');
        });
      });
    } else if (status === 'completed') {
      // Edit log buttons
      document.querySelectorAll('.edit-log-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
          const bookingId = this.getAttribute('data-booking-id');
          const logId = this.getAttribute('data-log-id');
          
          openSessionLogModal(bookingId, logId);
        });
      });
    }
  }
  
  // Filter bookings based on search and filters for coach dashboard
  function filterBookings(status) {
    const searchInput = document.getElementById(`${status}-search`);
    const courtFilter = document.getElementById(`${status}-filter-court`);
    const sortSelect = document.getElementById(`${status}-sort`);
    
    if (!searchInput || !courtFilter || !sortSelect) return;
    
    const search = searchInput.value.toLowerCase();
    const courtId = courtFilter.value;
    const sortBy = sortSelect.value;
    
    // If no filters and default sort, show original data
    if (!search && !courtId && sortBy === 'date-desc') {
      displayBookings(originalBookingsData[status], status);
      return;
    }
    
    // Clone the original data to avoid modifying it
    let filteredBookings = [...originalBookingsData[status]];
    
    // Apply search filter
    if (search) {
      filteredBookings = filteredBookings.filter(booking => {
        const studentName = `${booking.student.first_name} ${booking.student.last_name}`.toLowerCase();
        const courtName = booking.court.name.toLowerCase();
        
        return studentName.includes(search) || courtName.includes(search);
      });
    }
    
    // Apply court filter
    if (courtId) {
      filteredBookings = filteredBookings.filter(booking => {
        return booking.court.id.toString() === courtId;
      });
    }
    
    // Apply sorting
    filteredBookings.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      
      if (sortBy === 'date-asc') {
        return dateA - dateB;
      } else {
        return dateB - dateA;
      }
    });
    
    // Display the filtered bookings
    displayBookings(filteredBookings, status);
  }
  
  // Update upcoming bookings list on dashboard
  function updateUpcomingBookingsList(bookings) {
    const container = document.getElementById('upcoming-bookings-list');
    
    if (bookings.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No upcoming bookings</p>
        </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  bookings.forEach(booking => {
    const bookingItem = document.createElement('div');
    bookingItem.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
    
    // Format date and time
    const bookingDate = formatDate(booking.date);
    const startTime = formatTime(booking.start_time);
    
    bookingItem.innerHTML = `
      <div>
        <h4 class="font-medium">${booking.student.first_name} ${booking.student.last_name}</h4>
        <p class="text-gray-500 text-sm">${bookingDate} at ${startTime}</p>
      </div>
      <div class="text-right">
        <p class="font-medium">${formatCurrency(booking.price)}</p>
        <p class="text-gray-500 text-sm">${booking.court.name}</p>
      </div>
    `;
    
    container.appendChild(bookingItem);
  });
}

// Function to show complete booking modal
function showCompleteBookingModal(bookingId) {
  document.getElementById('complete-booking-id').value = bookingId;
  document.getElementById('complete-session-modal').classList.remove('hidden');
}

// Function to show confirm venue modal
function showConfirmVenueModal(bookingId) {
  document.getElementById('confirm-venue-booking-id').value = bookingId;
  document.getElementById('confirm-venue-modal').classList.remove('hidden');
}

// Function to show defer (reschedule) booking modal
function showDeferBookingModal(bookingId) {
  // Set the booking ID
  document.getElementById('defer-booking-id').value = bookingId;
  
  // Set min date to today
  const today = new Date().toISOString().split('T')[0];
  document.getElementById('defer-date').min = today;
  document.getElementById('defer-date').value = today;
  
  // Clear other fields
  document.getElementById('defer-start-time').value = '';
  document.getElementById('defer-end-time').value = '';
  document.getElementById('defer-reason').value = '';
  
  // Populate courts dropdown
  getCourts().then(courts => {
    const deferCourt = document.getElementById('defer-court');
    deferCourt.innerHTML = '<option value="">Select a court</option>';
    
    courts.forEach(court => {
      const option = document.createElement('option');
      option.value = court.id;
      option.textContent = court.name;
      deferCourt.appendChild(option);
    });
  }).catch(error => {
    console.error('Error loading courts:', error);
  });
  
  // Show the modal
  document.getElementById('defer-booking-modal').classList.remove('hidden');
}

// Export functions
export {
  setupBookingTabs,
  loadBookings,
  filterBookings,
  displayBookings,
  updateUpcomingBookingsList,
  showCompleteBookingModal,
  showConfirmVenueModal,
  showDeferBookingModal
};