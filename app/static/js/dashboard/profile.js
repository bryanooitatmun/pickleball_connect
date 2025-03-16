/**
 * Profile tab-specific JavaScript
 */

// Track showcase images changes
let showcaseImagesChanged = false;
let deletedImageIds = [];
let newImages = [];
let selectedTags = [];

// Function called when the profile tab is activated
function initProfileTab() {
  // Load coach profile data if not already loaded
  const profileForm = document.getElementById('profile-form');
  if (profileForm && !profileForm.dataset.loaded) {
    loadProfileData();
    setupProfileEventListeners();
    profileForm.dataset.loaded = 'true';
  }
}

// Load profile data
async function loadProfileData() {
  try {
    const profileData = await getCoachProfile();
    const user = profileData.user;
    const coach = profileData;
    
    // Populate personal information
    populatePersonalInfo(user);
    
    // Populate coach information if applicable
    if (IS_COACH) {
      populateCoachInfo(coach);
    }
    
    // Populate payment details
    populatePaymentDetails(profileData.payment_details || {});
    
    // Load showcase images
    loadShowcaseImages();
    
    // Load coach tags
    if (IS_COACH) {
      loadTags();
    }
  } catch (error) {
    console.error('Error loading profile data:', error);
    showToast('Error', 'Failed to load profile data', 'error');
  }
}

// Populate personal information fields
function populatePersonalInfo(user) {
  document.getElementById('first_name').value = user.first_name || '';
  document.getElementById('last_name').value = user.last_name || '';
  document.getElementById('email').value = user.email || '';
  document.getElementById('gender').value = user.gender || '';
  document.getElementById('location').value = user.location || '';
  document.getElementById('dupr_rating').value = user.dupr_rating || '';
}

// Populate coach information fields
function populateCoachInfo(coach) {
  document.getElementById('hourly_rate').value = coach.hourly_rate || '';
  document.getElementById('years_experience').value = coach.years_experience || '';
  document.getElementById('specialties').value = coach.specialties || '';
  document.getElementById('biography').value = coach.biography || '';
  
  // Set selected tags
  if (coach.tags) {
    selectedTags = [...coach.tags];
    updateSelectedTags();
  }
}

// Populate payment details fields
function populatePaymentDetails(paymentDetails) {
  document.getElementById('bank_name').value = paymentDetails.bank_name || '';
  document.getElementById('account_name').value = paymentDetails.account_name || '';
  document.getElementById('account_number').value = paymentDetails.account_number || '';
  document.getElementById('payment_reference').value = paymentDetails.payment_reference || '';
  document.getElementById('court_payment_details').value = paymentDetails.court_payment_details || '';
}

// Setup event listeners for profile-related actions
function setupProfileEventListeners() {
  // Profile picture management
  setupProfilePicture();
  
  // Showcase images management
  setupShowcaseImages();
  
  // Form submissions
  setupFormSubmissions();
  
  // Tag management
  setupTagManagement();
}

