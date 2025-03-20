/**
 * Students tab-specific JavaScript
 */

// Store original data for filtering
let originalStudentsData = [];
let currentStudentPackages = [];
let currentStudentBookings = [];
let currentStudentLogs = [];
let currentStudentId = null;

// Function called when the students tab is activated
function initStudentsTab() {
  // Load students data if not already loaded
  const studentsContainer = document.getElementById('students-container');
  if (studentsContainer && !studentsContainer.dataset.loaded) {
    loadStudents();
    setupStudentsEventListeners();
    studentsContainer.dataset.loaded = 'true';
  }
}

// Load students data from API
async function loadStudents() {
  try {
    // Get all students who have bookings with this coach
    const students = await fetchAPI('/coach/students');
    originalStudentsData = students;
    
    // Sort by name (A-Z) by default
    students.sort((a, b) => {
      const nameA = `${a.first_name} ${a.last_name}`.toLowerCase();
      const nameB = `${b.first_name} ${b.last_name}`.toLowerCase();
      return nameA.localeCompare(nameB);
    });
    
    // Display the students
    displayStudents(students);
  } catch (error) {
    console.error('Error loading students:', error);
    showToast('Error', 'Failed to load students data', 'error');
  }
}

// Display students in cards
function displayStudents(students) {
  const container = document.getElementById('students-container');
  
  if (!container) return;
  
  if (students.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-gray-500 col-span-3">
        <p>No students found</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  students.forEach(student => {
    const studentCard = document.createElement('div');
    studentCard.className = 'bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer';
    studentCard.dataset.studentId = student.id;
    
    // Create profile image or initial
    let profileImage = '';
    if (student.profile_picture) {
      profileImage = `<img src="${student.profile_picture}" alt="${student.first_name}" class="h-12 w-12 rounded-full object-cover">`;
    } else {
      profileImage = `
        <div class="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold text-lg">
          ${student.first_name[0]}
        </div>
      `;
    }
    
    // Format DUPR rating if available
    const duprRating = student.dupr_rating ? student.dupr_rating.toFixed(1) : 'N/A';
    
    // Format availability preferences if available
    let availabilityHTML = '<p class="text-gray-500 text-sm">No availability preferences set</p>';
    
    if (student.availability_preferences) {
      const prefs = student.availability_preferences;
      
      if (prefs.days && prefs.days.length > 0) {
        const dayNames = {
          0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'
        };
        
        const daysList = prefs.days.map(day => dayNames[day]).join(', ');
        
        let timesList = '';
        if (prefs.times && prefs.times.length > 0) {
          timesList = prefs.times.map(time => {
            if (typeof time === 'object' && time.start && time.end) {
              return `${formatTime(time.start)} - ${formatTime(time.end)}`;
            } else {
              return time;
            }
          }).join(', ');
        }
        
        availabilityHTML = `
          <p class="text-gray-600 text-sm">
            <span class="font-medium">Days:</span> ${daysList}<br>
            ${timesList ? `<span class="font-medium">Times:</span> ${timesList}` : ''}
          </p>
        `;
      }
    }
    
    // Create HTML for student card
    studentCard.innerHTML = `
      <div class="flex items-start">
        <div class="flex-1">
          <h3 class="font-semibold">${student.first_name} ${student.last_name}</h3>
          <p class="text-gray-500 text-sm">${student.email}</p>
          <p class="text-gray-500 text-sm">${student.phone || 'No phone'}</p>
          
          <div class="mt-3 grid grid-cols-3 gap-2">
            <div>
              <span class="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full">
                DUPR ${duprRating}
              </span>
            </div>
            <div>
              <span class="inline-block bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded-full">
                ${student.completed_sessions || 0} sessions
              </span>
            </div>
            <div>
              <span class="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-0.5 rounded-full">
                ${student.active_packages || 0} packages
              </span>
            </div>
          </div>
          
          <div class="mt-3">
            <h4 class="text-xs font-medium text-gray-700">Availability Preferences</h4>
            ${availabilityHTML}
          </div>
        </div>
      </div>
    `;
    
    // Add click handler
    studentCard.addEventListener('click', () => {
      openStudentDetailModal(student);
    });
    
    container.appendChild(studentCard);
  });
}

// Set up event listeners for students tab
function setupStudentsEventListeners() {
  // Search input
  const searchInput = document.getElementById('students-search');
  if (searchInput) {
    searchInput.addEventListener('input', filterStudents);
  }
  
  // Sort select
  const sortSelect = document.getElementById('students-sort');
  if (sortSelect) {
    sortSelect.addEventListener('change', filterStudents);
  }
  
  // Reset filters button
  const resetButton = document.getElementById('reset-students-filters');
  if (resetButton) {
    resetButton.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (sortSelect) sortSelect.value = 'name-asc';
      displayStudents(originalStudentsData);
    });
  }
  
  // Modal close buttons
  document.querySelectorAll('.close-student-detail-modal').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = document.getElementById('student-detail-modal');
      if (modal) modal.classList.add('hidden');
    });
  });
  
  // Tab buttons in student detail modal
  const packageTabBtn = document.getElementById('packages-tab-btn');
  const bookingsTabBtn = document.getElementById('bookings-tab-btn');
  const logsTabBtn = document.getElementById('logs-tab-btn');
  const newBookingTabBtn = document.getElementById('new-booking-tab-btn');
  
  if (packageTabBtn && bookingsTabBtn && logsTabBtn && newBookingTabBtn) {
    // Packages tab
    packageTabBtn.addEventListener('click', () => {
      setActiveTab('packages');
    });
    
    // Bookings tab
    bookingsTabBtn.addEventListener('click', () => {
      setActiveTab('bookings');
    });
    
    // Logs tab
    logsTabBtn.addEventListener('click', () => {
      setActiveTab('logs');
    });
    
    // New Booking tab
    newBookingTabBtn.addEventListener('click', () => {
      setActiveTab('new-booking');
    });
  }
  
  // New booking form submission
  const newBookingForm = document.getElementById('new-booking-form');
  if (newBookingForm) {
    newBookingForm.addEventListener('submit', handleNewBookingSubmit);
  }
}

