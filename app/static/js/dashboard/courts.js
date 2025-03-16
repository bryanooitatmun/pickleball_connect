/**
 * Courts tab-specific JavaScript
 */

// Function called when the courts tab is activated
function initCourtsTab() {
    // Load courts data if not already loaded
    const courtsList = document.getElementById('my-courts-list');
    if (courtsList && !courtsList.dataset.loaded) {
      loadCourts();
      setupCourtEventListeners();
      loadDefaultBookingResponsibility();
      courtsList.dataset.loaded = 'true';
    }
  }
  
  // Load courts data
  async function loadCourts() {
    try {
      // Get all courts
      const courts = await getCourts();
      
      // Get coach courts
      const coachCourts = await getCoachCourts();
      
      // Populate court select in court modal
      const courtSelect = document.getElementById('court-select');
      if (courtSelect) {
        courtSelect.innerHTML = '<option value="">Select a court</option>';
        
        // Filter out courts the coach is already associated with
        const availableCourts = courts.filter(court => 
          !coachCourts.some(coachCourt => coachCourt.id === court.id)
        );
        
        availableCourts.forEach(court => {
          const option = document.createElement('option');
          option.value = court.id;
          option.textContent = `${court.name} - ${court.address}, ${court.city}`;
          courtSelect.appendChild(option);
        });
      }
      
      // Populate coach courts list
      const courtsContainer = document.getElementById('my-courts-list');
      const noCourtMessage = document.getElementById('no-courts-message');
      
      if (!courtsContainer) return;
      
      if (coachCourts.length === 0) {
        if (noCourtMessage) {
          noCourtMessage.style.display = 'block';
        } else {
          courtsContainer.innerHTML = `
            <div class="text-center py-6 text-gray-500" id="no-courts-message">
              <p>No courts added yet</p>
            </div>
          `;
        }
        return;
      }
      
      // Hide no courts message if it exists
      if (noCourtMessage) {
        noCourtMessage.style.display = 'none';
      }
      
      courtsContainer.innerHTML = '';
      
      coachCourts.forEach(court => {
        const courtCard = document.createElement('div');
        courtCard.className = 'bg-gray-50 rounded-lg p-4 flex justify-between items-center';
        courtCard.innerHTML = `
          <div>
            <h4 class="font-medium">${court.name}</h4>
            <p class="text-gray-500 text-sm">${court.address}, ${court.city}, ${court.state} ${court.zip_code}</p>
          </div>
          <div class="flex space-x-2">
            <button class="text-blue-600 hover:text-blue-800 edit-court-instructions-btn" data-court-id="${court.id}" title="Edit Booking Instructions">
              <i class="fas fa-info-circle"></i>
            </button>
            <button class="text-red-600 hover:text-red-700 remove-court-btn" data-court-id="${court.id}" title="Remove Court">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        `;
        courtsContainer.appendChild(courtCard);
      });
      
      // Add event listeners to buttons
      document.querySelectorAll('.remove-court-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const courtId = this.getAttribute('data-court-id');
          document.getElementById('remove-court-id').value = courtId;
          document.getElementById('remove-court-modal').classList.remove('hidden');
        });
      });
      
      document.querySelectorAll('.edit-court-instructions-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const courtId = this.getAttribute('data-court-id');
          openCourtInstructionsModal(courtId);
        });
      });
      
      // Also load court booking instructions
      loadCourtInstructions(coachCourts);
      
    } catch (error) {
      console.error('Error loading courts:', error);
      showToast('Error', 'Failed to load courts data', 'error');
    }
  }
  
  // Load court booking instructions
  async function loadCourtInstructions(courts) {
    try {
      const instructionsContainer = document.getElementById('court-instructions-container');
      const noInstructionsMessage = document.getElementById('no-court-instructions-message');
      
      if (!instructionsContainer) return;
      
      // Filter courts that have booking instructions
      const courtsWithInstructions = courts.filter(court => 
        court.booking_instructions || court.booking_link
      );
      
      if (courtsWithInstructions.length === 0) {
        if (noInstructionsMessage) {
          noInstructionsMessage.style.display = 'block';
        } else {
          instructionsContainer.innerHTML = `
            <div class="text-center py-6 text-gray-500" id="no-court-instructions-message">
              <p>No courts with booking instructions yet</p>
            </div>
          `;
        }
        return;
      }
      
      // Hide no instructions message if it exists
      if (noInstructionsMessage) {
        noInstructionsMessage.style.display = 'none';
      }
      
      instructionsContainer.innerHTML = '';
      
      courtsWithInstructions.forEach(court => {
        const instructionCard = document.createElement('div');
        instructionCard.className = 'bg-gray-50 rounded-lg p-4 mb-4';
        
        // Create booking link element if exists
        let bookingLinkHtml = '';
        if (court.booking_link) {
          bookingLinkHtml = `
            <div class="mt-2">
              <a href="${court.booking_link}" target="_blank" class="text-blue-600 hover:text-blue-800 flex items-center">
                <i class="fas fa-external-link-alt mr-1"></i> Booking Link
              </a>
            </div>
          `;
        }
        
        instructionCard.innerHTML = `
          <div class="flex justify-between items-start">
            <h4 class="font-medium">${court.name}</h4>
            <button class="text-blue-600 hover:text-blue-800 edit-court-instructions-btn" data-court-id="${court.id}">
              <i class="fas fa-edit"></i>
            </button>
          </div>
          <div class="mt-2 text-gray-700">
            ${court.booking_instructions ? `<p>${court.booking_instructions}</p>` : '<p class="text-gray-500 italic">No specific instructions provided</p>'}
          </div>
          ${bookingLinkHtml}
        `;
        
        instructionsContainer.appendChild(instructionCard);
      });
      
      // Re-add event listeners to edit buttons
      document.querySelectorAll('.edit-court-instructions-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const courtId = this.getAttribute('data-court-id');
          openCourtInstructionsModal(courtId);
        });
      });
      
    } catch (error) {
      console.error('Error loading court instructions:', error);
    }
  }
  
  // Load default booking responsibility setting
  async function loadDefaultBookingResponsibility() {
    try {
      const response = await fetchAPI('/coach/default-booking-responsibility');
      
      const responsibility = response.default_responsibility || 'coach';
      
      // Set the radio button
      const radioBtn = document.getElementById(`${responsibility}-responsible`);
      if (radioBtn) {
        radioBtn.checked = true;
      }
      
    } catch (error) {
      console.error('Error loading default booking responsibility:', error);
    }
  }
  
  // Open court instructions modal with data
  async function openCourtInstructionsModal(courtId) {
    try {
      const court = await fetchAPI(`/courts/${courtId}`);
      
      // Set modal title
      const modalTitle = document.getElementById('court-instructions-modal-title');
      if (modalTitle) {
        modalTitle.textContent = `Booking Instructions for ${court.name}`;
      }
      
      // Set court ID in form
      const courtIdInput = document.getElementById('instructions-court-id');
      if (courtIdInput) {
        courtIdInput.value = courtId;
      }
      
      // Set existing data
      const instructionsTextarea = document.getElementById('booking-instructions');
      const bookingLinkInput = document.getElementById('booking-link');
      
      if (instructionsTextarea) {
        instructionsTextarea.value = court.booking_instructions || '';
      }
      
      if (bookingLinkInput) {
        bookingLinkInput.value = court.booking_link || '';
      }
      
      // Show modal
      document.getElementById('court-instructions-modal').classList.remove('hidden');
      
    } catch (error) {
      console.error('Error getting court details:', error);
      showToast('Error', 'Failed to load court details', 'error');
    }
  }
  
  // Setup event listeners for court-related actions
  function setupCourtEventListeners() {
    // Add court button
    const addCourtBtn = document.getElementById('add-court-btn');
    if (addCourtBtn) {
      addCourtBtn.addEventListener('click', function() {
        // Reset form
        const courtForm = document.getElementById('court-form');
        if (courtForm) courtForm.reset();
        
        // Set modal title
        const modalTitle = document.getElementById('court-modal-title');
        if (modalTitle) modalTitle.textContent = 'Add Court';
        
        // Show modal
        document.getElementById('court-modal').classList.remove('hidden');
      });
    }
    
    // Court form submission
    const courtForm = document.getElementById('court-form');
    if (courtForm) {
      courtForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const courtId = document.getElementById('court-select').value;
        
        if (!courtId) {
          showToast('Error', 'Please select a court', 'error');
          return;
        }
        
        try {
          showLoading(this);
          await addCoachCourt({court_id: courtId});
          hideLoading(this);
          
          // Close modal
          document.querySelector('.close-court-modal').click();
          
          showToast('Success', 'Court added successfully', 'success');
          
          // Reload courts data
          loadCourts();
        } catch (error) {
          hideLoading(this);
          showToast('Error', 'Failed to add court: ' + error.message, 'error');
        }
      });
    }
    
    // Court instructions form submission
    const courtInstructionsForm = document.getElementById('court-instructions-form');
    if (courtInstructionsForm) {
      courtInstructionsForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const instructionsData = {
          court_id: formData.get('court_id'),
          booking_instructions: formData.get('booking_instructions'),
          booking_link: formData.get('booking_link')
        };
        
        try {
          showLoading(this);
          await updateCourtBookingInstructions(
            instructionsData.court_id,
            instructionsData
          );
          hideLoading(this);
          
          // Close modal
          document.querySelector('.close-court-instructions-modal').click();
          
          showToast('Success', 'Booking instructions updated successfully', 'success');
          
          // Reload courts data to refresh instructions
          loadCourts();
        } catch (error) {
          hideLoading(this);
          showToast('Error', 'Failed to update booking instructions: ' + error.message, 'error');
        }
      });
    }
    
    // Confirm remove court button
    const confirmRemoveCourtBtn = document.getElementById('confirm-remove-court-btn');
    if (confirmRemoveCourtBtn) {
      confirmRemoveCourtBtn.addEventListener('click', async function() {
        const courtId = document.getElementById('remove-court-id').value;
        
        try {
          // Close modal first
          document.getElementById('remove-court-modal').classList.add('hidden');
          
          await removeCoachCourt(courtId);
          
          showToast('Success', 'Court removed successfully', 'success');
          
          // Reload courts data
          loadCourts();
        } catch (error) {
          showToast('Error', 'Failed to remove court: ' + error.message, 'error');
        }
      });
    }
    
    // Default booking responsibility form
    const bookingResponsibilityForm = document.getElementById('booking-responsibility-form');
    if (bookingResponsibilityForm) {
      bookingResponsibilityForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const responsibility = formData.get('default_booking_responsibility');
        
        try {
          showLoading(this);
          await fetchAPI('/coach/update-default-booking-responsibility', {
            method: 'POST',
            body: JSON.stringify({ default_responsibility: responsibility })
          });
          hideLoading(this);
          
          showToast('Success', 'Default booking responsibility updated', 'success');
        } catch (error) {
          hideLoading(this);
          showToast('Error', 'Failed to update booking responsibility: ' + error.message, 'error');
        }
      });
    }
    
    // Modal close buttons
    document.querySelectorAll('.close-court-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('court-modal').classList.add('hidden');
      });
    });
    
    document.querySelectorAll('.close-remove-court-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('remove-court-modal').classList.add('hidden');
      });
    });
    
    document.querySelectorAll('.close-court-instructions-modal').forEach(btn => {
      btn.addEventListener('click', function() {
        document.getElementById('court-instructions-modal').classList.add('hidden');
      });
    });
  }