// Profile picture management
function setupProfilePicture() {
  const profilePictureInput = document.getElementById('profile-picture-input');
  const changeProfilePictureBtn = document.getElementById('change-profile-picture');
  const removeProfilePictureBtn = document.getElementById('remove-profile-picture');
  
  // Change profile picture
  if (changeProfilePictureBtn && profilePictureInput) {
    changeProfilePictureBtn.addEventListener('click', function() {
      profilePictureInput.click();
    });
  }
  
  // Handle profile picture selection
  if (profilePictureInput) {
    profilePictureInput.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        const reader = new FileReader();
        const profilePreviewImage = document.getElementById('profile-preview-image');
        
        reader.onload = function(e) {
          if (profilePreviewImage.tagName === 'IMG') {
            profilePreviewImage.src = e.target.result;
          } else {
            // Replace the placeholder div with an actual image
            const parent = profilePreviewImage.parentElement;
            const img = document.createElement('img');
            img.id = 'profile-preview-image';
            img.src = e.target.result;
            img.alt = 'Profile Picture';
            img.className = 'h-full w-full object-cover';
            parent.replaceChild(img, profilePreviewImage);
          }
          
          // Show the remove button
          if (removeProfilePictureBtn) {
            removeProfilePictureBtn.style.display = 'block';
          }
          
          // Upload the image
          uploadProfilePicture(profilePictureInput.files[0]);
        };
        
        reader.readAsDataURL(this.files[0]);
      }
    });
  }
  
  // Remove profile picture
  if (removeProfilePictureBtn) {
    removeProfilePictureBtn.addEventListener('click', function() {
      // Ask for confirmation
      if (confirm('Are you sure you want to remove your profile picture?')) {
        const profilePreviewImage = document.getElementById('profile-preview-image');
        
        if (!profilePreviewImage) return;
        
        // Replace the image with placeholder
        const parent = profilePreviewImage.parentElement;
        const placeholder = document.createElement('div');
        placeholder.id = 'profile-preview-image';
        placeholder.className = 'bg-gray-200 h-full w-full flex items-center justify-center';
        placeholder.innerHTML = '<i class="fas fa-user text-gray-400 text-4xl"></i>';
        
        // If the current element is an image, replace it
        if (profilePreviewImage.tagName === 'IMG') {
          parent.replaceChild(placeholder, profilePreviewImage);
        }
        
        // Hide the remove button
        removeProfilePictureBtn.style.display = 'none';
        
        // Send request to server to remove profile picture
        removeProfilePicture();
      }
    });
  }
}

// Showcase images management
function setupShowcaseImages() {
  const showcaseImagesInput = document.getElementById('showcase-images-input');
  const addShowcaseImagesBtn = document.getElementById('add-showcase-images');
  const saveShowcaseChangesBtn = document.getElementById('save-showcase-changes');
  
  // Add showcase images button
  if (addShowcaseImagesBtn && showcaseImagesInput) {
    addShowcaseImagesBtn.addEventListener('click', function() {
      showcaseImagesInput.click();
    });
  }
  
  // Handle showcase images selection
  if (showcaseImagesInput) {
    showcaseImagesInput.addEventListener('change', function() {
      if (this.files && this.files.length > 0) {
        // Store the selected files
        newImages = Array.from(this.files);
        
        // Preview the new images
        newImages.forEach(file => {
          const reader = new FileReader();
          reader.onload = function(e) {
            addShowcaseImagePreview(e.target.result, null, true);
          };
          reader.readAsDataURL(file);
        });
        
        // Show the save button
        if (saveShowcaseChangesBtn) {
          saveShowcaseChangesBtn.classList.remove('hidden');
        }
        showcaseImagesChanged = true;
      }
    });
  }
  
  // Save showcase changes button
  if (saveShowcaseChangesBtn) {
    saveShowcaseChangesBtn.addEventListener('click', function() {
      if (showcaseImagesChanged) {
        saveShowcaseChanges();
      }
    });
  }
}

