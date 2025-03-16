// Pricing Plans Management
let originalPricingPlansData = [];

// Initialize the pricing tab
function initPricingTab() {
  loadPricingPlans();
  setupPricingEventListeners();
}

// Load pricing plans
async function loadPricingPlans() {
  try {
    const endpoint = IS_ACADEMY_MANAGER ? '/api/academy/pricing-plans' : '/api/coach/pricing-plans';
    const plans = await fetchAPI(endpoint);
    
    // Store the original data
    originalPricingPlansData = plans;
    
    displayPricingPlans(plans);
  } catch (error) {
    console.error('Error loading pricing plans:', error);
    showToast('Error', 'Failed to load pricing plans data.', 'error');
  }
}

// Display pricing plans
function displayPricingPlans(plans) {
  const container = document.getElementById('pricing-plans-container');
  
  if (!plans || plans.length === 0) {
    container.innerHTML = `
      <div class="text-center py-12 text-gray-500">
        <p>No pricing plans added yet</p>
      </div>
    `;
    return;
  }
  
  container.innerHTML = '';
  
  plans.forEach(plan => {
    const planCard = document.createElement('div');
    planCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
    
    // Format discount details
    let discountDetails = '';
    
    if (plan.percentage_discount) {
      discountDetails = `${plan.percentage_discount}% off`;
    } else if (plan.fixed_discount) {
      discountDetails = `$${formatCurrency(plan.fixed_discount)} off`;
    }
    
    // Format plan type details
    let planTypeDetails = '';
    
    if (plan.discount_type === 'first_time') {
      planTypeDetails = 'First-Time Student Discount';
    } else if (plan.discount_type === 'package') {
      planTypeDetails = `Package Deal (${plan.sessions_required} sessions)`;
    } else if (plan.discount_type === 'seasonal'){
      const validFrom = formatDate(plan.valid_from);
      const validTo = formatDate(plan.valid_to);
      planTypeDetails = `Seasonal Offer (Valid ${validFrom} to ${validTo})`;
    } else if (plan.discount_type === 'custom') {
      planTypeDetails = 'Custom Discount';
    }
    
    // Add academy tag if it's an academy plan (for coaches)
    const academyBadge = plan.is_academy_plan 
      ? `<span class="ml-2 px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full text-xs">Academy</span>` 
      : '';
    
    planCard.innerHTML = `
      <div class="flex justify-between">
        <div>
          <h3 class="font-semibold">${plan.name} ${academyBadge}</h3>
          <p class="text-gray-500 text-sm">${planTypeDetails}</p>
        </div>
        <div class="text-right">
          <span class="font-semibold">${discountDetails}</span>
          <p class="text-gray-500 text-sm">${plan.is_active ? 'Active' : 'Inactive'}</p>
        </div>
      </div>
      
      <p class="mt-3 text-gray-600">${plan.description}</p>
      
      <div class="flex justify-end mt-4">
        <button class="text-red-600 hover:text-red-700 delete-pricing-btn ${plan.is_academy_plan && !IS_ACADEMY_MANAGER ? 'hidden' : ''}" data-plan-id="${plan.id}">
          <i class="fas fa-trash"></i> Delete
        </button>
      </div>
    `;
    
    container.appendChild(planCard);
  });
  
  // Add event listeners for delete buttons
  document.querySelectorAll('.delete-pricing-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const planId = this.getAttribute('data-plan-id');
      document.getElementById('delete-pricing-id').value = planId;
      document.getElementById('delete-pricing-modal').classList.remove('hidden');
    });
  });
}

// Setup pricing event listeners
function setupPricingEventListeners() {
  // Pricing discount type change handler
  document.getElementById('pricing-discount-type')?.addEventListener('change', function() {
    const discountType = this.value;
    const discountFields = document.querySelectorAll('.pricing-type-fields');
    
    // Hide all discount fields
    discountFields.forEach(field => {
      field.classList.add('hidden');
    });
    
    // Show fields based on discount type
    if (discountType === 'first_time') {
      document.getElementById('first-time-fields').classList.remove('hidden');
    } else if (discountType === 'package') {
      document.getElementById('pricing-package-fields').classList.remove('hidden');
    } else if (discountType === 'seasonal') {
      document.getElementById('seasonal-fields').classList.remove('hidden');
    } else if (discountType === 'custom') {
      document.getElementById('custom-fields').classList.remove('hidden');
    }
  });

  // Pricing form submit handler
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
    
    // Add academy plan flag if academy manager
    if (IS_ACADEMY_MANAGER) {
      planData.is_academy_plan = formData.get('is_academy_plan') ? true : false;
    }
    
    try {
      showLoading(this);
      const endpoint = IS_ACADEMY_MANAGER ? '/api/academy/pricing-plans/add' : '/api/coach/pricing-plans/add';
      await fetchAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify(planData)
      });
      hideLoading(this);
      showToast('Success', 'Pricing plan added successfully.', 'success');
      this.reset();
      
      // Hide all discount fields
      document.querySelectorAll('.pricing-type-fields').forEach(field => {
        field.classList.add('hidden');
      });
      
      loadPricingPlans();
    } catch (error) {
      hideLoading(this);
      showToast('Error', 'Failed to add pricing plan. Please try again.', 'error');
    }
  });
  
  // Delete pricing plan confirmation
  document.getElementById('confirm-delete-pricing-btn')?.addEventListener('click', async function() {
    const planId = document.getElementById('delete-pricing-id').value;
    
    try {
      document.getElementById('delete-pricing-modal').classList.add('hidden');
      const endpoint = IS_ACADEMY_MANAGER ? '/api/academy/pricing-plans/delete' : '/api/coach/pricing-plans/delete';
      await fetchAPI(endpoint, {
        method: 'POST',
        body: JSON.stringify({ plan_id: planId })
      });
      showToast('Success', 'Pricing plan deleted successfully.', 'success');
      loadPricingPlans();
    } catch (error) {
      showToast('Error', 'Failed to delete pricing plan. Please try again.', 'error');
    }
  });
  
  // Close pricing modal
  document.querySelectorAll('.close-delete-pricing-modal').forEach(btn => {
    btn.addEventListener('click', function() {
      document.getElementById('delete-pricing-modal').classList.add('hidden');
    });
  });
}