// app/static/js/coach/forms.js
// Setup form submit handlers
function setupForms() {
    // Profile form
    document.getElementById('profile-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const profileData = {
        user: {
          first_name: formData.get('first_name'),
          last_name: formData.get('last_name'),
          email: formData.get('email'),
          gender: formData.get('gender'),
          location: formData.get('location'),
          dupr_rating: parseFloat(formData.get('dupr_rating'))
        },
        coach: {
          hourly_rate: parseFloat(formData.get('hourly_rate')),
          years_experience: parseInt(formData.get('years_experience')),
          specialties: formData.get('specialties'),
          biography: formData.get('biography')
        }
      };
      
      try {
        showLoading(this);
        await updateCoachProfile(profileData);
        hideLoading(this);
        showToast('Success', 'Your profile has been updated successfully.', 'success');
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to update profile. Please try again.', 'error');
      }
    });
    
    // Password form
    document.getElementById('password-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const currentPassword = formData.get('current_password');
      const newPassword = formData.get('new_password');
      const confirmPassword = formData.get('confirm_password');
      
      if (newPassword !== confirmPassword) {
        showToast('Error', 'New passwords do not match.', 'error');
        return;
      }
      
      try {
        showLoading(this);
        await changePassword({
          current_password: currentPassword,
          new_password: newPassword
        });
        hideLoading(this);
        showToast('Success', 'Your password has been changed successfully.', 'success');
        this.reset();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to change password. Please check your current password and try again.', 'error');
      }
    });
    
    // Court form
    document.getElementById('court-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const courtId = document.getElementById('court-select').value;
      
      if (!courtId) {
        showToast('Error', 'Please select a court.', 'error');
        return;
      }
      
      try {
        showLoading(this);
        await addCoachCourt(courtId);
        hideLoading(this);
        document.querySelector('.close-court-modal')?.click();
        showToast('Success', 'Court added successfully.', 'success');
        loadCourts();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to add court. Please try again.', 'error');
      }
    });
    
    // Availability form
    document.getElementById('availability-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const availabilityData = {
        court_id: formData.get('court_id'),
        date: formData.get('date'),
        start_time: formData.get('start_time'),
        end_time: formData.get('end_time')
      };
      
      // Validate time
      if (availabilityData.start_time >= availabilityData.end_time) {
        showToast('Error', 'End time must be after start time.', 'error');
        return;
      }
      
      try {
        showLoading(this);
        await addAvailability(availabilityData);
        hideLoading(this);
        showToast('Success', 'Availability added successfully.', 'success');
        this.reset();
        loadAvailability();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to add availability. Please try again.', 'error');
      }
    });
    
    // Session log form
    document.getElementById('session-log-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const logData = {
        log_id: formData.get('log_id'),
        booking_id: formData.get('booking_id'),
        title: formData.get('title'),
        notes: formData.get('notes'),
        coach_notes: formData.get('coach_notes')
      };
      
      try {
        showLoading(this);
        await updateSessionLog(logData);
        hideLoading(this);
        document.querySelector('.close-session-log-modal')?.click();
        showToast('Success', 'Session log updated successfully.', 'success');
        loadSessionLogs();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to update session log. Please try again.', 'error');
      }
    });
    
    // Pricing form
    document.getElementById('pricing-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const discountType = formData.get('discount_type');
      
      let planData = {
        name: formData.get('name'),
        description: formData.get('description'),
        discount_type: discountType,
        is_active: formData.get('is_active') ? true : false
      };
      
      // Add fields based on discount type
      if (discountType === 'first_time') {
        const amountType = formData.get('discount_amount_type');
        if (amountType === 'percentage') {
          planData.percentage_discount = parseFloat(formData.get('discount_amount'));
        } else {
          planData.fixed_discount = parseFloat(formData.get('discount_amount'));
        }
        planData.first_time_only = true;
      }
      else if (discountType === 'package') {
        const amountType = formData.get('package_discount_type');
        if (amountType === 'percentage') {
          planData.percentage_discount = parseFloat(formData.get('package_discount_amount'));
        } else {
          planData.fixed_discount = parseFloat(formData.get('package_discount_amount'));
        }
        planData.sessions_required = parseInt(formData.get('sessions_required'));
      }
      else if (discountType === 'seasonal') {
        const amountType = formData.get('seasonal_discount_type');
        if (amountType === 'percentage') {
          planData.percentage_discount = parseFloat(formData.get('seasonal_discount_amount'));
        } else {
          planData.fixed_discount = parseFloat(formData.get('seasonal_discount_amount'));
        }
        planData.valid_from = formData.get('valid_from');
        planData.valid_to = formData.get('valid_to');
      }
      else if (discountType === 'custom') {
        const amountType = formData.get('custom_discount_type');
        if (amountType === 'percentage') {
          planData.percentage_discount = parseFloat(formData.get('custom_discount_amount'));
        } else {
          planData.fixed_discount = parseFloat(formData.get('custom_discount_amount'));
        }
      }
      
      try {
        showLoading(this);
        await addPricingPlan(planData);
        hideLoading(this);
        showToast('Success', 'Pricing plan added successfully.', 'success');
        this.reset();
        loadPricingPlans();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to add pricing plan. Please try again.', 'error');
      }
    });
  
    // Add availability filter event listeners
    document.getElementById('availability-filter-court')?.addEventListener('change', function() {
      filterAvailability();
    });
  
    document.getElementById('availability-filter-date')?.addEventListener('change', function() {
      filterAvailability();
    });
  
    // Add session logs filter event listeners
    document.getElementById('session-logs-search')?.addEventListener('input', function() {
      filterSessionLogs();
    });
  
    document.getElementById('session-logs-filter-court')?.addEventListener('change', function() {
      filterSessionLogs();
    });
  
    document.getElementById('session-logs-sort')?.addEventListener('change', function() {
      filterSessionLogs();
    });
  }
  
  // Export functions
  export {
    setupForms
  };