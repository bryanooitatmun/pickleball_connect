/**
 * Bookings tab-specific JavaScript
 */

// Store original data for filtering
let originalBookingsData = {
    upcoming: [],
    completed: [],
    cancelled: []
  };
  
  // Track current active bookings tab
  let currentBookingsTab = 'upcoming';
  
  // Function called when the bookings tab is activated
  function initBookingsTab() {
    // Load bookings data if not already loaded
    const upcomingContainer = document.getElementById('upcoming-bookings-container');
    if (upcomingContainer && !upcomingContainer.dataset.loaded) {
      loadBookings();
      setupBookingEventListeners();
      upcomingContainer.dataset.loaded = 'true';
    }
  }
  
  // Load bookings data
  async function loadBookings() {
    try {
      // For academy managers, check if a coach filter is applied
      let coachId = '';
      if (IS_ACADEMY_MANAGER) {
        const coachFilter = document.getElementById('coach-filter');
        if (coachFilter && coachFilter.value) {
          coachId = coachFilter.value;
        }
      }
      
      // Load upcoming bookings
      const upcomingEndpoint = coachId ? `/coach/bookings/upcoming?coach_id=${coachId}` : '/coach/bookings/upcoming';
      const upcomingBookings = await fetchAPI(upcomingEndpoint);
      originalBookingsData.upcoming = upcomingBookings;
      
      // Sort by date (newest first by default)
      upcomingBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        
        if (document.getElementById(`upcoming-sort`).value === 'date-asc') {
          return dateA - dateB;
        } else {
          return dateB - dateA;
        }
      });
      
      displayBookings(upcomingBookings, 'upcoming');
      
      // Load completed bookings
      const completedEndpoint = coachId ? `/coach/bookings/completed?coach_id=${coachId}` : '/coach/bookings/completed';
      const completedBookings = await fetchAPI(completedEndpoint);
      originalBookingsData.completed = completedBookings;
      
      // Sort by date (newest first by default)
      completedBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB - dateA;
      });
      
      displayBookings(completedBookings, 'completed');
      
      // Load cancelled bookings
      const cancelledEndpoint = coachId ? `/coach/bookings/cancelled?coach_id=${coachId}` : '/coach/bookings/cancelled';
      const cancelledBookings = await fetchAPI(cancelledEndpoint);
      originalBookingsData.cancelled = cancelledBookings;
      
      // Sort by date (newest first by default)
      cancelledBookings.sort((a, b) => {
        const dateA = new Date(a.date);
        const dateB = new Date(b.date);
        return dateB - dateA;
      });
      
      displayBookings(cancelledBookings, 'cancelled');
      
      // If academy manager
      if (IS_ACADEMY_MANAGER) {
        loadAcademyCoaches();
      }
      
      // Update dashboard data
      updateDashboardStats();
      
    } catch (error) {
      console.error('Error loading bookings:', error);
      showToast('Error', 'Failed to load bookings data', 'error');
    }
  }
  
  // Display bookings in the respective containers
  function displayBookings(bookings, status) {
    const container = document.getElementById(`${status}-bookings-container`);
    
    if (!container) return;
    
    if (bookings.length === 0) {
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
      let paymentProofHtml = '';
      let courtProofHtml = '';
      
      // View proofs button
      const viewProofsButton = `
        <button class="text-blue-600 hover:text-blue-800 view-proofs-btn" data-booking-id="${booking.id}">
          <i class="fas fa-receipt mr-1"></i> View Proofs
        </button>
      `;
      
      if (status === 'upcoming') {
        // Show court booking responsibility and status
        if (booking.court_booking_responsibility === 'coach') {
          if (IS_COACH) {
            venueStatusHtml = booking.venue_confirmed ? 
              `<div class="mt-3 px-3 py-1.5 rounded-md bg-green-100 border border-green-300 text-green-700 text-sm"><i class="fas fa-check-circle mr-1"></i> Venue Confirmed</div>` : 
              `<button class="mt-3 px-3 py-1.5 rounded-md ${booking.court_booking_proof ? 'bg-yellow-100 border border-yellow-300 text-yellow-700 hover:bg-yellow-200' : 'bg-red-100 border border-red-300 text-red-700 hover:bg-red-200'}  focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 text-sm font-medium flex items-center space-x-1.5 transition-colors confirm-venue-btn" data-booking-id="${booking.id}" data-has-proof="${booking.court_booking_proof ? 'true' : 'false'}">
                <i class="fas fa-exclamation-circle mr-1"></i>
                <span>${booking.court_booking_proof ? 'Confirm Venue Booking' : 'Please Book The Venue and Upload Court Booking Proof'}</span>
              </button>`;
          } else {
            venueStatusHtml = booking.venue_confirmed ? 
              `<div class="mt-3 px-3 py-1.5 rounded-md bg-green-100 border border-green-300 text-green-700 text-sm"><i class="fas fa-check-circle mr-1"></i> Venue Confirmed</div>` : 
              `<div class="mt-3 px-3 py-1.5 rounded-md bg-yellow-100 border border-yellow-300 text-yellow-700 text-sm"><i class="fas fa-exclamation-triangle mr-1"></i> Coach will book the venue</div>`;
          }
        } else {
          venueStatusHtml = booking.venue_confirmed ? 
            `<div class="mt-3 px-3 py-1.5 rounded-md bg-green-100 border border-green-300 text-green-700 text-sm"><i class="fas fa-check-circle mr-1"></i> Venue Confirmed</div>` : 
            `<button class="mt-3 px-3 py-1.5 rounded-md ${booking.court_booking_proof ? 'bg-yellow-100 border border-yellow-300 text-yellow-700 hover:bg-yellow-200' : 'bg-red-100 border border-red-300 text-red-700 hover:bg-red-200'} focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50 text-sm font-medium flex items-center space-x-1.5 transition-colors confirm-venue-btn" data-booking-id="${booking.id}" data-has-proof="${booking.court_booking_proof ? 'true' : 'false'}">
                <i class="fas fa-exclamation-circle mr-1"></i>
                <span>${booking.court_booking_proof ? 'Student Has Booked the Venue. Please Confirm Venue Booking' : 'ERROR: Student is responsible for court booking but image proof not available'}</span>
              </button>`;
        }
        
        // Show payment and court proof status
        if (booking.payment_proof) {
          paymentProofHtml = `
            <div class="text-green-600 text-sm"><i class="fas fa-check-circle mr-1"></i> Payment proof uploaded</div>
          `;
        }
        
        if (booking.court_booking_proof) {
          courtProofHtml = `
            <div class="text-green-600 text-sm"><i class="fas fa-check-circle mr-1"></i> Court booking proof uploaded</div>
          `;
        }
      }
  
      let actionsHtml = '';
      
      if (status === 'upcoming') {
        if (IS_COACH) {
          actionsHtml = `
            <div class="flex flex-wrap gap-2 mt-4">
              <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 complete-booking-btn" data-booking-id="${booking.id}">
                <i class="fas fa-check-circle mr-1"></i> Complete
              </button>
              <button class="bg-yellow-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-yellow-700 reschedule-booking-btn" data-booking-id="${booking.id}">
                <i class="fas fa-clock mr-1"></i> Reschedule
              </button>
              <button class="bg-red-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-red-700 cancel-booking-btn" data-booking-id="${booking.id}">
                <i class="fas fa-times-circle mr-1"></i> Cancel
              </button>
              ${viewProofsButton}
            </div>
          `;
        } else {
          actionsHtml = `
            <div class="flex flex-wrap gap-2 mt-4">
              <button class="text-red-600 hover:text-red-800 request-cancel-btn" data-booking-id="${booking.id}">
                <i class="fas fa-times-circle mr-1"></i> Request Cancellation
              </button>
              ${viewProofsButton}
            </div>
          `;
        }
      } else if (status === 'completed') {
        const hasSessionLog = booking.session_log !== null;
        
        if (IS_COACH) {
          actionsHtml = `
            <div class="flex flex-wrap gap-2 mt-4">
              <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 edit-log-btn" data-booking-id="${booking.id}" data-log-id="${hasSessionLog ? booking.session_log.id : ''}">
                <i class="fas fa-clipboard-list mr-1"></i> ${hasSessionLog ? 'Edit Log' : 'Add Log'}
              </button>
              ${viewProofsButton}
            </div>
          `;
        } else {
          actionsHtml = `
            <div class="flex flex-wrap gap-2 mt-4">
              ${hasSessionLog ? `
                <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 view-log-btn" data-booking-id="${booking.id}" data-log-id="${booking.session_log.id}">
                  <i class="fas fa-clipboard-list mr-1"></i> View Session Log
                </button>
              ` : ''}
              ${viewProofsButton}
            </div>
          `;
        }
      } else if (status === 'cancelled') {
        actionsHtml = `
          <div class="flex flex-wrap gap-2 mt-4">
            ${viewProofsButton}
          </div>
        `;
      }
      
      // Create HTML structure based on whether user is coach or student
      if (IS_COACH) {
        bookingCard.innerHTML = `
          <div class="flex flex-col md:flex-row md:justify-between">
            <div>
              <h3 class="font-semibold">${booking.student.first_name} ${booking.student.last_name}</h3>
              <p class="text-gray-500 text-sm">Student</p>
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
              <div class="mt-3">
                <span class="inline-block bg-blue-100 text-blue-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
                  $${formatCurrency(booking.price)}
                </span>
                ${booking.pricing_plan ? `
                  <span class="inline-block bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
                    ${booking.pricing_plan.name}
                  </span>
                ` : ''}
              </div>
              ${paymentProofHtml}
              ${courtProofHtml}
            </div>
            <div class="mt-4 md:mt-0 md:text-right md:flex md:flex-col md:justify-between">
              ${venueStatusHtml}
              ${actionsHtml}
            </div>
          </div>
        `;
      } else {
        bookingCard.innerHTML = `
          <div class="flex flex-col md:flex-row md:justify-between">
            <div>
              <h3 class="font-semibold">${booking.coach.user.first_name} ${booking.coach.user.last_name}</h3>
              <p class="text-gray-500 text-sm">Coach</p>
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
              <div class="mt-3">
                <span class="inline-block bg-blue-100 text-blue-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
                  $${formatCurrency(booking.price)}
                </span>
                ${booking.pricing_plan ? `
                  <span class="inline-block bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
                    ${booking.pricing_plan.name}
                  </span>
                ` : ''}
              </div>
              ${paymentProofHtml}
              ${courtProofHtml}
            </div>
            <div class="mt-4 md:mt-0 md:text-right md:flex md:flex-col md:justify-between">
              ${venueStatusHtml}
              ${actionsHtml}
            </div>
          </div>
        `;
      }
      
      container.appendChild(bookingCard);
    });
    
    // Add event listeners to buttons
    addBookingButtonEventListeners(status);
  }
  
  // Add event listeners to booking action buttons
  function addBookingButtonEventListeners(status) {
    // Complete booking buttons
    document.querySelectorAll('.complete-booking-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        showCompleteBookingModal(bookingId);
      });
    });
    
    // Confirm venue buttons
    document.querySelectorAll('.confirm-venue-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        
        showConfirmVenueModal(bookingId);
      });
    });
    
    // Reschedule booking buttons
    document.querySelectorAll('.reschedule-booking-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        showRescheduleBookingModal(bookingId);
      });
    });
    
    // Cancel booking buttons
    document.querySelectorAll('.cancel-booking-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        showCancelBookingModal(bookingId);
      });
    });
    
    // Edit/add session log buttons
    document.querySelectorAll('.edit-log-btn, .view-log-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        const logId = this.getAttribute('data-log-id');
        openSessionLogModal(bookingId, logId);
      });
    });
    
    // View proofs buttons
    document.querySelectorAll('.view-proofs-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        showBookingProofs(bookingId);
      });
    });
    
    // Request cancellation buttons
    document.querySelectorAll('.request-cancel-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const bookingId = this.getAttribute('data-booking-id');
        showRequestCancellationModal(bookingId);
      });
    });
  }
  
  // Show booking proof viewer
  async function showBookingProofs(bookingId) {
    try {
      const booking = await fetchAPI(`/coach/bookings/${bookingId}`);
      
      const proofViewer = document.getElementById('proof-viewer');
      const bookingDetails = document.getElementById('booking-details');
      const paymentProofContainer = document.getElementById('payment-proof-container');
      const courtProofContainer = document.getElementById('court-proof-container');
      const uploadCourtProofSection = document.getElementById('upload-court-proof-section');
      
      if (!proofViewer || !bookingDetails || !paymentProofContainer || !courtProofContainer) {
        return;
      }
      
      // Display booking details
      const bookingDate = formatDate(booking.date);
      const startTime = formatTime(booking.start_time);
      const endTime = formatTime(booking.end_time);
      
      bookingDetails.innerHTML = `
        <h4 class="font-medium mb-2">Booking Details</h4>
        <div class="bg-gray-50 p-3 rounded-lg">
          <div class="flex items-center mb-2">
            <i class="fas fa-calendar-day mr-2 text-gray-600"></i>
            <span>${bookingDate}</span>
          </div>
          <div class="flex items-center mb-2">
            <i class="fas fa-clock mr-2 text-gray-600"></i>
            <span>${startTime} - ${endTime}</span>
          </div>
          <div class="flex items-center mb-2">
            <i class="fas fa-map-marker-alt mr-2 text-gray-600"></i>
            <span>${booking.court.name}</span>
          </div>
          <div class="flex items-center mb-2">
            <i class="fas fa-dollar-sign mr-2 text-gray-600"></i>
            <span>$${formatCurrency(booking.price)}</span>
          </div>
          <div class="flex items-center">
            <i class="fas fa-user mr-2 text-gray-600"></i>
            <span>${IS_COACH ? `${booking.student.first_name} ${booking.student.last_name}` : `${booking.coach.user.first_name} ${booking.coach.user.last_name}`}</span>
          </div>
        </div>
      `;
      
      // Display payment proof
      if (booking.payment_proof) {
        const fileExtension = booking.payment_proof.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) {
          paymentProofContainer.innerHTML = `
            <img src="/static/${booking.payment_proof}" alt="Payment Proof" class="max-w-full h-auto rounded">
          `;
        } else if (fileExtension === 'pdf') {
          paymentProofContainer.innerHTML = `
            <div class="flex flex-col items-center">
              <i class="fas fa-file-pdf text-red-500 text-4xl mb-2"></i>
              <a href="/static/${booking.payment_proof}" target="_blank" class="text-blue-600 hover:text-blue-800">
                View PDF Payment Proof
              </a>
            </div>
          `;
        } else {
          paymentProofContainer.innerHTML = `
            <div class="flex flex-col items-center">
              <i class="fas fa-file text-gray-500 text-4xl mb-2"></i>
              <a href="/static/${booking.payment_proof}" target="_blank" class="text-blue-600 hover:text-blue-800">
                Download Payment Proof
              </a>
            </div>
          `;
        }
      } else {
        paymentProofContainer.innerHTML = `
          <p class="text-gray-500">No payment proof available</p>
        `;
      }
      
      // Display court booking proof
      if (booking.court_booking_proof) {
        const fileExtension = booking.court_booking_proof.split('.').pop().toLowerCase();
        if (['jpg', 'jpeg', 'png', 'gif'].includes(fileExtension)) {
          courtProofContainer.innerHTML = `
            <img src="/static/${booking.court_booking_proof}" alt="Court Booking Proof" class="max-w-full h-auto rounded">
          `;
        } else if (fileExtension === 'pdf') {
          courtProofContainer.innerHTML = `
            <div class="flex flex-col items-center">
              <i class="fas fa-file-pdf text-red-500 text-4xl mb-2"></i>
              <a href="/static/${booking.court_booking_proof}" target="_blank" class="text-blue-600 hover:text-blue-800">
                View PDF Court Booking Proof
              </a>
            </div>
          `;
        } else {
          courtProofContainer.innerHTML = `
            <div class="flex flex-col items-center">
              <i class="fas fa-file text-gray-500 text-4xl mb-2"></i>
              <a href="/static/${booking.court_booking_proof}" target="_blank" class="text-blue-600 hover:text-blue-800">
                Download Court Booking Proof
              </a>
            </div>
          `;
        }
      } else {
        courtProofContainer.innerHTML = `
          <p class="text-gray-500">No court booking proof available</p>
        `;
      }
      
      // Show upload court proof section if coach is responsible and hasn't uploaded proof yet
      if (IS_COACH && booking.court_booking_responsibility === 'coach' && !booking.court_booking_proof && booking.status === 'upcoming') {
        uploadCourtProofSection.classList.remove('hidden');
        document.getElementById('court-proof-booking-id').value = bookingId;
      } else {
        uploadCourtProofSection.classList.add('hidden');
      }
      
      // Show the proof viewer
      proofViewer.classList.remove('hidden');
      
      // Add event listener to close button
      document.getElementById('close-proof-viewer').addEventListener('click', function() {
        proofViewer.classList.add('hidden');
      });
      
      // Add event listener to court proof upload form
      const courtProofForm = document.getElementById('court-proof-form');
      if (courtProofForm) {
        courtProofForm.addEventListener('submit', async function(e) {
          e.preventDefault();
          
          const formData = new FormData(this);
          try {
            showLoading(this);
            await uploadCourtBookingProof(formData.get('booking_id'), formData.get('court_proof'));
            hideLoading(this);
            
            showToast('Success', 'Court booking proof uploaded successfully', 'success');
            
            // Close proof viewer and reload bookings
            proofViewer.classList.add('hidden');
            loadBookings();
          } catch (error) {
            hideLoading(this);
            showToast('Error', 'Failed to upload court booking proof: ' + error.message, 'error');
          }
        });
      }
    } catch (error) {
      console.error('Error loading booking details:', error);
      showToast('Error', 'Failed to load booking details', 'error');
    }
  }
  
  // Show upload court proof modal
  function showUploadCourtProofModal(bookingId) {
    const modal = document.getElementById('upload-court-proof-modal');
    if (!modal) {
      // Create a modal if it doesn't exist
      const modalHTML = `
        <div id="upload-court-proof-modal" class="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50">
          <div class="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-4">
              <h3 class="text-lg font-semibold">Upload Court Booking Proof</h3>
              <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
                <i class="fas fa-times"></i>
              </button>
            </div>
            
            <form id="upload-court-proof-form">
              <input type="hidden" id="upload-proof-booking-id" name="booking_id" value="${bookingId}">
              <div class="mb-4">
                <label for="court-proof-file-upload" class="block text-gray-700 font-medium mb-2">Court Booking Proof*</label>
                <input type="file" id="court-proof-file-upload" name="court_proof" accept="image/*,application/pdf" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required>
                <p class="text-sm text-gray-500 mt-1">Upload screenshot or PDF of court booking confirmation</p>
              </div>
              
              <div class="flex justify-end space-x-3">
                <button type="button" class="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 focus:outline-none close-modal">
                  Cancel
                </button>
                <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none">
                  Upload Proof
                </button>
              </div>
            </form>
          </div>
        </div>
      `;
      
      // Append modal to body
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      const modal = document.getElementById('upload-court-proof-modal');
      
      // Add event listeners to close buttons
      modal.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
          modal.remove();
        });
      });
      
      // Add submit handler
      document.getElementById('upload-court-proof-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        try {
          showLoading(this);
          await uploadCourtBookingProof(formData.get('booking_id'), formData.get('court_proof'));
          hideLoading(this);
          
          showToast('Success', 'Court booking proof uploaded successfully', 'success');
          
          // Remove modal and reload bookings
          modal.remove();
          loadBookings();
        } catch (error) {
          hideLoading(this);
          showToast('Error', 'Failed to upload court booking proof: ' + error.message, 'error');
        }
      });
    } else {
      // Update booking ID in existing modal
      document.getElementById('upload-proof-booking-id').value = bookingId;
      modal.classList.remove('hidden');
    }
  }
  
  // Upload court booking proof to server
  async function uploadCourtBookingProof(bookingId, file) {
    const formData = new FormData();
    formData.append('booking_id', bookingId);
    formData.append('proof_type', 'court');
    formData.append('proof_image', file);
    
    const response = await fetch('/bookings/upload-payment-proof', {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload court booking proof');
    }
    
    return response.json();
  }
  
  // Function to show complete booking modal
  function showCompleteBookingModal(bookingId) {
    const modal = document.getElementById('complete-session-modal');
    if (!modal) return;
    
    // Set booking ID
    document.getElementById('complete-booking-id').value = bookingId;
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Add event listeners to close buttons
    document.querySelectorAll('.close-complete-session-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        modal.classList.add('hidden');
      });
    });
    
    // Add event listener to confirm button if not already added
    const confirmBtn = document.getElementById('confirm-complete-session-btn');
    const existingHandler = confirmBtn.getAttribute('data-handler-added');
    
    if (!existingHandler) {
      confirmBtn.addEventListener('click', async function() {
        const bookingId = document.getElementById('complete-booking-id').value;
        
        try {
          await completeSession(bookingId);
          
          // Hide modal
          modal.classList.add('hidden');
          
          // Show success message
          showToast('Success', 'Session marked as completed', 'success');
          
          // Reload bookings and open session log modal
          await loadBookings();
          await loadCalendarView();

          // Open session log modal after a short delay
          setTimeout(() => {
            openSessionLogModal(bookingId, null);
          }, 500);
          
        } catch (error) {
          console.error('Error completing session:', error);
          showToast('Error', 'Failed to complete session: ' + error.message, 'error');
        }
      });
      
      confirmBtn.setAttribute('data-handler-added', 'true');
    }
  }
  
  // Function to complete a session
  async function completeSession(bookingId) {
    const response = await fetchAPI('/coach/complete-session', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId })
    });
    
    return response;
  }
  
  // Function to show confirm venue modal
  async function showConfirmVenueModal(bookingId) {
    const modal = document.getElementById('confirm-venue-modal');
    if (!modal) return;
    
    try {
      // Show loading state
      modal.classList.add('loading');
      
      // Get booking details from API
      const booking = await fetchAPI(`/coach/bookings/${bookingId}`);
      
      // Set booking ID
      document.getElementById('confirm-venue-booking-id').value = bookingId;
      
      // Determine which section to show based on court booking responsibility
      document.getElementById('coach-booking-responsibility-section').classList.add('hidden');
      document.getElementById('student-booking-responsibility-section').classList.add('hidden');
      
      if (booking.court_booking_responsibility === 'coach') {
        // Coach is responsible for booking - show that section
        const coachSection = document.getElementById('coach-booking-responsibility-section');
        coachSection.classList.remove('hidden');
        
        // Add court booking information
        const instructionsElement = document.getElementById('court-booking-instructions');
        if (instructionsElement) {
          instructionsElement.textContent = booking.court.booking_instructions || 'No specific instructions provided.';
        }
        
        const linkElement = document.getElementById('court-booking-link');
        if (linkElement) {
          if (booking.court.booking_link) {
            linkElement.href = booking.court.booking_link;
            linkElement.textContent = booking.court.booking_link;
            linkElement.parentElement.classList.remove('hidden');
          } else {
            linkElement.parentElement.classList.add('hidden');
          }
        }
        
        // If court proof already exists, show it
        if (booking.court_booking_proof) {
          const proofSection = document.createElement('div');
          proofSection.innerHTML = `
            <div class="mb-4">
              <label class="block text-gray-700 font-medium mb-2">Court Booking Proof</label>
              <div class="p-3 bg-gray-50 rounded-lg flex items-center">
                <a href="${booking.court_booking_proof}" target="_blank" class="text-blue-600 hover:underline flex items-center">
                  <i class="fas fa-file-image mr-2"></i>
                  <span>View Uploaded Proof</span>
                </a>
              </div>
            </div>
          `;
          
          // Insert before the upload field
          const uploadField = coachSection.querySelector('input[type="file"]').parentElement;
          uploadField.insertAdjacentElement('beforebegin', proofSection);
          
          // Hide the upload field since proof already exists
          uploadField.classList.add('hidden');
        }
      } else {
        // Student is responsible for booking - show that section
        const studentSection = document.getElementById('student-booking-responsibility-section');
        studentSection.classList.remove('hidden');
        
        // Show payment and court booking proofs if they exist
        const studentProofLink = document.getElementById('student-court-booking-proof-link');
        const studentProofContainer = document.getElementById('student-court-booking-proof-container');
        
        if (booking.court_booking_proof) {
          studentProofLink.href = booking.court_booking_proof;
          studentProofContainer.classList.remove('hidden');
        } else {
          studentProofContainer.classList.add('hidden');
          studentProofContainer.innerHTML = `
            <p class="text-red-600">Student has not uploaded court booking proof yet.</p>
          `;
        }
        
        const paymentProofLink = document.getElementById('coach-payment-proof-link');
        const paymentProofContainer = document.getElementById('coach-payment-proof-container');
        
        if (booking.payment_proof) {
          paymentProofLink.href = booking.payment_proof;
          paymentProofContainer.classList.remove('hidden');
        } else {
          paymentProofContainer.classList.add('hidden');
          paymentProofContainer.innerHTML = `
            <p class="text-red-600">Student has not uploaded payment proof yet.</p>
          `;
        }
      }
      
      // Remove loading state
      modal.classList.remove('loading');
      
      // Show modal
      modal.classList.remove('hidden');
    } catch (error) {
      console.error('Error showing confirm venue modal:', error);
      showToast('Error', 'Failed to load booking details. Please try again.', 'error');
      modal.classList.remove('loading');
    }
    

    // Add event listeners to close buttons
    document.querySelectorAll('.close-confirm-venue-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        modal.classList.add('hidden');
      });
    });
    
    // Add event listener to confirm button if not already added
    const confirmBtn = document.getElementById('confirm-venue-btn');
    const existingHandler = confirmBtn.getAttribute('data-handler-added');
    
    if (!existingHandler) {
      confirmBtn.addEventListener('click', async function() {
        const bookingId = document.getElementById('confirm-venue-booking-id').value;
        
        try {
          await confirmVenueBooking(bookingId);
          
          // Hide modal
          modal.classList.add('hidden');
          
          // Show success message
          showToast('Success', 'Venue booking confirmed successfully', 'success');
          
          // Reload bookings
          loadBookings();
          await loadCalendarView();
          
        } catch (error) {
          console.error('Error confirming venue booking:', error);
          showToast('Error', 'Failed to confirm venue booking: ' + error.message, 'error');
        }
      });
      
      confirmBtn.setAttribute('data-handler-added', 'true');
    }
  }
  
  // Function to confirm venue booking
  async function confirmVenueBooking(bookingId) {
    const response = await fetchAPI('/coach/confirm-venue', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId })
    });
    
    return response;
  }
  
  // Function to show reschedule booking modal
  function showRescheduleBookingModal(bookingId) {
    const modal = document.getElementById('defer-booking-modal');
    if (!modal) return;
    
    // Set booking ID
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
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Add event listeners to close buttons
    document.querySelectorAll('.close-defer-booking-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        modal.classList.add('hidden');
      });
    });
    
    // Add event listener to form submission if not already added
    const form = document.getElementById('defer-booking-form');
    const existingHandler = form.getAttribute('data-handler-added');
    
    if (!existingHandler) {
      form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(this);
        const deferData = {
          booking_id: formData.get('booking_id'),
          date: formData.get('date'),
          start_time: formData.get('start_time'),
          end_time: formData.get('end_time'),
          court_id: formData.get('court_id'),
          reason: formData.get('reason')
        };
        
        try {
          showLoading(this);
          await deferBooking(deferData);
          hideLoading(this);
          
          // Hide modal
          modal.classList.add('hidden');
          
          // Show success message
          showToast('Success', 'Session rescheduled successfully', 'success');
          
          // Reload bookings
          loadBookings();
          await loadCalendarView();

        } catch (error) {
          hideLoading(this);
          console.error('Error rescheduling session:', error);
          showToast('Error', 'Failed to reschedule session: ' + error.message, 'error');
        }
      });
      
      form.setAttribute('data-handler-added', 'true');
    }
  }
  
  // Function to defer (reschedule) booking
  async function deferBooking(deferData) {
    const response = await fetchAPI('/coach/defer-booking', {
      method: 'POST',
      body: JSON.stringify(deferData)
    });
    
    return response;
  }
  
  // Function to show cancel booking modal
  function showCancelBookingModal(bookingId) {
    const modal = document.getElementById('cancel-session-modal');
    if (!modal) return;
    
    // Set booking ID
    document.getElementById('cancel-booking-id').value = bookingId;
    
    // Show modal
    modal.classList.remove('hidden');
    
    // Add event listeners to close buttons
    document.querySelectorAll('.close-cancel-session-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        modal.classList.add('hidden');
      });
    });
    
    // Add event listener to confirm button if not already added
    const confirmBtn = document.getElementById('confirm-cancel-session-btn');
    const existingHandler = confirmBtn.getAttribute('data-handler-added');

    if (!existingHandler) {
      confirmBtn.addEventListener('click', async function() {
        const bookingId = document.getElementById('cancel-booking-id').value;
        
        try {
          await cancelSession(bookingId);
          
          // Hide modal
          modal.classList.add('hidden');
          
          // Show success message
          showToast('Success', 'Session cancelled successfully', 'success');
          
          // Reload bookings
          loadBookings();
          await loadCalendarView();
          
        } catch (error) {
          console.error('Error cancelling session:', error);
          showToast('Error', 'Failed to cancel session: ' + error.message, 'error');
        }
      });
      
      confirmBtn.setAttribute('data-handler-added', 'true');
    }
  }
  
  // Function to cancel session
  async function cancelSession(bookingId) {
    const response = await fetchAPI('/coach/cancel-session', {
      method: 'POST',
      body: JSON.stringify({ booking_id: bookingId })
    });
    
    return response;
  }
  
  // Function to show request cancellation modal for students
  function showRequestCancellationModal(bookingId) {
    // Create a modal if it doesn't exist
    const modalID = 'request-cancellation-modal';
    let modal = document.getElementById(modalID);
    
    if (!modal) {
      const modalHTML = `
        <div id="${modalID}" class="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50">
          <div class="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
            <div class="flex justify-between items-center mb-4">
              <h3 class="text-lg font-semibold">Request Cancellation</h3>
              <button class="text-gray-500 hover:text-gray-700 focus:outline-none close-modal">
                <i class="fas fa-times"></i>
              </button>
            </div>
            
            <p class="mb-4">
              Please provide a reason for cancelling this booking. Your coach will be notified of the cancellation request.
            </p>
            
            <form id="cancellation-request-form">
              <input type="hidden" id="cancellation-booking-id" name="booking_id" value="${bookingId}">
              
              <div class="mb-4">
                <label for="cancellation-reason" class="block text-gray-700 font-medium mb-2">Reason for Cancellation*</label>
                <textarea id="cancellation-reason" name="reason" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required></textarea>
              </div>
              
              <div class="flex justify-end space-x-3">
                <button type="button" class="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 focus:outline-none close-modal">
                  Cancel
                </button>
                <button type="submit" class="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 focus:outline-none">
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      `;
      
      // Append modal to body
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      modal = document.getElementById(modalID);
      
      // Add event listeners to close buttons
      modal.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
          modal.remove();
        });
      });
      
      // Add submit handler
      document.getElementById('cancellation-request-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const requestData = {
          booking_id: formData.get('booking_id'),
          reason: formData.get('reason')
        };
        
        try {
          showLoading(this);
          // For now we just show a success message
          // In a real implementation, this would call an API endpoint
          await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
          hideLoading(this);
          
          showToast('Success', 'Cancellation request submitted successfully', 'success');
          
          // Remove modal
          modal.remove();
        } catch (error) {
          hideLoading(this);
          showToast('Error', 'Failed to submit cancellation request: ' + error.message, 'error');
        }
      });
    } else {
      // Update booking ID in existing modal
      document.getElementById('cancellation-booking-id').value = bookingId;
    }
  }
  
  // Load academy coaches for coach filter (academy managers only)
  async function loadAcademyCoaches() {
    if (!IS_ACADEMY_MANAGER) return;
    
    const coachFilter = document.getElementById('coach-filter');
    if (!coachFilter) return;
    
    try {
      const coaches = await fetchAPI('/academy/coaches');
      
      // Clear existing options (except the default one)
      coachFilter.innerHTML = '<option value="">All Coaches</option>';
      
      // Add coaches to select
      coaches.forEach(coach => {
        const option = document.createElement('option');
        option.value = coach.id;
        option.textContent = `${coach.user.first_name} ${coach.user.last_name}`;
        coachFilter.appendChild(option);
      });
      
      // Add event listener to filter button
      const filterBtn = document.getElementById('apply-coach-filter');
      if (filterBtn) {
        filterBtn.addEventListener('click', function() {
          loadBookings();
        });
      }
    } catch (error) {
      console.error('Error loading academy coaches:', error);
    }
  }
  
  // Setup event listeners for bookings-related actions
  function setupBookingEventListeners() {
    // Bookings tab buttons
    const upcomingBtn = document.getElementById('upcoming-tab-btn');
    const completedBtn = document.getElementById('completed-tab-btn');
    const cancelledBtn = document.getElementById('cancelled-tab-btn');
    
    if (upcomingBtn && completedBtn && cancelledBtn) {
      // Upcoming tab button
      upcomingBtn.addEventListener('click', function() {
        // Update button styles
        upcomingBtn.classList.add('text-blue-600', 'border-blue-600');
        upcomingBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        completedBtn.classList.remove('text-blue-600', 'border-blue-600');
        completedBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        cancelledBtn.classList.remove('text-blue-600', 'border-blue-600');
        cancelledBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        // Show/hide tabs
        const upcomingTab = document.getElementById('upcoming-bookings-tab');
        const completedTab = document.getElementById('completed-bookings-tab');
        const cancelledTab = document.getElementById('cancelled-bookings-tab');
        
        if (upcomingTab) upcomingTab.classList.remove('hidden');
        if (completedTab) completedTab.classList.add('hidden');
        if (cancelledTab) cancelledTab.classList.add('hidden');
        
        currentBookingsTab = 'upcoming';
      });
      
      // Completed tab button
      completedBtn.addEventListener('click', function() {
        // Update button styles
        completedBtn.classList.add('text-blue-600', 'border-blue-600');
        completedBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        upcomingBtn.classList.remove('text-blue-600', 'border-blue-600');
        upcomingBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        cancelledBtn.classList.remove('text-blue-600', 'border-blue-600');
        cancelledBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        // Show/hide tabs
        const upcomingTab = document.getElementById('upcoming-bookings-tab');
        const completedTab = document.getElementById('completed-bookings-tab');
        const cancelledTab = document.getElementById('cancelled-bookings-tab');
        
        if (upcomingTab) upcomingTab.classList.add('hidden');
        if (completedTab) completedTab.classList.remove('hidden');
        if (cancelledTab) cancelledTab.classList.add('hidden');
        
        currentBookingsTab = 'completed';
      });
      
      // Cancelled tab button
      cancelledBtn.addEventListener('click', function() {
        // Update button styles
        cancelledBtn.classList.add('text-blue-600', 'border-blue-600');
        cancelledBtn.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        upcomingBtn.classList.remove('text-blue-600', 'border-blue-600');
        upcomingBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        completedBtn.classList.remove('text-blue-600', 'border-blue-600');
        completedBtn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        // Show/hide tabs
        const upcomingTab = document.getElementById('upcoming-bookings-tab');
        const completedTab = document.getElementById('completed-bookings-tab');
        const cancelledTab = document.getElementById('cancelled-bookings-tab');
        
        if (upcomingTab) upcomingTab.classList.add('hidden');
        if (completedTab) completedTab.classList.add('hidden');
        if (cancelledTab) cancelledTab.classList.remove('hidden');
        
        currentBookingsTab = 'cancelled';
      });
    }
    
    // Add search and filter functionality
    setupBookingFilters();
  }
  
  // Setup booking filters
  function setupBookingFilters() {
    // Upcoming bookings filters
    const upcomingSearch = document.getElementById('upcoming-search');
    const upcomingCourtFilter = document.getElementById('upcoming-filter-court');
    const upcomingSort = document.getElementById('upcoming-sort');
    const resetUpcomingFilters = document.getElementById('reset-upcoming-filters');
    
    if (upcomingSearch) {
      upcomingSearch.addEventListener('input', function() {
        filterBookings('upcoming');
      });
    }
    
    if (upcomingCourtFilter) {
      upcomingCourtFilter.addEventListener('change', function() {
        filterBookings('upcoming');
      });
    }
    
    if (upcomingSort) {
      upcomingSort.addEventListener('change', function() {
        filterBookings('upcoming');
      });
    }
    
    if (resetUpcomingFilters) {
      resetUpcomingFilters.addEventListener('click', function() {
        if (upcomingSearch) upcomingSearch.value = '';
        if (upcomingCourtFilter) upcomingCourtFilter.value = '';
        if (upcomingSort) upcomingSort.value = 'date-desc';
        filterBookings('upcoming');
      });
    }
    
    // Completed bookings filters
    const completedSearch = document.getElementById('completed-search');
    const completedCourtFilter = document.getElementById('completed-filter-court');
    const completedSort = document.getElementById('completed-sort');
    const resetCompletedFilters = document.getElementById('reset-completed-filters');
    
    if (completedSearch) {
      completedSearch.addEventListener('input', function() {
        filterBookings('completed');
      });
    }
    
    if (completedCourtFilter) {
      completedCourtFilter.addEventListener('change', function() {
        filterBookings('completed');
      });
    }
    
    if (completedSort) {
      completedSort.addEventListener('change', function() {
        filterBookings('completed');
      });
    }
    
    if (resetCompletedFilters) {
      resetCompletedFilters.addEventListener('click', function() {
        if (completedSearch) completedSearch.value = '';
        if (completedCourtFilter) completedCourtFilter.value = '';
        if (completedSort) completedSort.value = 'date-desc';
        filterBookings('completed');
      });
    }
    
    // Cancelled bookings filters
    const cancelledSearch = document.getElementById('cancelled-search');
    const cancelledCourtFilter = document.getElementById('cancelled-filter-court');
    const cancelledSort = document.getElementById('cancelled-sort');
    const resetCancelledFilters = document.getElementById('reset-cancelled-filters');
    
    if (cancelledSearch) {
      cancelledSearch.addEventListener('input', function() {
        filterBookings('cancelled');
      });
    }
    
    if (cancelledCourtFilter) {
      cancelledCourtFilter.addEventListener('change', function() {
        filterBookings('cancelled');
      });
    }
    
    if (cancelledSort) {
      cancelledSort.addEventListener('change', function() {
        filterBookings('cancelled');
      });
    }
    
    if (resetCancelledFilters) {
      resetCancelledFilters.addEventListener('click', function() {
        if (cancelledSearch) cancelledSearch.value = '';
        if (cancelledCourtFilter) cancelledCourtFilter.value = '';
        if (cancelledSort) cancelledSort.value = 'date-desc';
        filterBookings('cancelled');
      });
    }
    
    // Load courts for filters
    loadCourtsForFilters();
  }
  
  // Load courts for booking filters
  async function loadCourtsForFilters() {
    try {
      const courts = await getCourts();
      
      // Populate courts in filters
      const filterSelects = [
        document.getElementById('upcoming-filter-court'),
        document.getElementById('completed-filter-court'),
        document.getElementById('cancelled-filter-court')
      ];
      
      filterSelects.forEach(select => {
        if (!select) return;
        
        // Clear existing options (except the default one)
        select.querySelectorAll('option:not(:first-child)').forEach(option => {
          option.remove();
        });
        
        // Add courts to select
        courts.forEach(court => {
          const option = document.createElement('option');
          option.value = court.id;
          option.textContent = court.name;
          select.appendChild(option);
        });
      });
    } catch (error) {
      console.error('Error loading courts for filters:', error);
    }
  }
  
  // Filter bookings based on search and filters
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
        // Get student/coach name based on user role
        let personName = '';
        if (IS_COACH) {
          personName = `${booking.student.first_name} ${booking.student.last_name}`.toLowerCase();
        } else {
          personName = `${booking.coach.user.first_name} ${booking.coach.user.last_name}`.toLowerCase();
        }
        
        const courtName = booking.court.name.toLowerCase();
        
        return personName.includes(search) || courtName.includes(search);
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
  
  // Initialize bookings tab when page loads
  document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the bookings tab
    const bookingsTab = document.getElementById('bookings-tab');
    if (bookingsTab && bookingsTab.classList.contains('active')) {
      initBookingsTab();
    }
    
    // Add event listener to tab link to initialize when clicked
    const bookingsTabLink = document.querySelector('.bookings-tab');
    if (bookingsTabLink) {
      bookingsTabLink.addEventListener('click', function() {
        initBookingsTab();
      });
    }
  });