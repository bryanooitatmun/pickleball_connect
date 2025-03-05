// app/static/js/coach/modals.js
// Setup modal event handlers
function setupModals() {
    // Court modal
    document.getElementById('add-court-btn')?.addEventListener('click', function() {
      document.getElementById('court-modal').classList.remove('hidden');
    });
    
    document.querySelectorAll('.close-court-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('court-modal').classList.add('hidden');
      });
    });
    
    // Remove court modal
    document.querySelectorAll('.close-remove-court-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('remove-court-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-remove-court-btn')?.addEventListener('click', async function() {
      const courtId = document.getElementById('remove-court-id').value;
      
      try {
        document.getElementById('remove-court-modal').classList.add('hidden');
        await removeCoachCourt(courtId);
        showToast('Success', 'Court removed successfully.', 'success');
        loadCourts();
      } catch (error) {
        showToast('Error', 'Failed to remove court. Please try again.', 'error');
      }
    });
    
    // Delete availability modal
    document.querySelectorAll('.close-delete-availability-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('delete-availability-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-delete-availability-btn')?.addEventListener('click', async function() {
      const availabilityId = document.getElementById('delete-availability-id').value;
      
      try {
        document.getElementById('delete-availability-modal').classList.add('hidden');
        await deleteAvailability(availabilityId);
        showToast('Success', 'Availability deleted successfully.', 'success');
        loadAvailability();
      } catch (error) {
        showToast('Error', 'Failed to delete availability. Please try again.', 'error');
      }
    });
    
    // Complete session modal
    document.querySelectorAll('.close-complete-session-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('complete-session-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-complete-session-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('complete-booking-id').value;
      
      try {
        document.getElementById('complete-session-modal').classList.add('hidden');
        await completeSession(bookingId);
        showToast('Success', 'Session marked as completed.', 'success');
        loadBookings();
        updateDashboardStats();
  
        // Reload bookings data and update calendar
        await loadCalendarView();
      } catch (error) {
        showToast('Error', 'Failed to complete session. Please try again.', 'error');
      }
    });
    
    // Cancel session modal
    document.querySelectorAll('.close-cancel-session-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('cancel-session-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-cancel-session-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('cancel-booking-id').value;
      
      try {
        document.getElementById('cancel-session-modal').classList.add('hidden');
        await cancelSession(bookingId);
        showToast('Success', 'Session cancelled successfully.', 'success');
        loadBookings();
        
        // Reload bookings data and update calendar
        await loadCalendarView();
      } catch (error) {
        showToast('Error', 'Failed to cancel session. Please try again.', 'error');
      }
    });
    
    // Confirm venue modal
    document.querySelectorAll('.close-confirm-venue-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('confirm-venue-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-venue-btn')?.addEventListener('click', async function() {
      const bookingId = document.getElementById('confirm-venue-booking-id').value;
      
      try {
        document.getElementById('confirm-venue-modal').classList.add('hidden');
        await confirmVenueBooking(bookingId);
        showToast('Success', 'Venue booking confirmed successfully.', 'success');
        loadBookings();
        // Reload bookings data and update calendar
        await loadCalendarView();
      } catch (error) {
        showToast('Error', 'Failed to confirm venue booking. Please try again.', 'error');
      }
    });
    
    // Defer booking modal
    document.querySelectorAll('.close-defer-booking-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('defer-booking-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('defer-booking-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
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
        
        document.getElementById('defer-booking-modal').classList.add('hidden');
        showToast('Success', 'Session rescheduled successfully.', 'success');
        loadBookings();
        // Reload bookings data and update calendar
        await loadCalendarView();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to reschedule session. Please try again.', 'error');
      }
    });
  
    // Session log modal
    document.querySelectorAll('.close-session-log-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('session-log-modal').classList.add('hidden');
      });
    });
    
    // Delete pricing plan modal
    document.querySelectorAll('.close-delete-pricing-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('delete-pricing-modal').classList.add('hidden');
      });
    });
    
    document.getElementById('confirm-delete-pricing-btn')?.addEventListener('click', async function() {
      const planId = document.getElementById('delete-pricing-id').value;
      
      try {
        document.getElementById('delete-pricing-modal').classList.add('hidden');
        await deletePricingPlan(planId);
        showToast('Success', 'Pricing plan deleted successfully.', 'success');
        loadPricingPlans();
      } catch (error) {
        showToast('Error', 'Failed to delete pricing plan. Please try again.', 'error');
      }
    });
    
    // Template modal
    document.querySelectorAll('.close-template-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('template-modal').classList.add('hidden');
      });
    });
    
    // Toast close button
    document.getElementById('toast-close')?.addEventListener('click', function() {
      const toast = document.getElementById('toast-notification');
      toast.classList.add('translate-y-24', 'opacity-0');
      setTimeout(() => {
        toast.classList.add('hidden');
      }, 300);
    });
  }
  
  // Export functions
  export {
    setupModals
  };