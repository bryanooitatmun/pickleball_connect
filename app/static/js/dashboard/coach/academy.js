// Academy Management
// This file contains functions for managing academy settings, coaches, and analytics

// Initialize the academy tab
function initAcademyTab() {
    if (!IS_ACADEMY_MANAGER) return;
    
    loadAcademyData();
    setupAcademyEventListeners();
  }
  
  // Load academy data
  async function loadAcademyData() {
    try {
      // Load academy info
      const academyInfo = await fetchAPI('/academy/info');
      populateAcademyForm(academyInfo);
      
      // Load academy coaches
      const coaches = await fetchAPI('/academy/coaches');
      displayAcademyCoaches(coaches);
      
      // Load academy analytics
      const analytics = await fetchAPI('/academy/analytics');
      displayAcademyAnalytics(analytics);
    } catch (error) {
      console.error('Error loading academy data:', error);
      showToast('Error', 'Failed to load academy data.', 'error');
    }
  }
  
  // Populate academy info form
  function populateAcademyForm(academyInfo) {
    // Academy info form
    document.getElementById('academy-name').value = academyInfo.name || '';
    document.getElementById('academy-website').value = academyInfo.website || '';
    document.getElementById('academy-description').value = academyInfo.description || '';
    document.getElementById('academy-tags').value = academyInfo.tags?.join(', ') || '';
    document.getElementById('academy-url-code').value = academyInfo.private_url_code || '';
    
    // Display academy logo if exists
    if (academyInfo.logo) {
      document.getElementById('academy-logo-preview').innerHTML = `
        <img src="${academyInfo.logo}" alt="Academy Logo" class="w-full h-full object-cover rounded-lg">
      `;
      document.getElementById('remove-academy-logo').classList.remove('hidden');
    }
    
    // Academy payment form
    document.getElementById('academy-bank-name').value = academyInfo.bank_name || '';
    document.getElementById('academy-account-name').value = academyInfo.account_name || '';
    document.getElementById('academy-account-number').value = academyInfo.account_number || '';
    document.getElementById('academy-payment-reference').value = academyInfo.payment_reference || '';
    
    // Court payment details
    document.getElementById('court-bank-name').value = academyInfo.court_bank_name || '';
    document.getElementById('court-account-name').value = academyInfo.court_account_name || '';
    document.getElementById('court-account-number').value = academyInfo.court_account_number || '';
    document.getElementById('court-payment-reference').value = academyInfo.court_payment_reference || '';
  }
  
  // Display academy coaches
  function displayAcademyCoaches(coaches) {
    const container = document.getElementById('academy-coaches-container');
    
    if (!coaches || coaches.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500">
          <p>No coaches added yet</p>
        </div>
      `;
      return;
    }
    
    container.innerHTML = '';
    
    coaches.forEach(coach => {
      const coachCard = document.createElement('div');
      coachCard.className = 'bg-white border border-gray-200 rounded-lg p-4 mb-4 shadow-sm';
      
      // Format role label
      let roleLabel = '';
      let roleClass = '';
      
      switch (coach.academy_role) {
        case 'head_coach':
          roleLabel = 'Head Coach';
          roleClass = 'bg-purple-100 text-purple-800';
          break;
        case 'assistant_manager':
          roleLabel = 'Assistant Manager';
          roleClass = 'bg-blue-100 text-blue-800';
          break;
        default:
          roleLabel = 'Coach';
          roleClass = 'bg-green-100 text-green-800';
      }
      
      coachCard.innerHTML = `
        <div class="flex justify-between">
          <div class="flex items-center">
            <div class="h-12 w-12 rounded-full bg-gray-200 flex-shrink-0 overflow-hidden">
              ${coach.profile_picture 
                ? `<img src="${coach.profile_picture}" alt="${coach.first_name}" class="h-full w-full object-cover">` 
                : `<div class="h-full w-full flex items-center justify-center text-gray-500">${coach.first_name[0]}</div>`
              }
            </div>
            <div class="ml-4">
              <h3 class="font-semibold">${coach.first_name} ${coach.last_name}</h3>
              <p class="text-gray-500 text-sm">${coach.email}</p>
            </div>
          </div>
          <div class="text-right">
            <span class="px-2 py-1 rounded-full text-xs ${roleClass}">${roleLabel}</span>
          </div>
        </div>
        
        <div class="mt-4 flex items-center">
          <div class="text-sm text-gray-600 flex-1">
            <div>
              <span class="font-medium">DUPR Rating:</span> ${coach.dupr_rating || 'N/A'}
            </div>
            <div>
              <span class="font-medium">Experience:</span> ${coach.years_experience || 0} years
            </div>
          </div>
          <div class="flex space-x-2">
            <button class="text-blue-600 hover:text-blue-700 edit-coach-role-btn" data-coach-id="${coach.id}" data-coach-name="${coach.first_name} ${coach.last_name}" data-coach-email="${coach.email}" data-coach-role="${coach.academy_role}">
              <i class="fas fa-edit"></i> Edit Role
            </button>
            <button class="text-red-600 hover:text-red-700 remove-coach-btn" data-coach-id="${coach.id}" data-coach-name="${coach.first_name} ${coach.last_name}">
              <i class="fas fa-user-minus"></i> Remove
            </button>
          </div>
        </div>
      `;
      
      container.appendChild(coachCard);
    });
    
    // Add event listeners
    container.querySelectorAll('.edit-coach-role-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const coachId = this.getAttribute('data-coach-id');
        const coachName = this.getAttribute('data-coach-name');
        const coachEmail = this.getAttribute('data-coach-email');
        const coachRole = this.getAttribute('data-coach-role');
        
        document.getElementById('edit-coach-id').value = coachId;
        document.getElementById('edit-coach-name').textContent = coachName;
        document.getElementById('edit-coach-email').textContent = coachEmail;
        document.getElementById('edit-coach-role').value = coachRole;
        
        document.getElementById('edit-coach-modal').classList.remove('hidden');
      });
    });
    
    container.querySelectorAll('.remove-coach-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        const coachId = this.getAttribute('data-coach-id');
        const coachName = this.getAttribute('data-coach-name');
        
        document.getElementById('remove-coach-id').value = coachId;
        document.getElementById('remove-coach-name').textContent = coachName;
        
        document.getElementById('remove-coach-modal').classList.remove('hidden');
      });
    });
  }
  
  // Display academy analytics
  function displayAcademyAnalytics(analytics) {
    // Update summary stats
    document.getElementById('academy-total-sessions').textContent = analytics.total_sessions;
    document.getElementById('academy-total-students').textContent = analytics.total_students;
    document.getElementById('academy-total-revenue').textContent = `$${formatCurrency(analytics.total_revenue)}`;
    
    // Create sessions by coach chart
    createSessionsByCoachChart(analytics.sessions_by_coach);
    
    // Create revenue chart
    createRevenueChart(analytics.revenue_by_month);
  }
  
  // Create sessions by coach chart
  function createSessionsByCoachChart(data) {
    const ctx = document.getElementById('academy-sessions-by-coach-chart')?.getContext('2d');
    if (!ctx) return;
    
    const labels = [];
    const values = [];
    const backgroundColor = [
      'rgba(54, 162, 235, 0.8)',
      'rgba(75, 192, 192, 0.8)',
      'rgba(153, 102, 255, 0.8)',
      'rgba(255, 159, 64, 0.8)',
      'rgba(255, 99, 132, 0.8)',
      'rgba(255, 205, 86, 0.8)'
    ];
    
    // Sort coaches by session count in descending order
    const sortedCoaches = Object.entries(data)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6); // Limit to top 6 coaches
    
    sortedCoaches.forEach(([coach, count]) => {
      labels.push(coach);
      values.push(count);
    });
    
    new Chart(ctx, {
      type: 'pie',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: backgroundColor
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              boxWidth: 12,
              padding: 10
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.raw;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = Math.round((value / total) * 100);
                return `${label}: ${value} sessions (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }
  
  // Create revenue chart
  function createRevenueChart(data) {
    const ctx = document.getElementById('academy-revenue-chart')?.getContext('2d');
    if (!ctx) return;
    
    const labels = [];
    const values = [];
    
    // Sort months chronologically
    const sortedMonths = Object.keys(data).sort((a, b) => {
      const dateA = new Date(a);
      const dateB = new Date(b);
      return dateA - dateB;
    });
    
    // Get the last 12 months
    const recentMonths = sortedMonths.slice(-12);
    
    recentMonths.forEach(month => {
      // Format date as MMM YYYY
      const date = new Date(month);
      const formattedMonth = date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      
      labels.push(formattedMonth);
      values.push(data[month]);
    });
    
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: values,
          backgroundColor: 'rgba(75, 192, 192, 0.8)',
          borderWidth: 0,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '$' + value;
              }
            }
          }
        },
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return 'Revenue: $' + formatCurrency(context.raw);
              }
            }
          }
        }
      }
    });
  }
  
  // Setup academy event listeners
  function setupAcademyEventListeners() {
    // Academy info form
    document.getElementById('academy-info-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const academyData = {
        name: formData.get('name'),
        website: formData.get('website'),
        description: formData.get('description'),
        tags: formData.get('tags').split(',').map(tag => tag.trim()).filter(tag => tag),
        private_url_code: formData.get('private_url_code')
      };
      
      try {
        showLoading(this);
        await fetchAPI('/academy/info', {
          method: 'PUT',
          body: JSON.stringify(academyData)
        });
        hideLoading(this);
        showToast('Success', 'Academy information updated successfully.', 'success');
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to update academy information. Please try again.', 'error');
      }
    });
    
    // Academy payment form
    document.getElementById('academy-payment-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const paymentData = {
        bank_name: formData.get('bank_name'),
        account_name: formData.get('account_name'),
        account_number: formData.get('account_number'),
        payment_reference: formData.get('payment_reference'),
        court_bank_name: formData.get('court_bank_name'),
        court_account_name: formData.get('court_account_name'),
        court_account_number: formData.get('court_account_number'),
        court_payment_reference: formData.get('court_payment_reference')
      };
      
      try {
        showLoading(this);
        await fetchAPI('/academy/payment-details', {
          method: 'PUT',
          body: JSON.stringify(paymentData)
        });
        hideLoading(this);
        showToast('Success', 'Payment details updated successfully.', 'success');
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to update payment details. Please try again.', 'error');
      }
    });
    
    // Academy logo upload
    document.getElementById('upload-academy-logo')?.addEventListener('click', function() {
      document.getElementById('academy-logo-input').click();
    });
    
    document.getElementById('academy-logo-input')?.addEventListener('change', async function() {
      if (this.files && this.files[0]) {
        const file = this.files[0];
        const reader = new FileReader();
        
        reader.onload = async function(e) {
          // Preview the logo
          document.getElementById('academy-logo-preview').innerHTML = `
            <img src="${e.target.result}" alt="Academy Logo" class="w-full h-full object-cover rounded-lg">
          `;
          
          // Show remove button
          document.getElementById('remove-academy-logo').classList.remove('hidden');
          
          // Upload the logo
          try {
            const formData = new FormData();
            formData.append('logo', file);
            
            await fetch('/academy/upload-logo', {
              method: 'POST',
              body: formData
            });
            
            showToast('Success', 'Academy logo uploaded successfully.', 'success');
          } catch (error) {
            console.error('Error uploading logo:', error);
            showToast('Error', 'Failed to upload academy logo. Please try again.', 'error');
          }
        };
        
        reader.readAsDataURL(this.files[0]);
      }
    });
    
    // Remove academy logo
    document.getElementById('remove-academy-logo')?.addEventListener('click', async function() {
      try {
        await fetchAPI('/academy/remove-logo', {
          method: 'POST'
        });
        
        // Reset logo preview
        document.getElementById('academy-logo-preview').innerHTML = `
          <i class="fas fa-image text-gray-400 text-xl"></i>
        `;
        
        // Hide remove button
        this.classList.add('hidden');
        
        showToast('Success', 'Academy logo removed successfully.', 'success');
      } catch (error) {
        console.error('Error removing logo:', error);
        showToast('Error', 'Failed to remove academy logo. Please try again.', 'error');
      }
    });
    
    // Add coach button
    document.getElementById('add-coach-btn')?.addEventListener('click', function() {
      document.getElementById('add-coach-modal').classList.remove('hidden');
    });
    
    // Close modals
    document.querySelectorAll('.close-add-coach-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('add-coach-modal').classList.add('hidden');
      });
    });
    
    document.querySelectorAll('.close-edit-coach-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('edit-coach-modal').classList.add('hidden');
      });
    });
    
    document.querySelectorAll('.close-remove-coach-modal')?.forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('remove-coach-modal').classList.add('hidden');
      });
    });
    
    // Add coach form
    document.getElementById('add-coach-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const coachData = {
        email: formData.get('email'),
        role: formData.get('role')
      };
      
      try {
        showLoading(this);
        await fetchAPI('/academy/coaches/add', {
          method: 'POST',
          body: JSON.stringify(coachData)
        });
        hideLoading(this);
        document.getElementById('add-coach-modal').classList.add('hidden');
        this.reset();
        
        showToast('Success', 'Coach added successfully.', 'success');
        loadAcademyData();
      } catch (error) {
        hideLoading(this);
        let errorMessage = 'Failed to add coach.';
        
        if (error.message) {
          if (error.message.includes('already exists')) {
            errorMessage = 'This coach is already part of your academy.';
          } else if (error.message.includes('not found')) {
            errorMessage = 'No user with this email was found.';
          }
        }
        
        showToast('Error', errorMessage, 'error');
      }
    });
    
    // Edit coach form
    document.getElementById('edit-coach-form')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const updateData = {
        coach_id: formData.get('coach_id'),
        role: formData.get('role')
      };
      
      try {
        showLoading(this);
        await fetchAPI('/academy/coaches/update-role', {
          method: 'POST',
          body: JSON.stringify(updateData)
        });
        hideLoading(this);
        document.getElementById('edit-coach-modal').classList.add('hidden');
        
        showToast('Success', 'Coach role updated successfully.', 'success');
        loadAcademyData();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to update coach role. Please try again.', 'error');
      }
    });
    
    // Remove coach confirmation
    document.getElementById('confirm-remove-coach-btn')?.addEventListener('click', async function() {
      const coachId = document.getElementById('remove-coach-id').value;
      
      try {
        document.getElementById('remove-coach-modal').classList.add('hidden');
        await fetchAPI('/academy/coaches/remove', {
          method: 'POST',
          body: JSON.stringify({ coach_id: coachId })
        });
        
        showToast('Success', 'Coach removed from academy successfully.', 'success');
        loadAcademyData();
      } catch (error) {
        showToast('Error', 'Failed to remove coach. Please try again.', 'error');
      }
    });
  }