// Filter students based on search and sort criteria
function filterStudents() {
  const searchInput = document.getElementById('students-search');
  const sortSelect = document.getElementById('students-sort');
  
  if (!searchInput || !sortSelect) return;
  
  const searchTerm = searchInput.value.toLowerCase();
  const sortValue = sortSelect.value;
  
  // Clone the original data
  let filteredStudents = [...originalStudentsData];
  
  // Apply search filter
  if (searchTerm) {
    filteredStudents = filteredStudents.filter(student => {
      const fullName = `${student.first_name} ${student.last_name}`.toLowerCase();
      const email = student.email.toLowerCase();
      return fullName.includes(searchTerm) || email.includes(searchTerm);
    });
  }
  
  // Apply sorting
  switch (sortValue) {
    case 'name-asc':
      filteredStudents.sort((a, b) => {
        const nameA = `${a.first_name} ${a.last_name}`.toLowerCase();
        const nameB = `${b.first_name} ${b.last_name}`.toLowerCase();
        return nameA.localeCompare(nameB);
      });
      break;
    case 'name-desc':
      filteredStudents.sort((a, b) => {
        const nameA = `${a.first_name} ${a.last_name}`.toLowerCase();
        const nameB = `${b.first_name} ${b.last_name}`.toLowerCase();
        return nameB.localeCompare(nameA);
      });
      break;
    case 'dupr-desc':
      filteredStudents.sort((a, b) => (b.dupr_rating || 0) - (a.dupr_rating || 0));
      break;
    case 'dupr-asc':
      filteredStudents.sort((a, b) => (a.dupr_rating || 0) - (b.dupr_rating || 0));
      break;
    case 'sessions-desc':
      filteredStudents.sort((a, b) => (b.completed_sessions || 0) - (a.completed_sessions || 0));
      break;
    case 'sessions-asc':
      filteredStudents.sort((a, b) => (a.completed_sessions || 0) - (b.completed_sessions || 0));
      break;
    case 'upcoming-asc':
      filteredStudents.sort((a, b) => {
        // For this we'd ideally sort by the date of the next upcoming booking
        // If there's no upcoming booking, put at the end
        const dateA = a.next_booking_date ? new Date(a.next_booking_date) : new Date('9999-12-31');
        const dateB = b.next_booking_date ? new Date(b.next_booking_date) : new Date('9999-12-31');
        return dateA - dateB;
      });
      break;
  }
  
  // Display the filtered students
  displayStudents(filteredStudents);
}