// Form submissions
function setupFormSubmissions() {
  // Profile form
  const profileForm = document.getElementById('profile-form');
  if (profileForm) {
    profileForm.addEventListener('submit', async function(e) {
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
        }
      };
      
      // Add coach data if applicable
      if (IS_COACH) {
        profileData.coach = {
          hourly_rate: parseFloat(formData.get('hourly_rate')),
          years_experience: parseInt(formData.get('years_experience')),
          specialties: formData.get('specialties'),
          biography: formData.get('biography'),
          tags: selectedTags.map(tag => tag.id)
        };
      }
      
      try {
        const saveBtn = document.getElementById('save-profile-btn');
        if (saveBtn) showLoading(saveBtn);
        
        await updateCoachProfile(profileData);
        
        if (saveBtn) hideLoading(saveBtn);
        showToast('Success', 'Your profile has been updated successfully', 'success');
      } catch (error) {
        if (document.getElementById('save-profile-btn')) {
          hideLoading(document.getElementById('save-profile-btn'));
        }
        showToast('Error', 'Failed to update profile: ' + error.message, 'error');
      }
    });
  }
  
  // Payment details form
  const paymentDetailsForm = document.getElementById('payment-details-form');
  if (paymentDetailsForm) {
    paymentDetailsForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const paymentData = {
        bank_name: formData.get('bank_name'),
        account_name: formData.get('account_name'),
        account_number: formData.get('account_number'),
        payment_reference: formData.get('payment_reference'),
        court_payment_details: formData.get('court_payment_details')
      };
      
      try {
        const saveBtn = document.getElementById('save-payment-details-btn');
        if (saveBtn) showLoading(saveBtn);
        
        await fetchAPI('/coach/update-payment-details', {
          method: 'POST',
          body: JSON.stringify(paymentData)
        });
        
        if (saveBtn) hideLoading(saveBtn);
        showToast('Success', 'Your payment details have been updated successfully', 'success');
      } catch (error) {
        if (document.getElementById('save-payment-details-btn')) {
          hideLoading(document.getElementById('save-payment-details-btn'));
        }
        showToast('Error', 'Failed to update payment details: ' + error.message, 'error');
      }
    });
  }
  
  // Password form
  const passwordForm = document.getElementById('password-form');
  if (passwordForm) {
    passwordForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const formData = new FormData(this);
      const currentPassword = formData.get('current_password');
      const newPassword = formData.get('new_password');
      const confirmPassword = formData.get('confirm_password');
      
      if (newPassword !== confirmPassword) {
        showToast('Error', 'New passwords do not match', 'error');
        return;
      }
      
      try {
        showLoading(this);
        await changePassword({
          current_password: currentPassword,
          new_password: newPassword
        });
        hideLoading(this);
        showToast('Success', 'Your password has been changed successfully', 'success');
        this.reset();
      } catch (error) {
        hideLoading(this);
        showToast('Error', 'Failed to change password: ' + error.message, 'error');
      }
    });
  }
}

// Tag management
function setupTagManagement() {
  const tagsSelect = document.getElementById('coach-tags');
  
  if (!tagsSelect) return;
  
  // Add tag when selected
  tagsSelect.addEventListener('change', function() {
    const tagId = this.value;
    
    if (!tagId) return;
    
    const tagText = this.options[this.selectedIndex].text;
    
    // Check if tag is already selected
    if (selectedTags.some(t => t.id.toString() === tagId)) {
      this.value = '';
      return;
    }
    
    // Add tag to selected tags
    selectedTags.push({
      id: tagId,
      name: tagText
    });
    
    // Update UI
    updateSelectedTags();
    
    // Reset select
    this.value = '';
  });
}

// Update selected tags display
function updateSelectedTags() {
  const container = document.getElementById('selected-tags-container');
  
  if (!container) return;
  
  if (selectedTags.length === 0) {
    container.innerHTML = '<div class="text-sm text-gray-500">No tags selected</div>';
    return;
  }
  
  container.innerHTML = '';
  
  selectedTags.forEach(tag => {
    const tagItem = document.createElement('div');
    tagItem.className = 'tag-item';
    tagItem.innerHTML = `
      ${tag.name}
      <span class="tag-remove-btn" data-tag-id="${tag.id}">×</span>
    `;
    
    container.appendChild(tagItem);
  });
  
  // Add event listeners to remove buttons
  container.querySelectorAll('.tag-remove-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const tagId = this.getAttribute('data-tag-id');
      
      // Remove tag from selected tags
      selectedTags = selectedTags.filter(t => t.id.toString() !== tagId);
      
      // Update UI
      updateSelectedTags();
    });
  });
}

// Load all available tags
async function loadTags() {
  try {
    const tags = await fetchAPI('/tags');
    
    const tagsSelect = document.getElementById('coach-tags');
    
    if (!tagsSelect) return;
    
    // Clear existing options (except the default one)
    tagsSelect.querySelectorAll('option:not(:first-child)').forEach(option => {
      option.remove();
    });
    
    // Add tags to select
    tags.forEach(tag => {
      const option = document.createElement('option');
      option.value = tag.id;
      option.textContent = tag.name;
      tagsSelect.appendChild(option);
    });
  } catch (error) {
    console.error('Error loading tags:', error);
  }
}

