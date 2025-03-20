// Packages Management
let originalPackagesData = {
    myPackages: [],
    purchasedPackages: [],
    academyPackages: []
  };
  
  // Initialize the packages tab
  function initPackagesTab() {
    loadPackagesData();
    setupPackagesEventListeners();
  }
  
  // Load packages data
  async function loadPackagesData() {
    try {
      // Load my packages
      const myPackagesEndpoint = IS_ACADEMY_MANAGER ? '/academy/packages' : '/coach/packages';
      const myPackages = await fetchAPI(myPackagesEndpoint);
      originalPackagesData.myPackages = myPackages;
      displayMyPackages(myPackages);
      
      // Load purchased packages
      const purchasedPackagesEndpoint = IS_ACADEMY_MANAGER ? '/academy/packages/purchased' : '/coach/packages/purchased';
      const purchasedPackages = await fetchAPI(purchasedPackagesEndpoint);
      originalPackagesData.purchasedPackages = purchasedPackages;
      displayPurchasedPackages(purchasedPackages);
      
      // Load academy packages (if academy manager)
      if (IS_ACADEMY_MANAGER) {
        const academyPackagesEndpoint = '/academy/packages/all';
        const academyPackages = await fetchAPI(academyPackagesEndpoint);
        originalPackagesData.academyPackages = academyPackages;
        displayAcademyPackages(academyPackages);
        
        // Populate coach filter
        populateCoachFilter(document.getElementById('academy-package-coach-filter'));
      }
    } catch (error) {
      console.error('Error loading packages data:', error);
      showToast('Error', 'Failed to load packages data.', 'error');
    }
  }
  
  // Display my packages
  function displayMyPackages(packages) {
    const container = document.getElementById('my-packages-tab');
    
    if (!packages || packages.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No packages created yet</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    packages.forEach(pkg => {
      const packageCard = document.createElement('div');
      packageCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
      
      // Add academy badge if needed
      const academyBadge = pkg.is_academy_package 
        ? `<span class="ml-2 px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full text-xs">Academy</span>` 
        : '';
      
      packageCard.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${pkg.name} ${academyBadge}</h3>
            <p class="text-gray-500 text-sm">${pkg.sessions} sessions · Valid for ${pkg.validity_days} days</p>
          </div>
          <div class="text-right">
            <span class="font-semibold">$${formatCurrency(pkg.price)}</span>
            <p class="text-gray-500 text-sm">${pkg.is_active ? 'Active' : 'Inactive'}</p>
          </div>
        </div>
        
        <p class="mt-3 text-gray-600">${pkg.description}</p>
        
        <div class="flex justify-end mt-4">
          <button class="text-blue-600 hover:text-blue-700 mr-4 view-package-btn hidden" data-package-id="${pkg.id}">
            <i class="fas fa-eye"></i> View
          </button>
          <button class="text-red-600 hover:text-red-700 delete-package-btn ${pkg.is_academy_package && !IS_ACADEMY_MANAGER ? 'hidden' : ''}" data-package-id="${pkg.id}">
            <i class="fas fa-trash"></i> Delete
          </button>
        </div>
      `;
      
      container.appendChild(packageCard);
    });
    
    // Add event listeners
    // container.querySelectorAll('.view-package-btn').forEach(btn => {
    //   btn.addEventListener('click', function() {
    //     const packageId = this.getAttribute('data-package-id');
    //     viewPackageDetails(packageId);
    //   });
    // });
    
    container.querySelectorAll('.delete-package-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const packageId = this.getAttribute('data-package-id');
        document.getElementById('delete-package-id').value = packageId;
        document.getElementById('delete-package-modal').classList.remove('hidden');
      });
    });
  }
  
  // Display purchased packages
  function displayPurchasedPackages(packages) {
    const container = document.getElementById('purchased-packages-container');
    
    if (!packages || packages.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No purchased packages found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    packages.forEach(purchase => {
      const purchaseCard = document.createElement('div');
      purchaseCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
      
      // Format status with appropriate color
      let statusClass = '';
      switch (purchase.status) {
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
      
      // Format dates
      const purchaseDate = formatDate(purchase.purchase_date);
      let expiryDate = '';
      if (purchase.expires_at) {
        expiryDate = formatDate(purchase.expires_at);
      }
      
      // Create appropriate action buttons based on status
      let actionButtons = '';
      if (purchase.status === 'pending') {
        actionButtons = `
          <button class="bg-green-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-green-700 approve-purchase-btn" data-purchase-id="${purchase.id}">
            <i class="fas fa-check-circle mr-1"></i> Approve
          </button>
        `;
      }
      
      purchaseCard.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${purchase.pricing_plan.name}</h3>
            <p class="text-gray-500 text-sm">
              Purchased by ${purchase.student.name} on ${purchaseDate}
            </p>
          </div>
          <div class="text-right">
            <span class="px-2 py-1 rounded-full text-xs ${statusClass} capitalize">${purchase.status}</span>
            <p class="text-gray-600 text-sm mt-1">
              ${purchase.sessions_used || 0}/${purchase.total_sessions} sessions used
            </p>
          </div>
        </div>
        
        <div class="mt-3 grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Purchase Date:</span> ${purchaseDate}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Expiry Date:</span> ${expiryDate || 'N/A'}
            </p>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Payment Method:</span> ${purchase.payment_method || 'N/A'}
            </p>
          </div>
        </div>
        
        <div class="flex justify-end mt-4">
          ${actionButtons}
          <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 ml-2 view-payment-proof-btn" data-purchase-id="${purchase.id}">
            <i class="fas fa-file-image mr-1"></i> Payment Proof
          </button>
        </div>
      `;
      
      container.appendChild(purchaseCard);
    });
    
    // Add event listeners
    container.querySelectorAll('.approve-purchase-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const purchaseId = this.getAttribute('data-purchase-id');
        showApprovePurchaseModal(purchaseId);
      });
    });
    
    container.querySelectorAll('.view-payment-proof-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const purchaseId = this.getAttribute('data-purchase-id');
        viewPaymentProof(purchaseId);
      });
    });
  }
  
  // Display academy packages (for academy manager)
  function displayAcademyPackages(packages) {
    const container = document.getElementById('academy-packages-container');
    
    if (!packages || packages.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No academy packages found</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    packages.forEach(purchase => {
      const purchaseCard = document.createElement('div');
      purchaseCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
      
      // Format status with appropriate color
      let statusClass = '';
      switch (purchase.status) {
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
      
      purchaseCard.innerHTML = `
        <div class="flex justify-between">
          <div>
            <h3 class="font-semibold">${purchase.pricing_plan.name}</h3>
            <p class="text-gray-500 text-sm">
              Student: ${purchase.student.name} · 
              Coach: ${purchase.coach?.name || 'Not Assigned'}
            </p>
          </div>
          <div class="text-right">
            <span class="px-2 py-1 rounded-full text-xs ${statusClass} capitalize">${purchase.status}</span>
            <p class="text-gray-600 text-sm mt-1">
              ${purchase.sessions_used || 0}/${purchase.total_sessions} sessions used
            </p>
          </div>
        </div>
        
        <div class="mt-3 grid grid-cols-2 gap-4">
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Purchase Date:</span> ${formatDate(purchase.purchase_date)}
            </p>
          </div>
          <div>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Expiry Date:</span> ${purchase.expirys_at ? formatDate(purchase.expirys_at) : 'N/A'}
            </p>
            <p class="text-sm text-gray-600">
              <span class="font-medium">Payment Method:</span> ${purchase.payment_method || 'N/A'}
            </p>
          </div>
        </div>
        
        <div class="flex justify-end mt-4">
          ${purchase.status === 'pending' ? `
            <button class="bg-green-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-green-700 approve-academy-purchase-btn" data-purchase-id="${purchase.id}">
              <i class="fas fa-check-circle mr-1"></i> Approve
            </button>
          ` : ''}
          <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium hover:bg-blue-700 ml-2 view-academy-payment-proof-btn" data-purchase-id="${purchase.id}">
            <i class="fas fa-file-image mr-1"></i> Payment Proof
          </button>
        </div>
      `;
      
      container.appendChild(purchaseCard);
    });
    
    // Add event listeners
    container.querySelectorAll('.approve-academy-purchase-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const purchaseId = this.getAttribute('data-purchase-id');
        showApprovePurchaseModal(purchaseId, true);
      });
    });
    
    container.querySelectorAll('.view-academy-payment-proof-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const purchaseId = this.getAttribute('data-purchase-id');
        viewPaymentProof(purchaseId, true);
      });
    });
  }
  
  // Setup packages event listeners
  function setupPackagesEventListeners() {
    // Package tabs
    document.getElementById('my-packages-tab-btn')?.addEventListener('click', function() {
      this.classList.add('text-blue-600', 'border-blue-600');
      this.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      document.getElementById('purchased-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
      document.getElementById('purchased-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      if (IS_ACADEMY_MANAGER) {
        document.getElementById('academy-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
        document.getElementById('academy-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      }
      
      document.getElementById('my-packages-tab').classList.remove('hidden');
      document.getElementById('my-packages-tab').classList.add('active');
      
      document.getElementById('purchased-packages-tab').classList.add('hidden');
      document.getElementById('purchased-packages-tab').classList.remove('active');
      
      if (IS_ACADEMY_MANAGER) {
        document.getElementById('academy-packages-tab').classList.add('hidden');
        document.getElementById('academy-packages-tab').classList.remove('active');
      }
    });
    
    document.getElementById('purchased-packages-tab-btn')?.addEventListener('click', function() {
      this.classList.add('text-blue-600', 'border-blue-600');
      this.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      document.getElementById('my-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
      document.getElementById('my-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      
      if (IS_ACADEMY_MANAGER) {
        document.getElementById('academy-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
        document.getElementById('academy-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
      }
      
      document.getElementById('purchased-packages-tab').classList.remove('hidden');
      document.getElementById('purchased-packages-tab').classList.add('active');
      
      document.getElementById('my-packages-tab').classList.add('hidden');
      document.getElementById('my-packages-tab').classList.remove('active');
      
      if (IS_ACADEMY_MANAGER) {
        document.getElementById('academy-packages-tab').classList.add('hidden');
        document.getElementById('academy-packages-tab').classList.remove('active');
      }
    });
    
    if (IS_ACADEMY_MANAGER) {
      document.getElementById('academy-packages-tab-btn')?.addEventListener('click', function() {
        this.classList.add('text-blue-600', 'border-blue-600');
        this.classList.remove('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        document.getElementById('my-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
        document.getElementById('my-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        document.getElementById('purchased-packages-tab-btn').classList.remove('text-blue-600', 'border-blue-600');
        document.getElementById('purchased-packages-tab-btn').classList.add('text-gray-500', 'border-transparent', 'hover:text-gray-700', 'hover:border-gray-300');
        
        document.getElementById('academy-packages-tab').classList.remove('hidden');
        document.getElementById('academy-packages-tab').classList.add('active');
        
        document.getElementById('my-packages-tab').classList.add('hidden');
        document.getElementById('my-packages-tab').classList.remove('active');
        
        document.getElementById('purchased-packages-tab').classList.add('hidden');
        document.getElementById('purchased-packages-tab').classList.remove('active');
      });
    }
    
    // Package form
    document.getElementById('package-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const packageData = {
        name: formData.get('name'),
        description: formData.get('description'),
        sessions: parseInt(formData.get('sessions')),
        price: parseFloat(formData.get('price')),
        validity_days: parseInt(formData.get('validity_days')),
        is_active: formData.get('is_active') ? true : false
      };
      
      // Add academy package flag if academy manager
      if (IS_ACADEMY_MANAGER) {
        packageData.is_academy_package = formData.get('is_academy_package') ? true : false;
      }
      
      try {
        showLoading(this);
        const endpoint = IS_ACADEMY_MANAGER ? '/academy/packages/create' : '/coach/packages/create';
        await fetchAPI(endpoint, {
          method: 'POST',
          body: JSON.stringify(packageData)
        });
        hideLoading(this);
        showToast('Success', 'Package created successfully.', 'success');
        this.reset();
        loadPackagesData();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to create package. Please try again.', 'error');
      }
    });
    
    // Search and filter event handlers
    document.getElementById('purchased-search')?.addEventListener('input', function() {
      filterPurchasedPackages();
    });
    
    document.getElementById('purchased-status-filter')?.addEventListener('change', function() {
      filterPurchasedPackages();
    });
    
    document.getElementById('reset-purchased-filters')?.addEventListener('click', function() {
      document.getElementById('purchased-search').value = '';
      document.getElementById('purchased-status-filter').value = '';
      displayPurchasedPackages(originalPackagesData.purchasedPackages);
    });
    
    // Academy package filters
    if (IS_ACADEMY_MANAGER) {
      document.getElementById('academy-package-coach-filter')?.addEventListener('change', function() {
        filterAcademyPackages();
      });
      
      document.getElementById('academy-package-status-filter')?.addEventListener('change', function() {
        filterAcademyPackages();
      });
      
      document.getElementById('reset-academy-package-filters')?.addEventListener('click', function() {
        document.getElementById('academy-package-coach-filter').value = '';
        document.getElementById('academy-package-status-filter').value = '';
        displayAcademyPackages(originalPackagesData.academyPackages);
      });
    }
    
    // Modal event handlers
    // Close view package modal
    document.querySelectorAll('.close-view-package-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('view-package-modal').classList.add('hidden');
      });
    });
    
    // Close delete package modal
    document.querySelectorAll('.close-delete-package-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('delete-package-modal').classList.add('hidden');
      });
    });
    
    // Delete package confirmation
    document.getElementById('confirm-delete-package-btn')?.addEventListener('click', async function() {
      const packageId = document.getElementById('delete-package-id').value;
      
      try {
        document.getElementById('delete-package-modal').classList.add('hidden');
        const endpoint = IS_ACADEMY_MANAGER ? '/academy/packages/delete' : '/coach/packages/delete';
        await fetchAPI(endpoint, {
          method: 'POST',
          body: JSON.stringify({ package_id: packageId })
        });
        showToast('Success', 'Package deleted successfully.', 'success');
        loadPackagesData();
      } catch (error) {
        showToast('Error', 'Failed to delete package. Please try again.', 'error');
      }
    });
    
    setupApprovalModalEventListeners();
  }
  
  function setupApprovalModalEventListeners(){
    // Close purchase approval modal
    document.querySelectorAll('.close-approve-purchase-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('approve-purchase-modal').classList.add('hidden');
      });
    });
    
    // // Approve purchase
    document.getElementById('approve-purchase-btn')?.addEventListener('click', async function() {
      const purchaseId = this.getAttribute('data-purchase-id');
      const isAcademy = this.getAttribute('data-is-academy') === 'true';
      
      try {
        document.getElementById('approve-purchase-modal').classList.add('hidden');
        
        const endpoint = isAcademy 
          ? '/academy/packages/purchased/approve' 
          : '/coach/packages/purchased/approve';
        
        await fetchAPI(endpoint, {
          method: 'POST',
          body: JSON.stringify({ purchase_id: purchaseId })
        });
        
        showToast('Success', 'Package purchase approved successfully.', 'success');
        loadPackagesData();
        
        // Trigger refresh of pending approvals
        if (typeof triggerApprovalCompleted === 'function') {
          triggerApprovalCompleted();
        }
      } catch (error) {
        showToast('Error', 'Failed to approve package purchase. Please try again.', 'error');
      }
    });
    
    // Reject purchase
    document.getElementById('reject-purchase-btn')?.addEventListener('click', async function() {
      const purchaseId = this.getAttribute('data-purchase-id');
      const isAcademy = this.getAttribute('data-is-academy') === 'true';
      const reasonInput = document.getElementById('package-rejection-reason');
      const reason = reasonInput ? reasonInput.value : '';
      
      try {
        document.getElementById('approve-purchase-modal').classList.add('hidden');
        
        const endpoint = isAcademy 
          ? '/academy/packages/purchased/reject' 
          : '/coach/packages/purchased/reject';
        
        const requestBody = { purchase_id: purchaseId };
        
        // Add reason if available
        if (reason) {
          requestBody.reason = reason;
        }
        
        await fetchAPI(endpoint, {
          method: 'POST',
          body: JSON.stringify(requestBody)
        });
        
        showToast('Success', 'Package purchase rejected.', 'success');
        loadPackagesData();
        
        // Trigger refresh of pending approvals
        if (typeof triggerApprovalCompleted === 'function') {
          triggerApprovalCompleted();
        }
      } catch (error) {
        showToast('Error', 'Failed to reject package purchase. Please try again.', 'error');
      }
    });
  }

  // View package details
  async function viewPackageDetails(packageId) {
    try {
      const endpoint = IS_ACADEMY_MANAGER 
        ? `/academy/packages/${packageId}` 
        : `/coach/packages/${packageId}`;
      
      const packageData = await fetchAPI(endpoint);
      
      // Populate modal
      document.getElementById('package-modal-title').textContent = 'Package Details';
      document.getElementById('package-view-name').textContent = packageData.name;
      document.getElementById('package-view-status').textContent = packageData.is_active ? 'Active' : 'Inactive';
      document.getElementById('package-view-sessions').textContent = packageData.sessions;
      document.getElementById('package-view-price').textContent = `$${formatCurrency(packageData.price)}`;
      document.getElementById('package-view-validity').textContent = `${packageData.validity_days} days`;
      document.getElementById('package-view-created').textContent = formatDate(packageData.created_at);
      document.getElementById('package-view-description').textContent = packageData.description;
      
      // Show modal
      document.getElementById('view-package-modal').classList.remove('hidden');
    } catch (error) {
      console.error('Error fetching package details:', error);
      showToast('Error', 'Failed to load package details.', 'error');
    }
  }
  
  // Show approve purchase modal
  async function showApprovePurchaseModal(purchaseId, isAcademy = false) {
    try {
      const endpoint = isAcademy 
        ? `/academy/packages/purchased/${purchaseId}` 
        : `/coach/packages/purchased/${purchaseId}`;
      
      const purchaseData = await fetchAPI(endpoint);
      
      // Populate modal
      document.getElementById('purchase-package-name').textContent = purchaseData.pricing_plan.name;
      document.getElementById('purchase-student-name').textContent = 
        `${purchaseData.student.name}`;
      
      // Set payment proof image
      if (purchaseData.payment_proof) {
        document.getElementById('payment-proof-link').href = purchaseData.payment_proof.image_url;
        document.getElementById('payment-proof-img').src = purchaseData.payment_proof.image_url;
        document.getElementById('payment-proof-container').classList.remove('hidden');
      } else {
        document.getElementById('payment-proof-container').classList.add('hidden');
      }
      
      // Add rejection reason field if it doesn't exist
      const reasonContainer = document.getElementById('rejection-reason-container');
      if (!reasonContainer) {
        const actionsContainer = document.querySelector('#approve-purchase-modal .modal-actions');
        if (actionsContainer) {
          // Insert rejection reason field before the action buttons
          const reasonHTML = `
            <div id="rejection-reason-container" class="mb-4 hidden">
              <label for="package-rejection-reason" class="block text-gray-700 font-medium mb-2">Reason for Rejection*</label>
              <textarea id="package-rejection-reason" rows="3" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" required></textarea>
              <p class="text-sm text-gray-500 mt-1">Please provide a reason for rejecting this package.</p>
            </div>
          `;
          actionsContainer.insertAdjacentHTML('beforebegin', reasonHTML);
        }
      } else {
        // Reset and hide reason field
        const reasonField = document.getElementById('package-rejection-reason');
        if (reasonField) {
          reasonField.value = '';
        }
        reasonContainer.classList.add('hidden');
      }
      
      // Set data attributes for approve/reject buttons
      document.getElementById('approve-purchase-btn').setAttribute('data-purchase-id', purchaseId);
      document.getElementById('approve-purchase-btn').setAttribute('data-is-academy', isAcademy.toString());
      
      document.getElementById('reject-purchase-btn').setAttribute('data-purchase-id', purchaseId);
      document.getElementById('reject-purchase-btn').setAttribute('data-is-academy', isAcademy.toString());
      
      // Add toggle to show rejection reason when switching to reject
      document.getElementById('reject-purchase-btn').addEventListener('mousedown', function() {
        document.getElementById('rejection-reason-container').classList.remove('hidden');
      });
      
      document.getElementById('approve-purchase-btn').addEventListener('mousedown', function() {
        document.getElementById('rejection-reason-container').classList.add('hidden');
      });
      
      // Show modal
      document.getElementById('approve-purchase-modal').classList.remove('hidden');
    } catch (error) {
      console.error('Error fetching purchase details:', error);
      showToast('Error', 'Failed to load purchase details.', 'error');
    }
  }
  
  // View payment proof
  function viewPaymentProof(purchaseId, isAcademy = false) {
    try {
      const endpoint = isAcademy 
        ? `/academy/packages/purchased/${purchaseId}/payment-proof` 
        : `/coach/packages/purchased/${purchaseId}/payment-proof`;
      
      fetchAPI(endpoint)
        .then(data => {
          if (data.image_url) {
            window.open(data.image_url, '_blank');
          } else {
            showToast('Info', 'No payment proof available for this purchase.', 'info');
          }
        })
        .catch(error => {
          console.error('Error fetching payment proof:', error);
          showToast('Error', 'Failed to load payment proof.', 'error');
        });
    } catch (error) {
      console.error('Error viewing payment proof:', error);
      showToast('Error', 'Failed to view payment proof.', 'error');
    }
  }
  
  // Filter purchased packages
  function filterPurchasedPackages() {
    const searchInput = document.getElementById('purchased-search');
    const statusFilter = document.getElementById('purchased-status-filter');
    
    if (!searchInput || !statusFilter) return;
    
    const search = searchInput.value.toLowerCase();
    const status = statusFilter.value;
    
    // If no filters, show all data
    if (!search && !status) {
      displayPurchasedPackages(originalPackagesData.purchasedPackages);
      return;
    }
    
    // Filter the data
    let filteredPackages = [...originalPackagesData.purchasedPackages];
    
    // Apply search filter
    if (search) {
      filteredPackages = filteredPackages.filter(purchase => {
        const studentName = `${purchase.student.first_name} ${purchase.student.last_name}`.toLowerCase();
        const packageName = purchase.package.name.toLowerCase();
        
        return studentName.includes(search) || packageName.includes(search);
      });
    }
    
    // Apply status filter
    if (status) {
      filteredPackages = filteredPackages.filter(purchase => purchase.status === status);
    }
    
    // Display filtered packages
    displayPurchasedPackages(filteredPackages);
  }
  
  // Filter academy packages
  function filterAcademyPackages() {
    if (!IS_ACADEMY_MANAGER) return;
    
    const coachFilter = document.getElementById('academy-package-coach-filter');
    const statusFilter = document.getElementById('academy-package-status-filter');
    
    if (!coachFilter || !statusFilter) return;
    
    const coachId = coachFilter.value;
    const status = statusFilter.value;
    
    // If no filters, show all data
    if (!coachId && !status) {
      displayAcademyPackages(originalPackagesData.academyPackages);
      return;
    }
    
    // Filter the data
    let filteredPackages = [...originalPackagesData.academyPackages];
    
    // Apply coach filter
    if (coachId) {
      filteredPackages = filteredPackages.filter(purchase => {
        return purchase.coach && purchase.coach.id.toString() === coachId;
      });
    }
    
    // Apply status filter
    if (status) {
      filteredPackages = filteredPackages.filter(purchase => purchase.status === status);
    }
    
    // Display filtered packages
    displayAcademyPackages(filteredPackages);
  }