// Open student detail modal
async function openStudentDetailModal(student) {
  currentStudentId = student.id;
  const modal = document.getElementById('student-detail-modal');
  
  if (!modal) return;
  
  try {
    // Update student details
    document.getElementById('student-detail-name').textContent = `Student: ${student.first_name} ${student.last_name}`;
    document.getElementById('student-detail-full-name').textContent = `${student.first_name} ${student.last_name}`;
    document.getElementById('student-detail-email').textContent = student.email || 'No email provided';
    document.getElementById('student-detail-phone').textContent = student.phone || 'No phone provided';
    document.getElementById('student-detail-dupr').textContent = student.dupr_rating ? student.dupr_rating.toFixed(1) : 'Not specified';
    document.getElementById('student-detail-sessions').textContent = student.completed_sessions || 0;
    
    // Set student ID in new booking form
    document.getElementById('new-booking-student-id').value = student.id;
    
    // Update profile image or initial
    const imageContainer = document.getElementById('student-detail-image');
    if (student.profile_picture) {
      imageContainer.innerHTML = `<img src="${student.profile_picture}" alt="${student.first_name}" class="h-24 w-24 rounded-full object-cover">`;
    } else {
      imageContainer.innerHTML = student.first_name[0];
    }
    
    // Update availability preferences
    const availabilityContainer = document.getElementById('student-detail-availability');
    
    if (student.availability_preferences) {
      const prefs = student.availability_preferences;
      
      if (prefs.days && prefs.days.length > 0) {
        const dayNames = {
          0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday'
        };
        
        const daysList = prefs.days.map(day => dayNames[day]).join(', ');
        
        let timesList = '';
        if (prefs.times && prefs.times.length > 0) {
          timesList = prefs.times.map(time => {
            if (typeof time === 'object' && time.start && time.end) {
              return `${formatTime(time.start)} - ${formatTime(time.end)}`;
            } else {
              return time;
            }
          }).join(', ');
        }
        
        let notesHtml = '';
        if (prefs.notes) {
          notesHtml = `<p class="mt-1"><span class="font-medium">Notes:</span> ${prefs.notes}</p>`;
        }
        
        availabilityContainer.innerHTML = `
          <p><span class="font-medium">Preferred Days:</span> ${daysList}</p>
          ${timesList ? `<p class="mt-1"><span class="font-medium">Preferred Times:</span> ${timesList}</p>` : ''}
          ${notesHtml}
        `;
      } else {
        availabilityContainer.innerHTML = 'No specific availability preferences set';
      }
    } else {
      availabilityContainer.innerHTML = 'No availability preferences set';
    }
    
    // Reset to packages tab by default
    setActiveTab('packages');
    
    // Load student's packages, bookings, and session logs
    await Promise.all([
      loadStudentPackages(student.id),
      loadStudentBookings(student.id),
      loadStudentSessionLogs(student.id)
    ]);
    
    // Populate courts and packages dropdowns for new booking
    await populateNewBookingForm(student.id);
    
    // Show modal
    modal.classList.remove('hidden');
  } catch (error) {
    console.error('Error opening student detail modal:', error);
    showToast('Error', 'Failed to load student details', 'error');
  }
}

