document.addEventListener('DOMContentLoaded', function() {
    // Initialize booking tabs
    initBookingTabs();
    
    // Initialize booking actions
    initBookingActions();
    
    // Load bookings on page load
    loadBookings();
    
    // Initialize package approval handling
    initPackageApproval();
  });
  
  // Initialize booking tabs
  function initBookingTabs() {
    const upcomingBtn = document.getElementById('upcoming-tab-btn');
    const completedBtn = document.getElementById('completed-tab-btn');
    const cancelledBtn = document.getElementById('cancelled-tab-btn');
    const packagesBtn = document.getElementById('packages-tab-btn');
    
    const upcomingTab = document.getElementById('upcoming-bookings-tab');
    const completedTab = document.getElementById('completed-bookings-tab');
    const cancelledTab = document.getElementById('cancelled-bookings-tab');
    const packagesTab = document.getElementById('packages-tab');
    
    // Handle upcoming tab
    if (upcomingBtn && upcomingTab) {
      upcomingBtn.addEventListener('click', function() {
        setActiveTab(upcomingBtn, upcomingTab);
      });
    }
    
    // Handle completed tab
    if (completedBtn && completedTab) {
      completedBtn.addEventListener('click', function() {
        setActiveTab(completedBtn, completedTab);
      });
    }
    
    // Handle cancelled tab
    if (cancelledBtn && cancelledTab) {
      cancelledBtn.addEventListener('click', function() {
        setActiveTab(cancelledBtn, cancelledTab);
      });
    }
    
    // Handle packages tab
    if (packagesBtn && packagesTab) {
      packagesBtn.addEventListener('click', function() {
        setActiveTab(packagesBtn, packagesTab);
      });
    }
    
    // Set active tab
    function setActiveTab(button, tabContent) {
      // Update button styles
      [upcomingBtn, completedBtn, cancelledBtn, packagesBtn].forEach(btn => {
        if (btn) {
          btn.classList.remove('text-blue-600', 'border-blue-600');
          btn.classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        }
      });
      
      button.classList.add('text-blue-600', 'border-blue-600');
      button.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      // Update tab content
      [upcomingTab, completedTab, cancelledTab, packagesTab].forEach(tab => {
        if (tab) {
          tab.classList.add('hidden');
          tab.classList.remove('active');
        }
      });
      
      tabContent.classList.remove('hidden');
      tabContent.classList.add('active');
    }
    
    // Add search and filter functionality
    initBookingFilters();
  }
  
  // Initialize booking filters
  function initBookingFilters() {
    // Search filters for upcoming bookings
    document.getElementById('upcoming-search')?.addEventListener('input', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('upcoming-filter-court')?.addEventListener('change', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('upcoming-filter-coach')?.addEventListener('change', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('upcoming-sort')?.addEventListener('change', function() {
      filterBookings('upcoming');
    });
    
    document.getElementById('reset-upcoming-filters')?.addEventListener('click', function() {
      resetFilters('upcoming');
    });
    
    // Similar for completed bookings
    document.getElementById('completed-search')?.addEventListener('input', function() {
      filterBookings('completed');
    });
    
    document.getElementById('completed-filter-court')?.addEventListener('change', function() {
      filterBookings('completed');
    });
    
    document.getElementById('completed-filter-coach')?.addEventListener('change', function() {
      filterBookings('completed');
    });
    
    document.getElementById('completed-sort')?.addEventListener('change', function() {
      filterBookings('completed');
    });
    
    document.getElementById('reset-completed-filters')?.addEventListener('click', function() {
      resetFilters('completed');
    });
    
    // Similar for cancelled bookings
    document.getElementById('cancelled-search')?.addEventListener('input', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('cancelled-filter-court')?.addEventListener('change', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('cancelled-filter-coach')?.addEventListener('change', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('cancelled-sort')?.addEventListener('change', function() {
      filterBookings('cancelled');
    });
    
    document.getElementById('reset-cancelled-filters')?.addEventListener('click', function() {
      resetFilters('cancelled');
    });
    
    // Package filters
    document.getElementById('packages-search')?.addEventListener('input', function() {
      filterPackages();
    });
    
    document.getElementById('packages-filter-coach')?.addEventListener('change', function() {
      filterPackages();
    });
    
    document.getElementById('packages-filter-status')?.addEventListener('change', function() {
      filterPackages();
    });
    
    document.getElementById('packages-sort')?.addEventListener('change', function() {
      filterPackages();
    });
    
    document.getElementById('reset-packages-filters')?.addEventListener('click', function() {
      resetPackageFilters();
    });
  }
  
  // Initialize booking action handlers
  function initBookingActions() {
    // Confirm venue modal
    document.getElementById('confirm-venue-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('confirm-venue-booking-id').value;
      const modal = document.getElementById('confirm-venue-modal');
      const bookingResponsibility = modal.getAttribute('data-booking-responsibility');
      
      try {
        showLoading(this);
        
        // Handle different responsibilities
        if (bookingResponsibility === 'coach') {
          // For coach responsibility, need to upload court booking proof
          const fileInput = document.getElementById('court-booking-proof');
          
          if (!fileInput.files || fileInput.files.length === 0) {
            showToast('Error', 'Please upload court booking proof', 'error');
            hideLoading(this);
            return;
          }
          
          const formData = new FormData();
          formData.append('booking_id', bookingId);
          formData.append('court_booking_proof', fileInput.files[0]);
          
          // Upload court booking proof
          await fetch('/api/coach/upload-court-booking-proof', {
            method: 'POST',
            body: formData
          });
        }
        
        // Confirm venue booking
        await fetchAPI('/coach/confirm-venue', {
          method: 'POST',
          body: JSON.stringify({ booking_id: bookingId })
        });
        
        hideLoading(this);
        modal.classList.add('hidden');
        
        showToast('Success', 'Venue booking confirmed successfully', 'success');
        
        // Reload bookings to reflect changes
        loadBookings();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to confirm venue: ${error.message}`, 'error');
      }
    });
    
    // Complete session button
    document.getElementById('confirm-complete-session-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('complete-booking-id').value;
      
      try {
        showLoading(this);
        
        await fetchAPI('/coach/complete-session', {
          method: 'POST',
          body: JSON.stringify({ booking_id: bookingId })
        });
        
        hideLoading(this);
        document.getElementById('complete-session-modal').classList.add('hidden');
        
        showToast('Success', 'Session marked as completed', 'success');
        
        // Reload bookings
        loadBookings();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to complete session: ${error.message}`, 'error');
      }
    });
    
    // Cancel session button
    document.getElementById('confirm-cancel-session-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('cancel-booking-id').value;
      const reason = document.getElementById('cancel-reason').value;
      
      try {
        showLoading(this);
        
        await fetchAPI('/coach/cancel-session', {
          method: 'POST',
          body: JSON.stringify({ 
            booking_id: bookingId,
            reason: reason
          })
        });
        
        hideLoading(this);
        document.getElementById('cancel-session-modal').classList.add('hidden');
        
        showToast('Success', 'Session cancelled successfully', 'success');
        
        // Reload bookings
        loadBookings();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to cancel session: ${error.message}`, 'error');
      }
    });
    
    // Defer (reschedule) booking form submission
    document.getElementById('defer-booking-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const bookingId = formData.get('booking_id');
      const date = formData.get('date');
      const startTime = formData.get('start_time');
      const endTime = formData.get('end_time');
      const courtId = formData.get('court_id');
      const reason = formData.get('reason');
      
      try {
        showLoading(this);
        
        await fetchAPI('/coach/defer-booking', {
          method: 'POST',
          body: JSON.stringify({
            booking_id: bookingId,
            date: date,
            start_time: startTime,
            end_time: endTime,
            court_id: courtId,
            reason: reason
          })
        });
        
        hideLoading(this);
        document.getElementById('defer-booking-modal').classList.add('hidden');
        
        showToast('Success', 'Session rescheduled successfully', 'success');
        
        // Reload bookings
        loadBookings();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to reschedule session: ${error.message}`, 'error');
      }
    });
    
    // Upload court booking proof
    document.getElementById('upload-court-proof-btn')?.addEventListener('click', function() {
      document.getElementById('court-booking-proof').click();
    });
    
    document.getElementById('court-booking-proof')?.addEventListener('change', function() {
      if (this.files && this.files.length > 0) {
        const filename = this.files[0].name;
        document.getElementById('court-proof-filename').textContent = filename;
      }
    });
  }
  
  // Initialize payment proof viewing modal
  function initViewPaymentProofModal() {
    document.addEventListener('click', function(e) {
      // Find closest view proof button
      const viewProofBtn = e.target.closest('.view-proof-btn');
      
      if (viewProofBtn) {
        const bookingId = viewProofBtn.getAttribute('data-booking-id');
        const proofType = viewProofBtn.getAttribute('data-proof-type');
        
        openPaymentProofModal(bookingId, proofType);
      }
    });
  }
  
  // Open payment proof modal
  async function openPaymentProofModal(bookingId, proofType) {
    try {
      const modal = document.getElementById('view-payment-proof-modal');
      const titleEl = document.getElementById('proof-modal-title');
      
      // Set modal title based on proof type
      if (proofType === 'court') {
        titleEl.textContent = 'Court Booking Proof';
      } else if (proofType === 'payment') {
        titleEl.textContent = 'Payment Proof';
      } else {
        titleEl.textContent = 'Booking Proofs';
      }
      
      document.getElementById('proof-booking-id').value = bookingId;
      
      // Show loading state
      modal.classList.add('loading');
      modal.classList.remove('hidden');
      
      // Get booking details and proofs
      const booking = await fetchAPI(`/coach/booking/${bookingId}`);
      
      // Fill booking details
      document.getElementById('proof-student-name').textContent = `${booking.student.first_name} ${booking.student.last_name}`;
      document.getElementById('proof-court-name').textContent = booking.court.name;
      document.getElementById('proof-date').textContent = formatDate(booking.date);
      document.getElementById('proof-time').textContent = `${formatTime(booking.start_time)} - ${formatTime(booking.end_time)}`;
      
      // Handle court proof if available
      const courtProofContainer = document.getElementById('court-proof-container');
      if (booking.court_booking_proof) {
        courtProofContainer.classList.remove('hidden');
        document.getElementById('court-booking-proof-img').src = booking.court_booking_proof;
      } else {
        courtProofContainer.classList.add('hidden');
      }
      
      // Handle payment proof if available
      const paymentProofContainer = document.getElementById('payment-proof-container');
      if (booking.payment_proof) {
        paymentProofContainer.classList.remove('hidden');
        document.getElementById('coaching-payment-proof-img').src = booking.payment_proof;
      } else {
        paymentProofContainer.classList.add('hidden');
      }
      
      // Show/hide approve buttons for admin/manager
      const approveBtn = document.getElementById('approve-proof-btn');
      const rejectBtn = document.getElementById('reject-proof-btn');
      
      if ((proofType === 'payment' || proofType === 'both') && booking.coaching_payment_status === 'uploaded') {
        approveBtn.classList.remove('hidden');
        rejectBtn.classList.remove('hidden');
        approveBtn.setAttribute('data-proof-type', 'payment');
      } else if (proofType === 'court' && booking.court_payment_status === 'uploaded') {
        approveBtn.classList.remove('hidden');
        rejectBtn.classList.remove('hidden');
        approveBtn.setAttribute('data-proof-type', 'court');
      } else {
        approveBtn.classList.add('hidden');
        rejectBtn.classList.add('hidden');
      }
      
      // Remove loading state
      modal.classList.remove('loading');
      
    } catch (error) {
      console.error('Error loading payment proof:', error);
      showToast('Error', 'Failed to load payment proof', 'error');
      document.getElementById('view-payment-proof-modal').classList.add('hidden');
    }
  }
  
  // Show venue confirmation modal
  function showConfirmVenueModal(bookingId) {
    const modal = document.getElementById('confirm-venue-modal');
    modal.classList.add('loading');
    modal.classList.remove('hidden');
    
    document.getElementById('confirm-venue-booking-id').value = bookingId;
    
    // Get booking details to check responsibility and show appropriate sections
    fetchAPI(`/coach/booking/${bookingId}`)
      .then(booking => {
        // Set booking responsibility data attribute
        const responsibility = booking.student_books_court ? 'student' : 'coach';
        modal.setAttribute('data-booking-responsibility', responsibility);
        
        // Show appropriate sections based on responsibility
        const coachSection = document.getElementById('coach-books-court-section');
        const studentSection = document.getElementById('student-books-court-section');
        const proofsContainer = document.getElementById('existing-proofs-container');
        
        if (responsibility === 'coach') {
          // Coach is responsible for booking the court
          coachSection.classList.remove('hidden');
          studentSection.classList.add('hidden');
          
          // Show booking instructions if available
          const instructionsContainer = document.getElementById('court-booking-instructions-container');
          const instructionsText = document.getElementById('court-booking-instructions');
          
          if (booking.court_booking_instructions) {
            instructionsContainer.classList.remove('hidden');
            instructionsText.textContent = booking.court_booking_instructions;
          } else {
            instructionsContainer.classList.add('hidden');
          }
          
          // Set court booking link if available
          const linkContainer = document.getElementById('court-booking-link-container');
          const linkElement = document.getElementById('court-booking-link');
          
          if (booking.court.booking_link) {
            linkContainer.classList.remove('hidden');
            linkElement.href = booking.court.booking_link;
          } else {
            linkContainer.classList.add('hidden');
          }
        } else {
          // Student is responsible for booking the court
          coachSection.classList.add('hidden');
          studentSection.classList.remove('hidden');
        }
        
        // Show proofs if available
        const courtProofPreview = document.getElementById('court-proof-preview');
        const paymentProofPreview = document.getElementById('payment-proof-preview');
        
        if (booking.court_booking_proof || booking.payment_proof) {
          proofsContainer.classList.remove('hidden');
          
          if (booking.court_booking_proof) {
            courtProofPreview.classList.remove('hidden');
            document.getElementById('court-proof-image').src = booking.court_booking_proof;
          } else {
            courtProofPreview.classList.add('hidden');
          }
          
          if (booking.payment_proof) {
            paymentProofPreview.classList.remove('hidden');
            document.getElementById('payment-proof-image').src = booking.payment_proof;
          } else {
            paymentProofPreview.classList.add('hidden');
          }
        } else {
          proofsContainer.classList.add('hidden');
        }
        
        // Remove loading state
        modal.classList.remove('loading');
      })
      .catch(error => {
        console.error('Error loading booking details:', error);
        showToast('Error', 'Failed to load booking details', 'error');
        modal.classList.add('hidden');
      });
  }
  
  // Initialize package approval
  function initPackageApproval() {
    // Package approval button
    document.getElementById('approve-package-btn')?.addEventListener('click', async function() {
      const packageId = document.getElementById('package-id').value;
      
      try {
        showLoading(this);
        
        await fetchAPI('/coach/approve-package', {
          method: 'POST',
          body: JSON.stringify({ package_id: packageId })
        });
        
        hideLoading(this);
        document.getElementById('package-approval-modal').classList.add('hidden');
        
        showToast('Success', 'Package approved successfully', 'success');
        
        // Reload packages
        loadPackages();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to approve package: ${error.message}`, 'error');
      }
    });
    
    // Package rejection button
    document.getElementById('reject-package-btn')?.addEventListener('click', async function() {
      const packageId = document.getElementById('package-id').value;
      const reasonContainer = document.getElementById('rejection-reason-container');
      
      // Show reason input if not already visible
      if (reasonContainer.classList.contains('hidden')) {
        reasonContainer.classList.remove('hidden');
        return;
      }
      
      const reason = document.getElementById('rejection-reason').value;
      
      if (!reason) {
        showToast('Error', 'Please provide a reason for rejection', 'error');
        return;
      }
      
      try {
        showLoading(this);
        
        await fetchAPI('/coach/reject-package', {
          method: 'POST',
          body: JSON.stringify({ 
            package_id: packageId,
            reason: reason
          })
        });
        
        hideLoading(this);
        document.getElementById('package-approval-modal').classList.add('hidden');
        
        showToast('Success', 'Package rejected successfully', 'success');
        
        // Reload packages
        loadPackages();
        
      } catch (error) {
        hideLoading(this);
        showToast('Error', `Failed to reject package: ${error.message}`, 'error');
      }
    });
  }
  
  // Helper functions for filtering and formatting
  function filterBookings(status) {
    // Implement booking filtering based on search, court, coach, and sort
  }
  
  function filterPackages() {
    // Implement package filtering based on search, coach, status, and sort
  }
  
  function resetFilters(status) {
    document.getElementById(`${status}-search`).value = '';
    document.getElementById(`${status}-filter-court`).value = '';
    
    if (document.getElementById(`${status}-filter-coach`)) {
      document.getElementById(`${status}-filter-coach`).value = '';
    }
    
    document.getElementById(`${status}-sort`).value = 'date-desc';
    
    // Reload original data
    displayBookings(window[`original${capitalize(status)}Bookings`], status);
  }
  
  function resetPackageFilters() {
    document.getElementById('packages-search').value = '';
    document.getElementById('packages-filter-coach').value = '';
    document.getElementById('packages-filter-status').value = 'pending';
    document.getElementById('packages-sort').value = 'date-desc';
    
    // Reload original data
    displayPackages(window.originalPackages);
  }
  
  function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
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