/*
  script.js - Custom JavaScript for UP Funds
  ============================================
  Handles:
  - Sidebar toggle on mobile
  - Auto-dismiss flash messages
  - Form enhancements
*/

document.addEventListener('DOMContentLoaded', function() {

    // ============================================
    // SIDEBAR TOGGLE (Mobile)
    // ============================================
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        });
    }


    // ============================================
    // AUTO-DISMISS FLASH MESSAGES (after 5 seconds)
    // ============================================
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            // Use Bootstrap's alert dismiss method
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });


    // ============================================
    // FORM ENHANCEMENTS
    // ============================================

    // Prevent double-submit on forms
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !form.dataset.submitted) {
                form.dataset.submitted = 'true';
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Processing...';

                // Re-enable after 3 seconds (in case of validation error or slow response)
                setTimeout(function() {
                    form.dataset.submitted = '';
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = submitBtn.dataset.originalText || submitBtn.innerHTML;
                }, 3000);
            }
        });

        // Store original button text for restoration
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.dataset.originalText = submitBtn.innerHTML;
        }
    });


    // ============================================
    // SEARCHABLE STAFF DROPDOWN (simple filter)
    // ============================================
    const staffSelect = document.getElementById('staff_id');
    if (staffSelect && staffSelect.options.length > 10) {
        // For large staff lists, add a simple search input above the select
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'form-control form-control-sm mb-2';
        searchInput.placeholder = 'Type to filter staff...';
        searchInput.id = 'staffSearchInput';

        staffSelect.parentNode.insertBefore(searchInput, staffSelect);

        searchInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            for (let i = 1; i < staffSelect.options.length; i++) {
                const text = staffSelect.options[i].text.toLowerCase();
                staffSelect.options[i].style.display = text.includes(filter) ? '' : 'none';
            }
        });
    }

});
