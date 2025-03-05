let currentBookingCalendarView = 'month'; // Track current view state globally

// Generate bookings calendar view
function generateBookingsCalendarView(month, year, bookingsData) {
    const calendarContainer = document.getElementById('bookings-calendar');
    calendarContainer.innerHTML = '';
    
    // Update month/year display
    const monthYearDisplay = document.getElementById('cal-month-year');
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
    
    // Group bookings data by date
    const bookingsByDate = {};
    if (bookingsData && bookingsData.length > 0) {
      bookingsData.forEach(booking => {
        // Extract the date part only
        const bookingDate = booking.date.split('T')[0];
        if (!bookingsByDate[bookingDate]) {
          bookingsByDate[bookingDate] = [];
        }
        bookingsByDate[bookingDate].push(booking);
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

          // Add booking info if any exists for this date
          if (bookingsByDate[dateStr] && bookingsByDate[dateStr].length > 0) {
            
            // Color based on status
            const upcomingCount = bookingsByDate[dateStr].filter(b => b.status === 'upcoming').length;
            const completedCount = bookingsByDate[dateStr].filter(b => b.status === 'completed').length;
            const cancelledCount = bookingsByDate[dateStr].filter(b => b.status === 'cancelled').length;
            
            if (upcomingCount > 0) {
                const bookingsCount = document.createElement('div');
                bookingsCount.className = 'text-xs bg-blue-100 rounded p-1 mb-1 text-center text-blue-800';
                bookingsCount.textContent = `${upcomingCount} upcoming`;
                cell.appendChild(bookingsCount);
            } 
            if (completedCount > 0) {
                const bookingsCount = document.createElement('div');
                bookingsCount.className = 'text-xs bg-green-100 rounded p-1 mb-1 text-center text-green-800';
                bookingsCount.textContent = `${completedCount} completed`;
                cell.appendChild(bookingsCount);
            } 
            if (cancelledCount > 0) {
                const bookingsCount = document.createElement('div');
                bookingsCount.className = 'text-xs bg-red-100 rounded p-1 mb-1 text-center text-green-800';
                bookingsCount.textContent = `${cancelledCount} cancelled`;
                cell.appendChild(bookingsCount);
            }
            
            // Add a View button if there are bookings
            const viewButton = document.createElement('button');
            viewButton.className = 'text-xs bg-blue-600 text-white rounded px-2 py-1 hover:bg-blue-700 w-full';
            viewButton.textContent = 'View Bookings';
            viewButton.setAttribute('data-date', dateStr);
            viewButton.addEventListener('click', function() {
              showDateBookings(dateStr, bookingsByDate[dateStr]);
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
  
  // Generate bookings week view
  function generateBookingsWeekView(startDate, bookingsData) {
    const today = new Date();
    const calendarContainer = document.getElementById('bookings-calendar');
    calendarContainer.innerHTML = '';
    
    // Calculate start and end of the week
    const startOfWeek = new Date(startDate);
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    // Update month/year display to show week range
    const monthYearDisplay = document.getElementById('cal-month-year');
    monthYearDisplay.textContent = `${startOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endOfWeek.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
    
    // Rest of the week view generation code...
    
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
    
    // Create table body with time slots (same as original)
  
    // Generate time slots from 6:00 to 22:00 in 60-minute increments
    const tbody = document.createElement('tbody');
    for (let hour = 6; hour < 22; hour++) {
      const row = document.createElement('tr');
      row.className = 'h-16';
      
      // Time column
      const timeCell = document.createElement('td');
      timeCell.className = 'p-1 border border-gray-200 text-center text-xs bg-gray-50';
      
      const timeStr = `${hour.toString().padStart(2, '0')}:00`;
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
        
        // Check if there are any bookings for this date and time
        if (bookingsData && bookingsData.length > 0) {
          const bookingsForDateAndTime = bookingsData.filter(booking => {
            const bookingDate = booking.date.split('T')[0];
            const bookingHour = parseInt(booking.start_time.split(':')[0]);
            return bookingDate === dateStr && bookingHour === hour;
          });
          
          if (bookingsForDateAndTime.length > 0) {
            // Find the statuses of bookings
            const hasUpcoming = bookingsForDateAndTime.some(b => b.status === 'upcoming');
            const hasCompleted = bookingsForDateAndTime.some(b => b.status === 'completed');
            
            if (hasUpcoming) {
              cell.className += ' bg-blue-100';
            } else if (hasCompleted) {
              cell.className += ' bg-green-100';
            }
            
            const bookingsList = document.createElement('div');
            bookingsList.className = 'text-xs';
            
            bookingsForDateAndTime.forEach(booking => {
              const bookingItem = document.createElement('div');
              bookingItem.className = 'rounded px-1 mb-1 truncate';
              
              if (booking.status === 'upcoming') {
                bookingItem.className += ' bg-blue-200 text-blue-800';
              } else if (booking.status === 'completed') {
                bookingItem.className += ' bg-green-200 text-green-800';
              } else if (booking.status === 'cancelled') {
                bookingItem.className += ' bg-red-200 text-red-800';
              }
              
              if (IS_COACH) {
                bookingItem.textContent = `${formatTime(booking.start_time)} - ${booking.student.first_name}`;
              } else {
                bookingItem.textContent = `${formatTime(booking.start_time)} - ${booking.coach.user.first_name}`;
              }
              
              bookingsList.appendChild(bookingItem);
            });
            
            cell.appendChild(bookingsList);
            
            // Add click handler to show details
            cell.style.cursor = 'pointer';
            cell.addEventListener('click', () => {
              showDateTimeBookings(dateStr, hour, bookingsForDateAndTime);
            });
          }
        }
        
        row.appendChild(cell);
      }
      
      tbody.appendChild(row);
    }
    
    table.appendChild(tbody);
    calendarContainer.appendChild(table);
  }
  
  // Show bookings for a specific date
  function showDateBookings(date, bookings) {
    // Create a modal to show the details
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50';
    
    const content = document.createElement('div');
    content.className = 'bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4';
    
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-4';
    header.innerHTML = `
      <h3 class="text-lg font-semibold">Bookings for ${formatDate(date)}</h3>
      <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
        <i class="fas fa-times"></i>
      </button>
    `;
    
    content.appendChild(header);
    
    // Group bookings by status
    const upcomingBookings = bookings.filter(b => b.status === 'upcoming');
    const completedBookings = bookings.filter(b => b.status === 'completed');
    const cancelledBookings = bookings.filter(b => b.status === 'cancelled');
    
    // Create list of bookings grouped by status
    const bookingsList = document.createElement('div');
    bookingsList.className = 'max-h-96 overflow-y-auto';
    
    // Show upcoming bookings
    if (upcomingBookings.length > 0) {
      const upcomingHeader = document.createElement('h4');
      upcomingHeader.className = 'font-medium text-blue-800 mt-4 mb-2';
      upcomingHeader.textContent = 'Upcoming';
      bookingsList.appendChild(upcomingHeader);
      
      const upcomingItems = document.createElement('div');
      upcomingItems.className = 'space-y-2';
      
      // Sort bookings by time
      upcomingBookings.sort((a, b) => a.start_time.localeCompare(b.start_time));
      
      upcomingBookings.forEach(booking => {
            const bookingItem = document.createElement('div');
            bookingItem.className = 'flex justify-between items-center bg-blue-50 p-2 rounded';
            
            if (IS_COACH) {
                const venueStatus = booking.venue_confirmed ? 
                `<div class="my-3 px-3 py-1.5 rounded-md bg-green-100 border border-green-300 text-green-700 text-sm mt-1"><i class="fas fa-check-circle"></i> Venue Confirmed</div>` : 
                `<button class="my-3 px-3 py-1.5 rounded-md bg-red-100 border border-red-300 text-red-700 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 text-sm font-medium flex items-center space-x-1.5 transition-colors confirm-venue-btn" data-booking-id="${booking.id}">
                    <i class="fas fa-exclamation-circle"></i>
                    <span>Please Book and Confirm Venue</span>
                </button>`;
              
              const actionButtons = `
                <div class="flex space-x-3 mt-1">
                  <button class="text-blue-600 hover:text-blue-800 complete-booking-btn" data-booking-id="${booking.id}" title="Complete">
                    <i class="fas fa-check-circle"></i> Complete
                  </button>
                  <button class="text-yellow-600 hover:text-yellow-800 defer-booking-btn" data-booking-id="${booking.id}" title="Reschedule">
                    <i class="fas fa-clock"></i> Reschedule
                  </button>
                  <button class="text-red-600 hover:text-red-800 cancel-booking-btn" data-booking-id="${booking.id}" title="Cancel">
                    <i class="fas fa-times-circle"></i> Cancel
                  </button>
                </div>
              `;
              
              bookingItem.innerHTML = `
                <div>
                  <div><span class="font-medium">${booking.student.first_name} ${booking.student.last_name}</span></div>
                  <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
                  <div class="text-sm text-gray-600">${booking.court.name}</div>
                  ${venueStatus}
                  ${actionButtons}
                </div>
              `;
        } else {
          bookingItem.innerHTML = `
            <div>
              <div><span class="font-medium">${booking.coach.user.first_name} ${booking.coach.user.last_name}</span></div>
              <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
              <div class="text-sm text-gray-600">${booking.court.name}</div>
            </div>
            <div>
              <button class="text-red-600 hover:text-red-800 request-cancel-btn" data-booking-id="${booking.id}">
                <i class="fas fa-times-circle"></i>
              </button>
            </div>
          `;
        }
        
        upcomingItems.appendChild(bookingItem);
      });
      
      bookingsList.appendChild(upcomingItems);
    }
    
    // Show completed bookings
    if (completedBookings.length > 0) {
      const completedHeader = document.createElement('h4');
      completedHeader.className = 'font-medium text-green-800 mt-4 mb-2';
      completedHeader.textContent = 'Completed';
      bookingsList.appendChild(completedHeader);
      
      const completedItems = document.createElement('div');
      completedItems.className = 'space-y-2';
      
      // Sort bookings by time
      completedBookings.sort((a, b) => a.start_time.localeCompare(b.start_time));
      
      completedBookings.forEach(booking => {
        const bookingItem = document.createElement('div');
        bookingItem.className = 'flex justify-between items-center bg-green-50 p-2 rounded';
        
        let buttonHtml = '';
        if (booking.session_log) {
          buttonHtml = `
            <button class="text-blue-600 hover:text-blue-800 view-log-btn" data-booking-id="${booking.id}" data-log-id="${booking.session_log.id}">
              <i class="fas fa-clipboard-list"></i>
            </button>
          `;
        }
        
        if (IS_COACH) {
          bookingItem.innerHTML = `
            <div>
              <div><span class="font-medium">${booking.student.first_name} ${booking.student.last_name}</span></div>
              <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
              <div class="text-sm text-gray-600">${booking.court.name}</div>
            </div>
            <div>
              ${buttonHtml}
            </div>
          `;
        } else {
          bookingItem.innerHTML = `
            <div>
              <div><span class="font-medium">${booking.coach.user.first_name} ${booking.coach.user.last_name}</span></div>
              <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
              <div class="text-sm text-gray-600">${booking.court.name}</div>
            </div>
            <div>
              ${buttonHtml}
            </div>
          `;
        }
        
        completedItems.appendChild(bookingItem);
      });
      
      bookingsList.appendChild(completedItems);
    }
    
    // Show cancelled bookings
    if (cancelledBookings.length > 0) {
      const cancelledHeader = document.createElement('h4');
      cancelledHeader.className = 'font-medium text-red-800 mt-4 mb-2';
      cancelledHeader.textContent = 'Cancelled';
      bookingsList.appendChild(cancelledHeader);
      
      const cancelledItems = document.createElement('div');
      cancelledItems.className = 'space-y-2';
      
      // Sort bookings by time
      cancelledBookings.sort((a, b) => a.start_time.localeCompare(b.start_time));
      
      cancelledBookings.forEach(booking => {
        const bookingItem = document.createElement('div');
        bookingItem.className = 'flex justify-between items-center bg-red-50 p-2 rounded';
        
        if (IS_COACH) {
          bookingItem.innerHTML = `
            <div>
              <div><span class="font-medium">${booking.student.first_name} ${booking.student.last_name}</span></div>
              <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
              <div class="text-sm text-gray-600">${booking.court.name}</div>
            </div>
          `;
        } else {
          bookingItem.innerHTML = `
            <div>
              <div><span class="font-medium">${booking.coach.user.first_name} ${booking.coach.user.last_name}</span></div>
              <div class="text-sm">${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}</div>
              <div class="text-sm text-gray-600">${booking.court.name}</div>
            </div>
          `;
        }
        
        cancelledItems.appendChild(bookingItem);
      });
      
      bookingsList.appendChild(cancelledItems);
    }
    
    content.appendChild(bookingsList);
    
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
    
    // Add event listeners
    addBookingModalEventListeners(modal);
  }
  
  // Show bookings for a specific date and hour
  function showDateTimeBookings(date, hour, bookings) {
    // Similar to showDateBookings, but filtered for the specific hour
    showDateBookings(date, bookings);
  }
  
  // Add event listeners to booking modal elements
  function addBookingModalEventListeners(modal) {
    // Close button
    modal.querySelectorAll('.close-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.body.removeChild(modal);
      });
    });
    
    // Session log view button
    modal.querySelectorAll('.view-log-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        const logId = this.getAttribute('data-log-id');
        document.body.removeChild(modal);
        openSessionLogModal(bookingId, logId);   

      });
    });
    
    // For coach actions
    if (IS_COACH) {
      // Complete booking button
      modal.querySelectorAll('.complete-booking-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          document.body.removeChild(modal);
          showCompleteBookingModal(bookingId);
        });
      });
      
      // Confirm venue button
      modal.querySelectorAll('.confirm-venue-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          document.body.removeChild(modal);
          showConfirmVenueModal(bookingId);
        });
      });
      
      // Defer booking button
      modal.querySelectorAll('.defer-booking-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          document.body.removeChild(modal);
          showDeferBookingModal(bookingId);
        });
      });
      
      // Cancel booking button
      modal.querySelectorAll('.cancel-booking-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const bookingId = this.getAttribute('data-booking-id');
          document.body.removeChild(modal);
          document.getElementById('cancel-booking-id').value = bookingId;
          document.getElementById('cancel-session-modal').classList.remove('hidden');
        });
      });
    } else {
      // Request cancel button for students
      modal.querySelectorAll('.request-cancel-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          // For now, just show a toast message that cancellation is not implemented yet
          showToast('Information', 'Cancellation requests are not implemented yet.', 'info');
        });
      });
    }
  }
  
  // Add these API functions for coach actions
  async function completeBooking(bookingId) {
    return fetchAPI('/coach/complete-session', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId })
    });
  }
  
  async function confirmVenueBooking(bookingId) {
    return fetchAPI('/coach/confirm-venue', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId })
    });
  }
  
  async function deferBooking(deferData) {
    return fetchAPI('/coach/defer-booking', {
      method: 'POST',
      body: JSON.stringify(deferData)
    });
  }
  
  // Load bookings for the calendar
  async function loadCalendarView() {
    currentBookingCalendarView = 'month';
    document.getElementById('toggle-cal-view').textContent = 'Switch to Week View';

    const today = new Date();
    const bookingsData = await loadBookingsForMonth(today.getMonth(), today.getFullYear());
    generateBookingsCalendarView(today.getMonth(), today.getFullYear(), bookingsData);

    // Update navigation buttons to handle month navigation
    updateCalendarNavigationForMonths();
  }
  
  // Load bookings for a specific month/year
  async function loadBookingsForMonth(month, year) {
    // Create date range for the month
    const startDate = new Date(year, month, 1);
    const endDate = new Date(year, month + 1, 0);
    
    // Format dates as required by API
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    try {
      // This assumes an API endpoint that can filter by date range
      // You might need to adjust this based on your actual API endpoints
      let bookings = [];
      
      // For now, get all bookings and filter client-side
      const upcomingBookings = await getBookings('upcoming');
      const completedBookings = await getBookings('completed');
      const cancelledBookings = await getBookings('cancelled');
      
      bookings = [...upcomingBookings, ...completedBookings, ...cancelledBookings];
      
      // Filter bookings for the selected month
      return bookings.filter(booking => {
        const bookingDate = new Date(booking.date);
        return bookingDate >= startDate && bookingDate <= endDate;
      });
    } catch (error) {
      console.error('Error loading bookings for calendar:', error);
      showToast('Error', 'Failed to load bookings for calendar view.', 'error');
      return [];
    }
  }
  
  // Load all bookings for the calendar
  async function loadAllBookings() {
    try {
      const upcomingBookings = await getBookings('upcoming');
      const completedBookings = await getBookings('completed');
      const cancelledBookings = await getBookings('cancelled');
      
      return [...upcomingBookings, ...completedBookings, ...cancelledBookings];
    } catch (error) {
      console.error('Error loading bookings for calendar:', error);
      showToast('Error', 'Failed to load bookings for calendar view.', 'error');
      return [];
    }
  }
  

// Add these functions to manage navigation buttons based on view state
function updateCalendarNavigationForMonths() {
  // Remove any existing event listeners
  const prevBtn = document.getElementById('cal-prev-month-btn');
  const nextBtn = document.getElementById('cal-next-month-btn');
  
  // Clone and replace the buttons to remove old event listeners
  const newPrevBtn = prevBtn.cloneNode(true);
  const newNextBtn = nextBtn.cloneNode(true);
  prevBtn.parentNode.replaceChild(newPrevBtn, prevBtn);
  nextBtn.parentNode.replaceChild(newNextBtn, nextBtn);
  
  // Add month-based navigation
  newPrevBtn.addEventListener('click', async function() {
    const monthYearText = document.getElementById('cal-month-year').textContent;
    const [monthName, year] = monthYearText.split(' ');
    
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const monthIndex = monthNames.indexOf(monthName);
    
    let newMonth = monthIndex - 1;
    let newYear = parseInt(year);
    
    if (newMonth < 0) {
      newMonth = 11;
      newYear -= 1;
    }
    
    const bookingsData = await loadBookingsForMonth(newMonth, newYear);
    generateBookingsCalendarView(newMonth, newYear, bookingsData);
  });
  
  newNextBtn.addEventListener('click', async function() {
    const monthYearText = document.getElementById('cal-month-year').textContent;
    const [monthName, year] = monthYearText.split(' ');
    
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const monthIndex = monthNames.indexOf(monthName);
    
    let newMonth = monthIndex + 1;
    let newYear = parseInt(year);
    
    if (newMonth > 11) {
      newMonth = 0;
      newYear += 1;
    }
    
    const bookingsData = await loadBookingsForMonth(newMonth, newYear);
    generateBookingsCalendarView(newMonth, newYear, bookingsData);
  });
}

// Helper function to get current week range from display
function getWeekRangeFromDisplay(){
  // Get current week range from display
  const monthYearText = document.getElementById('cal-month-year').textContent;
  // Example format: "Apr 15 - Apr 21, 2025"
  const dateRangeRegex = /(\w+)\s+(\d+)\s+-\s+(\w+)\s+(\d+),\s+(\d+)/;
  const match = monthYearText.match(dateRangeRegex);
  
  /*
  if (!match) {
    // If can't parse, use current week
    const today = new Date();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());
    
    generateBookingsWeekView(startOfWeek);
    return;
  }
  */

  const startMonth = match[1];
  const startDay = parseInt(match[2]);
  const endMonth = match[3];
  const endDay = parseInt(match[4]);
  const year = parseInt(match[5]);
  
  // Month name to number mapping
  const monthMap = {
    'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
    'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
  };

  const startOfWeek = new Date(year, monthMap[startMonth], startDay);
  return startOfWeek;
}

// Function to handle week-based navigation
function updateCalendarNavigationForWeeks() {
  // Remove any existing event listeners
  const prevBtn = document.getElementById('cal-prev-month-btn');
  const nextBtn = document.getElementById('cal-next-month-btn');
  
  // Clone and replace the buttons to remove old event listeners
  const newPrevBtn = prevBtn.cloneNode(true);
  const newNextBtn = nextBtn.cloneNode(true);
  prevBtn.parentNode.replaceChild(newPrevBtn, prevBtn);
  nextBtn.parentNode.replaceChild(newNextBtn, nextBtn);
  
  // Add event listeners for week navigation
  newPrevBtn.addEventListener('click', async function() {
    // Create a date object for the start of the week
    const startOfWeek = getWeekRangeFromDisplay();
    
    // Go to previous week
    const prevWeek = new Date(startOfWeek);
    prevWeek.setDate(prevWeek.getDate() - 7);
    
    const bookingsData = await loadAllBookings();
    generateBookingsWeekView(prevWeek, bookingsData);
  });
  
  newNextBtn.addEventListener('click', async function() {
    // Create a date object for the start of the week
    const startOfWeek = getWeekRangeFromDisplay();

    // Go to next week
    const nextWeek = new Date(startOfWeek);
    nextWeek.setDate(nextWeek.getDate() + 7);
    
    const bookingsData = await loadAllBookings();
    generateBookingsWeekView(nextWeek, bookingsData);
  });
}

// Update initCalendarView function to initialize the correct navigation mode
async function initCalendarView() {
  // Set today's date for default view
  const today = new Date();
  
  // Initial load of calendar - month view is default
  currentBookingCalendarView = 'month';
  const bookingsData = await loadBookingsForMonth(today.getMonth(), today.getFullYear());
  generateBookingsCalendarView(today.getMonth(), today.getFullYear(), bookingsData);
  
  // Set up month navigation initially
  updateCalendarNavigationForMonths();
  
  // Toggle view button event
  document.getElementById('toggle-cal-view').addEventListener('click', async function() {
    if (currentBookingCalendarView === 'month') {
        // Switch to week view
        currentBookingCalendarView = 'week';
        this.textContent = 'Switch to Month View';
      
        // Generate week view
        // Start with current week
        const startOfWeek = new Date(today);
        startOfWeek.setDate(today.getDate() - today.getDay());
        generateBookingsWeekView(startOfWeek, bookingsData);
        
        // Update navigation buttons to handle week navigation
        updateCalendarNavigationForWeeks();

    } else {
        // Switch to month view
        currentBookingCalendarView = 'month';
        this.textContent = 'Switch to Week View';
        
        // Generate month view
        const bookingsData = await loadBookingsForMonth(today.getMonth(), today.getFullYear());
        generateBookingsCalendarView(today.getMonth(), today.getFullYear(), bookingsData);
        
        // Update navigation buttons to handle month navigation
        updateCalendarNavigationForMonths();
    }
  });
  
}
