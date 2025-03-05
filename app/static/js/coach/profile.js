// app/static/js/coach/profile.js
// Populate profile form with coach data
function populateProfileForm(coachData) {
    const user = coachData.user;
    const coach = coachData;
  
    // User data
    document.getElementById('first_name').value = user.first_name;
    document.getElementById('last_name').value = user.last_name;
    document.getElementById('email').value = user.email;
    document.getElementById('gender').value = user.gender || '';
    document.getElementById('location').value = user.location;
    document.getElementById('dupr_rating').value = user.dupr_rating;
    
    // Coach data
    document.getElementById('hourly_rate').value = coach.hourly_rate;
    document.getElementById('years_experience').value = coach.years_experience;
    document.getElementById('specialties').value = coach.specialties;
    document.getElementById('biography').value = coach.biography;
  }
  
  // Initialize profile image functionality
  function initializeProfileImageHandling() {
    const profilePictureInput = document.getElementById('profile-picture-input');
    const changeProfilePictureBtn = document.getElementById('change-profile-picture');
    const removeProfilePictureBtn = document.getElementById('remove-profile-picture');
    const profilePreviewImage = document.getElementById('profile-preview-image');
  
    // Change profile picture
    changeProfilePictureBtn?.addEventListener('click', function() {
      profilePictureInput.click();
    });
  
    profilePictureInput?.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        const reader = new FileReader();
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
          removeProfilePictureBtn.style.display = 'block';
          
          // Upload the image
          uploadProfilePicture(profilePictureInput.files[0]);
        };
        reader.readAsDataURL(this.files[0]);
      }
    });
  
    // Remove profile picture
    removeProfilePictureBtn?.addEventListener('click', function() {
      // Ask for confirmation
      if (confirm('Are you sure you want to remove your profile picture?')) {
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
  
  // Upload profile picture to server
  async function uploadProfilePicture(file) {
    try {
      const formData = new FormData();
      formData.append('profile_picture', file);
      
      // Show loading indicator
      const changeProfilePictureBtn = document.getElementById('change-profile-picture');
      changeProfilePictureBtn.innerHTML = '<i class="fas fa-spinner fa-spin text-white text-xl"></i>';
      
      const response = await fetch('/api/coach/update-profile-picture', {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to upload profile picture');
      }
      
      // Reset loading indicator
      changeProfilePictureBtn.innerHTML = '<i class="fas fa-camera text-white text-xl"></i>';
      
      // Show success message
      showToast('Success', 'Profile picture updated successfully', 'success');
    } catch (error) {
      console.error('Error uploading profile picture:', error);
      document.getElementById('change-profile-picture').innerHTML = '<i class="fas fa-camera text-white text-xl"></i>';
      showToast('Error', 'Failed to update profile picture', 'error');
    }
  }
  
  // Remove profile picture from server
  async function removeProfilePicture() {
    try {
      const response = await fetch('/api/coach/remove-profile-picture', {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Failed to remove profile picture');
      }
      
      showToast('Success', 'Profile picture removed successfully', 'success');
    } catch (error) {
      console.error('Error removing profile picture:', error);
      showToast('Error', 'Failed to remove profile picture', 'error');
    }
  }
  
  // Initialize showcase images functionality
  function initializeShowcaseImages() {
    const showcaseImagesContainer = document.getElementById('showcase-images-container');
    const showcaseImagesInput = document.getElementById('showcase-images-input');
    const addShowcaseImagesBtn = document.getElementById('add-showcase-images');
    const saveShowcaseChangesBtn = document.getElementById('save-showcase-changes');
    
    // Track changes to showcase images
    let showcaseImagesChanged = false;
    let deletedImageIds = [];
    let newImages = [];
  
    // Load showcase images
    loadShowcaseImages();
  
    // Add showcase images button
    addShowcaseImagesBtn?.addEventListener('click', function() {
      showcaseImagesInput.click();
    });
  
    // Handle file selection
    showcaseImagesInput?.addEventListener('change', function() {
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
        saveShowcaseChangesBtn.classList.remove('hidden');
        showcaseImagesChanged = true;
      }
    });
  
    // Save changes button
    saveShowcaseChangesBtn?.addEventListener('click', function() {
      if (showcaseImagesChanged) {
        saveShowcaseChanges();
      }
    });
  
    // Load showcase images from server
    async function loadShowcaseImages() {
      try {
        const response = await fetch('/api/coach/showcase-images');
        
        if (!response.ok) {
          throw new Error('Failed to load showcase images');
        }
        
        const data = await response.json();
        
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
  
    // Add a showcase image preview to the container
    function addShowcaseImagePreview(imageUrl, imageId, isNew = false) {
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
        saveShowcaseChangesBtn.classList.remove('hidden');
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
      const placeholder = document.createElement('div');
      placeholder.className = 'add-image-placeholder';
      placeholder.innerHTML = `
        <i class="fas fa-plus text-gray-400 text-2xl mb-1"></i>
        <span class="text-xs text-gray-500">Add Photo</span>
      `;
      
      placeholder.addEventListener('click', function() {
        addShowcaseImagesBtn.click();
      });
      
      showcaseImagesContainer.appendChild(placeholder);
    }
  
    // Save showcase image changes
    async function saveShowcaseChanges() {
      try {
        // Show loading state
        saveShowcaseChangesBtn.disabled = true;
        saveShowcaseChangesBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
        
        const formData = new FormData();
        
        // Add new images to form data
        newImages.forEach(file => {
          formData.append('new_images', file);
        });
        
        // Add deleted image IDs
        if (deletedImageIds.length > 0) {
          formData.append('deleted_image_ids', JSON.stringify(deletedImageIds));
        }
        
        const response = await fetch('/api/coach/update-showcase-images', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          throw new Error('Failed to update showcase images');
        }
        
        // Reset state
        newImages = [];
        deletedImageIds = [];
        showcaseImagesChanged = false;
        
        // Hide save button
        saveShowcaseChangesBtn.classList.add('hidden');
        
        // Reload images
        await loadShowcaseImages();
        
        // Show success toast
        showToast('Success', 'Showcase images updated successfully', 'success');
        
      } catch (error) {
        console.error('Error saving showcase images:', error);
        showToast('Error', 'Failed to update showcase images: ' + error.message, 'error');
      } finally {
        // Reset button state
        saveShowcaseChangesBtn.disabled = false;
        saveShowcaseChangesBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Changes';
      }
    }
  }
  
  // Export functions
  export {
    populateProfileForm,
    initializeProfileImageHandling,
    initializeShowcaseImages,
    uploadProfilePicture,
    removeProfilePicture
  };