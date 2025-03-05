// app/static/js/coach/pricing.js
// Load pricing plans
async function loadPricingPlans() {
    try {
      const plans = await getPricingPlans();
      
      const container = document.getElementById('pricing-plans-container');
      if (!container) return;
      
      if (plans.length === 0) {
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
          discountDetails = `$${plan.fixed_discount} off`;
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
        
        planCard.innerHTML = `
          <div class="flex justify-between">
            <div>
              <h3 class="font-semibold">${plan.name}</h3>
              <p class="text-gray-500 text-sm">${planTypeDetails}</p>
            </div>
            <div class="text-right">
              <span class="font-semibold">${discountDetails}</span>
              <p class="text-gray-500 text-sm">${plan.is_active ? 'Active' : 'Inactive'}</p>
            </div>
          </div>
          
          <p class="mt-3 text-gray-600">${plan.description}</p>
          
          <div class="flex justify-end mt-4">
            <button class="text-red-600 hover:text-red-700 delete-pricing-btn" data-plan-id="${plan.id}">
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
      
    } catch (error) {
      console.error('Error loading pricing plans:', error);
      showToast('Error', 'Failed to load pricing plans data.', 'error');
    }
  }
  
  // Initialize pricing plan discount type change handler
  function initializePricingFormHandlers() {
    document.getElementById('pricing-discount-type')?.addEventListener('change', function() {
      const discountType = this.value;
      const discountFields = document.querySelectorAll('.pricing-type-fields');
      
      // Hide all discount fields
      discountFields.forEach(field => {
        field.classList.add('hidden');
      });
      
      // Show fields based on discount type
      if (discountType === 'first_time') {
        document.getElementById('first-time-fields')?.classList.remove('hidden');
      } else if (discountType === 'package') {
        document.getElementById('package-fields')?.classList.remove('hidden');
      } else if (discountType === 'seasonal') {
        document.getElementById('seasonal-fields')?.classList.remove('hidden');
      } else if (discountType === 'custom') {
        document.getElementById('custom-fields')?.classList.remove('hidden');
      }
    });
  }
  
  // Export functions
  export {
    loadPricingPlans,
    initializePricingFormHandlers
  };