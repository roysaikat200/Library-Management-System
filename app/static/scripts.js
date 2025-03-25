// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Flash message auto-dismiss after 1 minute
    setTimeout(function() {
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 500); // Ensure complete removal after fading
        });
    }, 10000); // 1 minute (60,000 milliseconds)

    // Add event listener to search form
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            // Don't submit if search field is empty
            const searchField = document.getElementById('search');
            if (searchField && searchField.value.trim() === '') {
                e.preventDefault();
            }
        });
    }

    // Handle genre filter change
    const genreFilter = document.getElementById('genreFilter');
    if (genreFilter) {
        genreFilter.addEventListener('change', function() {
            document.getElementById('searchForm').submit();
        });
    }

    // Book deletion confirmation
    const deleteButtons = document.querySelectorAll('.delete-book');
    if (deleteButtons) {
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to delete this book? This action cannot be undone.')) {
                    e.preventDefault();
                }
            });
        });
    }

    // Toggle password visibility
    const togglePasswordBtns = document.querySelectorAll('.toggle-password');
    if (togglePasswordBtns) {
        togglePasswordBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const passwordField = document.querySelector(this.getAttribute('data-target'));
                if (passwordField) {
                    const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
                    passwordField.setAttribute('type', type);
                    
                    // Toggle icon
                    this.innerHTML = type === 'password' 
                        ? '<i class="bi bi-eye"></i>'
                        : '<i class="bi bi-eye-slash"></i>';
                }
            });
        });
    }

    // Due date highlighting for borrowed books
    const dueDates = document.querySelectorAll('.due-date');
    if (dueDates) {
        dueDates.forEach(date => {
            const dueDate = new Date(date.dataset.date);
            const today = new Date();
            
            // Calculate days until due
            const timeDiff = dueDate - today;
            const daysDiff = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            
            if (daysDiff < 0) {
                // Overdue
                date.classList.add('text-danger', 'fw-bold');
            } else if (daysDiff < 3) {
                // Almost due
                date.classList.add('text-warning', 'fw-bold');
            }
        });
    }

    // Confirm book return
    const returnButtons = document.querySelectorAll('.return-book');
    if (returnButtons) {
        returnButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to return this book?')) {
                    e.preventDefault();
                }
            });
        });
    }

    // Confirm book renewal
    const renewButtons = document.querySelectorAll('.renew-book');
    if (renewButtons) {
        renewButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to renew this book for 7 more days?')) {
                    e.preventDefault();
                }
            });
        });
    }
});