// Upload profile picture to server
async function uploadProfilePicture(file) {
  try {
    const formData = new FormData();
    formData.append('profile_picture', file);
    
    // Show loading indicator
    const changeProfilePictureBtn = document.getElementById('change-profile-picture');
    if (changeProfilePictureBtn) {
      changeProfilePictureBtn.innerHTML = '<i class="fas fa-spinner fa-spin text-white text-xl"></i>';
    }
    
    const response = await fetch(`${API_BASE_URL}/coach/update-profile-picture`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload profile picture');
    }
    
    // Reset loading indicator
    if (changeProfilePictureBtn) {
      changeProfilePictureBtn.innerHTML = '<i class="fas fa-camera text-white text-xl"></i>';
    }
    
    // Show success message
    showToast('Success', 'Profile picture updated successfully', 'success');
    
    // Update header profile picture
    const headerProfileImg = document.querySelector('#profile-initial img');
    if (headerProfileImg) {
      headerProfileImg.src = URL.createObjectURL(file);
    }
  } catch (error) {
    console.error('Error uploading profile picture:', error);
    
    const changeProfilePictureBtn = document.getElementById('change-profile-picture');
    if (changeProfilePictureBtn) {
      changeProfilePictureBtn.innerHTML = '<i class="fas fa-camera text-white text-xl"></i>';
    }
    
    showToast('Error', 'Failed to update profile picture: ' + error.message, 'error');
  }
}

// Remove profile picture from server
async function removeProfilePicture() {
  try {
    const response = await fetch(`${API_BASE_URL}/coach/remove-profile-picture`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to remove profile picture');
    }
    
    showToast('Success', 'Profile picture removed successfully', 'success');
    
    // Update header profile picture
    const headerProfileImg = document.querySelector('#profile-initial img');
    const profileInitial = document.getElementById('profile-initial');
    if (headerProfileImg && profileInitial) {
      headerProfileImg.remove();
      profileInitial.textContent = document.getElementById('first_name').value.charAt(0) || '';
    }
  } catch (error) {
    console.error('Error removing profile picture:', error);
    showToast('Error', 'Failed to remove profile picture: ' + error.message, 'error');
  }
}

// Load showcase images from server
async function loadShowcaseImages() {
  try {
    const response = await fetch(`${API_BASE_URL}/coach/showcase-images`);
    
    if (!response.ok) {
      throw new Error('Failed to load showcase images');
    }
    
    const data = await response.json();
    const showcaseImagesContainer = document.getElementById('showcase-images-container');
    
    if (!showcaseImagesContainer) return;
    
    // Clear loading indicator
    showcaseImagesContainer.innerHTML = '';
    
    // Add images to the container
    if (data.images && data.images.length > 0) {
      data.images.forEach(image => {
        addShowcaseImagePreview(image.url, image.id);
      });
    }
    
    // Add the "Add Image" placeholder
    addAddImagePlaceholder();
    
  } catch (error) {
    console.error('Error loading showcase images:', error);
    
    const showcaseImagesContainer = document.getElementById('showcase-images-container');
    if (showcaseImagesContainer) {
      showcaseImagesContainer.innerHTML = `
        <div class="col-span-full p-4 text-center">
          <p class="text-red-500">Failed to load images. Please try again.</p>
          <button type="button" class="mt-2 text-blue-600 hover:text-blue-800" onclick="loadShowcaseImages()">
            <i class="fas fa-sync-alt mr-1"></i> Retry
          </button>
        </div>
      `;
    }
  }
}

