// app/static/js/coach/calendar.js
// Initialize calendar view
function initCalendarView() {
    // Month navigation
    document.getElementById('cal-prev-month-btn')?.addEventListener('click', function() {
      const monthYearText = document.getElementById('cal-month-year').textContent;
      const [monthName, year] = monthYearText.split(' ');
      
      const monthIndex = new Date(`${monthName} 1, ${year}`).getMonth();
      const currentYear = parseInt(year);
      
      let newMonth = monthIndex - 1;
      let newYear = currentYear;
      
      if (newMonth < 0) {
        newMonth = 11;
        newYear--;
      }
      
      generateBookingsCalendarView(newMonth, newYear);
    });
    
    document.getElementById('cal-next-month-btn')?.addEventListener('click', function() {
      const monthYearText = document.getElementById('cal-month-year').textContent;
      const [monthName, year] = monthYearText.split(' ');
      
      const monthIndex = new Date(`${monthName} 1, ${year}`).getMonth();
      const currentYear = parseInt(year);
      
      let newMonth = monthIndex + 1;
      let newYear = currentYear;
      
      if (newMonth > 11) {
        newMonth = 0;
        newYear++;
      }
      
      generateBookingsCalendarView(newMonth, newYear);
    });
    
    // Toggle view
    document.getElementById('toggle-cal-view')?.addEventListener('click', function() {
      const isWeekView = this.textContent.includes('Month');
      
      if (isWeekView) {
        this.textContent = 'Switch to Week View';
        generateBookingsCalendarView(new Date().getMonth(), new Date().getFullYear());
      } else {
        this.textContent = 'Switch to Month View';
        generateBookingsWeekView();
      }
    });
  }
  
  // Load calendar view data
  async function loadCalendarView() {
    try {
      const bookings = await getBookings('all');
      const currentDate = new Date();
      
      generateBookingsCalendarView(currentDate.getMonth(), currentDate.getFullYear(), bookings);
    } catch (error) {
      console.error('Error loading calendar view:', error);
      showToast('Error', 'Failed to load calendar data.', 'error');
    }
  }
  
  // Generate bookings calendar view
  function generateBookingsCalendarView(month, year, bookings = []) {
    const calendarContainer = document.getElementById('bookings-calendar');
    if (!calendarContainer) return;
    
    // Update month/year display
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('cal-month-year').textContent = `${monthNames[month]} ${year}`;
    
    // Generate calendar days
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay(); // 0 = Sunday, 1 = Monday, etc.
    
    // Create calendar header
    let calendarHTML = `
      <div class="grid grid-cols-7 gap-1 mb-1">
        <div class="text-center py-2 text-sm font-medium text-gray-600">Sun</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Mon</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Tue</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Wed</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Thu</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Fri</div>
        <div class="text-center py-2 text-sm font-medium text-gray-600">Sat</div>
      </div>
      <div class="grid grid-cols-7 gap-1">
    `;
    
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startingDayOfWeek; i++) {
      calendarHTML += `<div class="bg-gray-100 p-2 rounded-lg min-h-24"></div>`;
    }
    
    // Group bookings by date
    const bookingsByDate = {};
    bookings.forEach(booking => {
      const bookingDate = new Date(booking.date);
      if (bookingDate.getMonth() === month && bookingDate.getFullYear() === year) {
        const day = bookingDate.getDate();
        if (!bookingsByDate[day]) {
          bookingsByDate[day] = [];
        }
        bookingsByDate[day].push(booking);
      }
    });
    
    // Add days of the month
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(year, month, day);
      const isToday = date.toDateString() === new Date().toDateString();
      const dayBookings = bookingsByDate[day] || [];
      
      calendarHTML += `
        <div class="${isToday ? 'bg-blue-50 border border-blue-200' : 'bg-white border border-gray-200'} p-2 rounded-lg min-h-24 relative">
          <div class="text-right ${isToday ? 'font-bold text-blue-600' : 'text-gray-700'}">${day}</div>
          <div class="day-bookings mt-1 overflow-y-auto max-h-20">
      `;
      
      if (dayBookings.length > 0) {
        dayBookings.forEach(booking => {
          const startTime = formatTime(booking.start_time);
          
          let statusColor = '';
          if (booking.status === 'completed') {
            statusColor = 'bg-green-100 text-green-800';
          } else if (booking.status === 'cancelled') {
            statusColor = 'bg-red-100 text-red-800';
          } else {
            statusColor = 'bg-blue-100 text-blue-800';
          }
          
          calendarHTML += `
            <div class="text-xs mb-1 p-1 rounded ${statusColor} truncate" title="${booking.student.first_name} ${booking.student.last_name} - ${startTime}">
              ${startTime} - ${booking.student.first_name} ${booking.student.last_name.charAt(0)}.
            </div>
          `;
        });
      }
      
      calendarHTML += `
          </div>
        </div>
      `;
    }
    
    // Add empty cells for days after the last day of the month
    const lastDayOfWeek = lastDay.getDay();
    const emptyCellsAfter = 6 - lastDayOfWeek;
    
    for (let i = 0; i < emptyCellsAfter; i++) {
      calendarHTML += `<div class="bg-gray-100 p-2 rounded-lg min-h-24"></div>`;
    }
    
    calendarHTML += `</div>`;
    
    // Update the calendar container
    calendarContainer.innerHTML = calendarHTML;
  }
  
  // Export functions
  export {
    initCalendarView,
    loadCalendarView,
    generateBookingsCalendarView
  };