// Set active tab in student detail modal
function setActiveTab(tabName) {
  // Update tab buttons
  document.getElementById('packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
  document.getElementById('packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
  
  document.getElementById('bookings-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
  document.getElementById('bookings-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
  
  document.getElementById('logs-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
  document.getElementById('logs-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
  
  document.getElementById('new-booking-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
  document.getElementById('new-booking-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
  
  // Update tab content
  document.getElementById('packages-tab-content').classList.add('hidden');
  document.getElementById('packages-tab-content').classList.remove('active');
  
  document.getElementById('bookings-tab-content').classList.add('hidden');
  document.getElementById('bookings-tab-content').classList.remove('active');
  
  document.getElementById('logs-tab-content').classList.add('hidden');
  document.getElementById('logs-tab-content').classList.remove('active');
  
  document.getElementById('new-booking-tab-content').classList.add('hidden');
  document.getElementById('new-booking-tab-content').classList.remove('active');
  
  // Set active tab
  document.getElementById(`${tabName}-tab-btn`).classList.add('text-blue-600', 'border-blue-600');
  document.getElementById(`${tabName}-tab-btn`).classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
  
  document.getElementById(`${tabName}-tab-content`).classList.remove('hidden');
  document.getElementById(`${tabName}-tab-content`).classList.add('active');
}

// Load student packages
async function loadStudentPackages(studentId) {
  try {
    const packages = await fetchAPI(`/student/packages_for_coach?student_id=${currentStudentId}`);
    currentStudentPackages = packages;
    
    const container = document.getElementById('student-packages-container');
    
    if (!packages || packages.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No packages found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    packages.forEach(pkg => {
      const packageEl = document.createElement('div');
      packageEl.className = 'bg-white border border-gray-200 rounded-lg p-4';
      
      // Format status with appropriate color
      let statusClass = '';
      switch (pkg.status) {
        case 'pending':
          statusClass = 'bg-yellow-100 text-yellow-800';
          break;
        case 'active':
          statusClass = 'bg-green-100 text-green-800';
          break;
        case 'completed':
          statusClass = 'bg-blue-100 text-blue-800';
          break;
        case 'expired':
          statusClass = 'bg-red-100 text-red-800';
          break;
        case 'rejected':
          statusClass = 'bg-red-100 text-red-800';
          break;
      }
      
      // Create HTML for package
      packageEl.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${pkg.pricing_plan ? pkg.pricing_plan.name : 'Standard Package'}</h3>
            <p class="text-gray-500 text-sm">
              Purchased on ${formatDate(pkg.purchase_date)}
            </p>
          </div>
          <div class="text-right">
            <span class="px-2 py-1 rounded-full text-xs ${statusClass} capitalize">${pkg.status}</span>
            <p class="text-gray-600 text-sm mt-1">
              ${pkg.sessions_booked || 0}/${pkg.total_sessions} sessions used
            </p>
          </div>
        </div>
        
        <div class="mt-3 grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Total Sessions:</span> ${pkg.total_sessions}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Price:</span> $${formatCurrency(pkg.total_price)}
            </p>
          </div>
        </div>
        
        <div class="mt-3 grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Available Sessions:</span> ${pkg.total_sessions - (pkg.sessions_booked || 0)}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Expires:</span> ${pkg.expires_at ? formatDate(pkg.expires_at) : 'Never'}
            </p>
          </div>
        </div>
        
        ${pkg.status === 'active' ? `
          <div class="mt-4">
            <button type="button" class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 use-package-btn" data-package-id="${pkg.id}">
              Use Package
            </button>
          </div>
        ` : ''}
      `;
      
      // Add event listener to "Use Package" button
      const usePackageBtn = packageEl.querySelector('.use-package-btn');
      if (usePackageBtn) {
        usePackageBtn.addEventListener('click', () => {
          setActiveTab('new-booking');
          document.getElementById('new-booking-package').value = pkg.id;
        });
      }
      
      container.appendChild(packageEl);
    });
  } catch (error) {
    console.error('Error loading student packages:', error);
    showToast('Error', 'Failed to load student packages', 'error');
  }
}

// Load student bookings
async function loadStudentBookings(studentId) {
  try {
    // Fetch both upcoming and completed bookings
    const upcomingBookings = await fetchAPI(`/student/bookings/upcoming?student_id=${studentId}`);
    const completedBookings = await fetchAPI(`/student/bookings/completed?student_id=${studentId}`);
    
    // Combine and sort bookings (newest first)
    const bookings = [...upcomingBookings, ...completedBookings];
    bookings.sort((a, b) => {
      const dateA = new Date(a.date);
      const dateB = new Date(b.date);
      return dateB - dateA;
    });
    
    currentStudentBookings = bookings;
    
    const container = document.getElementById('student-bookings-container');
    
    if (!bookings || bookings.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No bookings found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    bookings.forEach(booking => {
      const bookingEl = document.createElement('div');
      bookingEl.className = 'bg-white border border-gray-200 rounded-lg p-4';
      
      const bookingDate = formatDate(booking.date);
      const startTime = formatTime(booking.start_time);
      const endTime = formatTime(booking.end_time);
      
      // Determine status and appropriate styling
      let statusClass = '';
      let statusText = booking.status;
      
      switch (booking.status) {
        case 'upcoming':
          statusClass = 'bg-blue-100 text-blue-800';
          statusText = 'Upcoming';
          break;
        case 'completed':
          statusClass = 'bg-green-100 text-green-800';
          statusText = 'Completed';
          break;
        case 'cancelled':
          statusClass = 'bg-red-100 text-red-800';
          statusText = 'Cancelled';
          break;
      }
      
      // Create HTML for booking
      bookingEl.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${bookingDate}</h3>
            <p class="text-gray-500 text-sm">${startTime} - ${endTime}</p>
          </div>
          <div class="text-right">
            <span class="px-2 py-1 rounded-full text-xs ${statusClass}">${statusText}</span>
            <p class="text-gray-600 text-sm mt-1">$${formatCurrency(booking.price)}</p>
          </div>
        </div>
        
        <div class="mt-3">
          <p class="text-sm text-gray-600">
            <i class="fas fa-map-marker-alt mr-1"></i> ${booking.court.name}
          </p>
        </div>
        
        ${booking.status === 'upcoming' ? `
          <div class="mt-3 flex justify-end space-x-2">
            ${!booking.venue_confirmed ? `
              <button type="button" class="bg-yellow-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-yellow-700 confirm-venue-btn" data-booking-id="${booking.id}">
                <i class="fas fa-check-circle mr-1"></i> Confirm Venue
              </button>
            ` : ''}
            <button type="button" class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 reschedule-btn" data-booking-id="${booking.id}">
              <i class="fas fa-clock mr-1"></i> Reschedule
            </button>
            <button type="button" class="bg-red-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-red-700 cancel-btn" data-booking-id="${booking.id}">
              <i class="fas fa-times-circle mr-1"></i> Cancel
            </button>
          </div>
        ` : ''}
        
        ${booking.status === 'completed' && booking.session_log ? `
          <div class="mt-3 flex justify-end">
            <button type="button" class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 view-log-btn" data-log-id="${booking.session_log.id}">
              <i class="fas fa-clipboard-list mr-1"></i> View Log
            </button>
          </div>
        ` : ''}
      `;
      
      // Add event listeners to action buttons
      const confirmVenueBtn = bookingEl.querySelector('.confirm-venue-btn');
      if (confirmVenueBtn) {
        confirmVenueBtn.addEventListener('click', () => {
          showConfirmVenueModal(confirmVenueBtn.dataset.bookingId);
        });
      }
      
      const rescheduleBtn = bookingEl.querySelector('.reschedule-btn');
      if (rescheduleBtn) {
        rescheduleBtn.addEventListener('click', () => {
          showRescheduleBookingModal(rescheduleBtn.dataset.bookingId);
        });
      }
      
      const cancelBtn = bookingEl.querySelector('.cancel-btn');
      if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
          showCancelBookingModal(cancelBtn.dataset.bookingId);
        });
      }
      
      const viewLogBtn = bookingEl.querySelector('.view-log-btn');
      if (viewLogBtn) {
        viewLogBtn.addEventListener('click', () => {
          openSessionLogModal(null, viewLogBtn.dataset.logId);
        });
      }
      
      container.appendChild(bookingEl);
    });
  } catch (error) {
    console.error('Error loading student bookings:', error);
    showToast('Error', 'Failed to load student bookings', 'error');
  }
}

// Load student session logs
async function loadStudentSessionLogs(studentId) {
  try {
    const sessionLogs = await fetchAPI(`/student/session-logs?student_id=${studentId}`);
    currentStudentLogs = sessionLogs;
    
    const container = document.getElementById('student-logs-container');
    
    if (!sessionLogs || sessionLogs.length === 0) {
      container.innerHTML = `
        <div class="text-center py-6 text-gray-500">
          <p>No session logs found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    sessionLogs.forEach(log => {
      const logEl = document.createElement('div');
      logEl.className = 'bg-white border border-gray-200 rounded-lg p-4';
      
      const logDate = log.booking ? formatDate(log.booking.date) : 'Unknown date';
      
      // Create HTML for session log
      logEl.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${log.title}</h3>
            <p class="text-gray-500 text-sm">${logDate}</p>
          </div>
          <div class="text-right">
            <span class="text-gray-600">${formatDate(log.created_at)}</span>
          </div>
        </div>
        
        ${log.booking ? `
          <div class="mt-2">
            <span class="inline-block bg-gray-100 text-gray-700 rounded-lg px-2 py-1 text-xs">
              <i class="fas fa-map-marker-alt mr-1"></i> ${log.booking.court.name}
            </span>
          </div>
        ` : ''}
        
        <div class="mt-3">
          <h4 class="text-sm font-medium text-gray-700">Public Notes</h4>
          <p class="text-gray-600 mt-1">${log.notes || 'No notes added'}</p>
        </div>

        <div class="mt-3">
          <h4 class="text-sm font-medium text-gray-700">Private Coach Notes</h4>
          <p class="text-gray-600 mt-1">${log.coach_notes || 'No notes added'}</p>
        </div>
        
        <div class="mt-3 flex justify-end">
          <button type="button" class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 edit-log-btn" data-log-id="${log.id}" data-booking-id="${log.booking ? log.booking.id : ''}">
            Edit Log
          </button>
        </div>
      `;
      
      // Add event listener to edit button
      const editLogBtn = logEl.querySelector('.edit-log-btn');
      if (editLogBtn) {
        editLogBtn.addEventListener('click', () => {
          const bookingId = editLogBtn.dataset.bookingId;
          const logId = editLogBtn.dataset.logId;
          openSessionLogModal(bookingId, logId);
        });
      }
      
      container.appendChild(logEl);
    });
  } catch (error) {
    console.error('Error loading student session logs:', error);
    showToast('Error', 'Failed to load student session logs', 'error');
  }
}

// Populate the new booking form with courts and packages
async function populateNewBookingForm(studentId) {
  try {
    // Set min date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('new-booking-date').min = today;
    document.getElementById('new-booking-date').value = today;
    
    // Clear other fields
    document.getElementById('new-booking-start-time').value = '';
    document.getElementById('new-booking-end-time').value = '';
    
    // Populate packages dropdown
    const packageSelect = document.getElementById('new-booking-package');
    packageSelect.innerHTML = '<option value="">Select a package</option>';
    
    currentStudentPackages.forEach(pkg => {
      if (pkg.status === 'active' && pkg.total_sessions > pkg.sessions_booked) {
        const option = document.createElement('option');
        option.value = pkg.id;
        option.textContent = `${pkg.pricing_plan ? pkg.pricing_plan.name : 'Standard Package'} (${pkg.total_sessions - pkg.sessions_booked} sessions left)`;
        packageSelect.appendChild(option);
      }
    });
    
    // Populate courts dropdown
    const courts = await getCourts();
    const courtSelect = document.getElementById('new-booking-court');
    courtSelect.innerHTML = '<option value="">Select a court</option>';
    
    courts.forEach(court => {
      const option = document.createElement('option');
      option.value = court.id;
      option.textContent = court.name;
      courtSelect.appendChild(option);
    });
    
    //document.getElementById('new-booking-responsibility').value = 'student';

  } catch (error) {
    console.error('Error populating new booking form:', error);
    showToast('Error', 'Failed to load form data', 'error');
  }
}

// Handle new booking form submission
async function handleNewBookingSubmit(e) {
  e.preventDefault();
  
  const form = document.getElementById('new-booking-form');
  const formData = new FormData(form);
  
  const bookingData = {
    student_id: formData.get('student_id'),
    package_id: formData.get('package_id'),
    court_id: formData.get('court_id'),
    date: formData.get('date'),
    start_time: formData.get('start_time'),
    end_time: formData.get('end_time')
  };
  
  try {
    showLoading(form);
    
    // Create the booking
    const response = await fetchAPI('/coach/create-booking-for-student', {
      method: 'POST',
      body: JSON.stringify(bookingData)
    });
    
    hideLoading(form);
    
    // Close the modal
    document.getElementById('student-detail-modal').classList.add('hidden');
    
    showToast('Success', 'Booking created successfully', 'success');
    
    // Reload students to update data
    await loadStudents();
  } catch (error) {
    hideLoading(form);
    showToast('Error', 'Failed to create booking: ' + error.message, 'error');
  }
}

// Initialize students tab when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Check if we're on the students tab
  const studentsTab = document.getElementById('students-tab');
  if (studentsTab && studentsTab.classList.contains('active')) {
    initStudentsTab();
  }
  
  // Add event listener to tab link to initialize when clicked
  const studentsTabLink = document.querySelector('.students-tab');
  if (studentsTabLink) {
    studentsTabLink.addEventListener('click', function() {
      initStudentsTab();
    });
  }
});