// Add a showcase image preview to the container
function addShowcaseImagePreview(imageUrl, imageId, isNew = false) {
  const showcaseImagesContainer = document.getElementById('showcase-images-container');
  if (!showcaseImagesContainer) return;
  
  const imageItem = document.createElement('div');
  imageItem.className = 'showcase-image-item';
  if (imageId) imageItem.dataset.id = imageId;
  if (isNew) imageItem.dataset.new = 'true';
  
  imageItem.innerHTML = `
    <img src="${imageUrl}" alt="Showcase Image">
    <div class="remove-image">
      <i class="fas fa-times text-red-500"></i>
    </div>
  `;
  
  // Add remove button click handler
  const removeBtn = imageItem.querySelector('.remove-image');
  removeBtn.addEventListener('click', function() {
    if (isNew) {
      // Just remove from display
      imageItem.remove();
      
      // Update new images array if needed
      const imgIndex = Array.from(showcaseImagesContainer.querySelectorAll('[data-new="true"]')).indexOf(imageItem);
      if (imgIndex > -1 && imgIndex < newImages.length) {
        newImages.splice(imgIndex, 1);
      }
    } else {
      // Mark as deleted and add to deleted IDs
      imageItem.dataset.deleted = 'true';
      deletedImageIds.push(imageId);
    }
    
    // Show save button
    const saveShowcaseChangesBtn = document.getElementById('save-showcase-changes');
    if (saveShowcaseChangesBtn) {
      saveShowcaseChangesBtn.classList.remove('hidden');
    }
    showcaseImagesChanged = true;
  });
  
  // Add to container before the "Add Image" placeholder
  const addPlaceholder = showcaseImagesContainer.querySelector('.add-image-placeholder');
  if (addPlaceholder) {
    showcaseImagesContainer.insertBefore(imageItem, addPlaceholder);
  } else {
    showcaseImagesContainer.appendChild(imageItem);
  }
}

// Add the "Add Image" placeholder
function addAddImagePlaceholder() {
  const showcaseImagesContainer = document.getElementById('showcase-images-container');
  if (!showcaseImagesContainer) return;
  
  const placeholder = document.createElement('div');
  placeholder.className = 'add-image-placeholder';
  placeholder.innerHTML = `
    <i class="fas fa-plus text-gray-400 text-2xl mb-1"></i>
    <span class="text-xs text-gray-500">Add Photo</span>
  `;
  
  placeholder.addEventListener('click', function() {
    const addShowcaseImagesBtn = document.getElementById('add-showcase-images');
    if (addShowcaseImagesBtn) {
      addShowcaseImagesBtn.click();
    }
  });
  
  showcaseImagesContainer.appendChild(placeholder);
}

// Save showcase image changes
async function saveShowcaseChanges() {
  try {
    // Show loading state
    const saveShowcaseChangesBtn = document.getElementById('save-showcase-changes');
    if (saveShowcaseChangesBtn) {
      saveShowcaseChangesBtn.disabled = true;
      saveShowcaseChangesBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
    }
    
    const formData = new FormData();
    
    // Add new images to form data
    newImages.forEach((file, index) => {
      formData.append(`new_images_${index}`, file);
    });
    formData.append('new_images_count', newImages.length);
    
    // Add deleted image IDs
    if (deletedImageIds.length > 0) {
      formData.append('deleted_image_ids', JSON.stringify(deletedImageIds));
    }
    
    const response = await fetch(`${API_BASE_URL}/coach/update-showcase-images`, {
      method: 'POST',
      body: formData
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to update showcase images');
    }
    
    // Reset state
    newImages = [];
    deletedImageIds = [];
    showcaseImagesChanged = false;
    
    // Hide save button
    if (saveShowcaseChangesBtn) {
      saveShowcaseChangesBtn.classList.add('hidden');
    }
    
    // Reload images
    await loadShowcaseImages();
    
    // Show success toast
    showToast('Success', 'Showcase images updated successfully', 'success');
    
  } catch (error) {
    console.error('Error saving showcase images:', error);
    showToast('Error', 'Failed to update showcase images: ' + error.message, 'error');
  } finally {
    // Reset button state
    const saveShowcaseChangesBtn = document.getElementById('save-showcase-changes');
    if (saveShowcaseChangesBtn) {
      saveShowcaseChangesBtn.disabled = false;
      saveShowcaseChangesBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Changes';
    }
  }
}