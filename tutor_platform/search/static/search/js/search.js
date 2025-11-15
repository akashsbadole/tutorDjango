/**
 * Search App JavaScript
 * Handles search functionality, suggestions, and real-time updates
 */

// Global variables
let searchTimeout;
let currentSearchRequest = null;
let searchSuggestions = [];

// DOM Elements
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results-container');
const suggestionsDropdown = document.getElementById('suggestions-dropdown');
const advancedFilters = document.getElementById('advanced-filters');
const searchForm = document.getElementById('search-form');

// Initialize search functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeSearch();
    initializeFilters();
    initializeViewMode();
    initializeKeyboardNavigation();
});

/**
 * Initialize search functionality
 */
function initializeSearch() {
    if (!searchInput) return;
    
    // Setup search input event listeners
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('focus', handleSearchFocus);
    searchInput.addEventListener('blur', handleSearchBlur);
    searchInput.addEventListener('keydown', handleSearchKeydown);
    
    // Setup search form submission
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearchSubmit);
    }
    
    // Load recent searches
    loadRecentSearches();
}

/**
 * Handle search input changes
 */
function handleSearchInput(event) {
    const query = event.target.value.trim();
    
    // Clear previous timeout
    clearTimeout(searchTimeout);
    
    // Hide suggestions if query is empty
    if (query.length < 2) {
        hideSuggestions();
        return;
    }
    
    // Show loading state
    showSearchLoading();
    
    // Debounce search requests
    searchTimeout = setTimeout(() => {
        fetchSearchSuggestions(query);
    }, 300);
}

/**
 * Handle search input focus
 */
function handleSearchFocus() {
    const query = searchInput.value.trim();
    if (query.length >= 2 && searchSuggestions.length > 0) {
        showSuggestions();
    }
}

/**
 * Handle search input blur
 */
function handleSearchBlur() {
    // Delay hiding suggestions to allow clicking on them
    setTimeout(() => {
        hideSuggestions();
    }, 200);
}

/**
 * Handle search input keyboard events
 */
function handleSearchKeydown(event) {
    // Handle escape key
    if (event.key === 'Escape') {
        hideSuggestions();
        return;
    }
    
    // Handle arrow keys for navigation
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        navigateSuggestions(event.key === 'ArrowDown' ? 1 : -1);
        return;
    }
    
    // Handle enter key
    if (event.key === 'Enter') {
        const activeSuggestion = document.querySelector('.suggestion-item.active');
        if (activeSuggestion) {
            event.preventDefault();
            selectSuggestion(activeSuggestion);
        }
    }
}

/**
 * Handle search form submission
 */
function handleSearchSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(searchForm);
    const query = formData.get('q');
    
    if (query) {
        // Save to recent searches
        saveRecentSearch(query);
        
        // Track search analytics
        trackSearch(query, formData);
    }
    
    // Submit the form
    searchForm.submit();
}

/**
 * Fetch search suggestions
 */
async function fetchSearchSuggestions(query) {
    try {
        // Cancel previous request if still pending
        if (currentSearchRequest) {
            currentSearchRequest.abort();
        }
        
        currentSearchRequest = new AbortController();
        
        const response = await fetch(`/search/api/suggestions/?q=${encodeURIComponent(query)}`, {
            signal: currentSearchRequest.signal
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const data = await response.json();
        searchSuggestions = data.suggestions || [];
        
        if (searchSuggestions.length > 0) {
            displaySuggestions(searchSuggestions);
        } else {
            hideSuggestions();
        }
        
        hideSearchLoading();
    } catch (error) {
        console.error('Error fetching search suggestions:', error);
        hideSearchLoading();
    }
}

/**
 * Display search suggestions
 */
function displaySuggestions(suggestions) {
    if (!suggestionsDropdown) return;
    
    // Clear existing suggestions
    suggestionsDropdown.innerHTML = '';
    
    // Create suggestion items
    suggestions.forEach((suggestion, index) => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.textContent = suggestion;
        item.dataset.index = index;
        
        // Add click event
        item.addEventListener('click', () => {
            selectSuggestion(item);
        });
        
        suggestionsDropdown.appendChild(item);
    });
    
    // Show suggestions dropdown
    showSuggestions();
}

/**
 * Show suggestions dropdown
 */
function showSuggestions() {
    if (suggestionsDropdown) {
        suggestionsDropdown.style.display = 'block';
        suggestionsDropdown.classList.add('show');
    }
}

/**
 * Hide suggestions dropdown
 */
function hideSuggestions() {
    if (suggestionsDropdown) {
        suggestionsDropdown.style.display = 'none';
        suggestionsDropdown.classList.remove('show');
    }
}

/**
 * Select a suggestion
 */
function selectSuggestion(item) {
    const suggestion = item.textContent;
    searchInput.value = suggestion;
    hideSuggestions();
    
    // Trigger search
    if (searchForm) {
        searchForm.dispatchEvent(new Event('submit'));
    }
}

/**
 * Navigate suggestions with keyboard
 */
function navigateSuggestions(direction) {
    const items = document.querySelectorAll('.suggestion-item');
    if (items.length === 0) return;
    
    // Find currently active item
    let activeIndex = -1;
    items.forEach((item, index) => {
        if (item.classList.contains('active')) {
            activeIndex = index;
        }
    });
    
    // Remove active class from current item
    if (activeIndex >= 0) {
        items[activeIndex].classList.remove('active');
    }
    
    // Calculate new active index
    let newIndex = activeIndex + direction;
    if (newIndex < 0) {
        newIndex = items.length - 1;
    } else if (newIndex >= items.length) {
        newIndex = 0;
    }
    
    // Add active class to new item
    items[newIndex].classList.add('active');
    
    // Update input value
    searchInput.value = items[newIndex].textContent;
}

/**
 * Show search loading state
 */
function showSearchLoading() {
    if (searchInput) {
        searchInput.classList.add('search-loading');
    }
}

/**
 * Hide search loading state
 */
function hideSearchLoading() {
    if (searchInput) {
        searchInput.classList.remove('search-loading');
    }
}

/**
 * Save recent search
 */
function saveRecentSearch(query) {
    try {
        // Get existing recent searches
        let recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        
        // Remove if already exists
        recentSearches = recentSearches.filter(search => search !== query);
        
        // Add to beginning
        recentSearches.unshift(query);
        
        // Keep only last 10
        recentSearches = recentSearches.slice(0, 10);
        
        // Save to localStorage
        localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
    } catch (error) {
        console.error('Error saving recent search:', error);
    }
}

/**
 * Load recent searches
 */
function loadRecentSearches() {
    try {
        const recentSearches = JSON.parse(localStorage.getItem('recentSearches') || '[]');
        displayRecentSearches(recentSearches);
    } catch (error) {
        console.error('Error loading recent searches:', error);
    }
}

/**
 * Display recent searches
 */
function displayRecentSearches(recentSearches) {
    // This would be implemented in the template
    // For now, we'll just log it
    console.log('Recent searches:', recentSearches);
}

/**
 * Track search analytics
 */
function trackSearch(query, formData) {
    try {
        // Send analytics data to server
        fetch('/search/api/track/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                query: query,
                content_type: formData.get('content_type'),
                filters: Object.fromEntries(formData.entries())
            })
        }).catch(error => {
            console.error('Error tracking search:', error);
        });
    } catch (error) {
        console.error('Error tracking search:', error);
    }
}

/**
 * Initialize filters
 */
function initializeFilters() {
    if (!advancedFilters) return;
    
    // Setup filter change events
    const filterInputs = advancedFilters.querySelectorAll('input, select');
    filterInputs.forEach(input => {
        input.addEventListener('change', handleFilterChange);
    });
}

/**
 * Handle filter changes
 */
function handleFilterChange(event) {
    // Debounce filter changes
    clearTimeout(window.filterTimeout);
    window.filterTimeout = setTimeout(() => {
        // Auto-submit form when filters change
        if (searchForm) {
            searchForm.dispatchEvent(new Event('submit'));
        }
    }, 1000);
}

/**
 * Initialize view mode
 */
function initializeViewMode() {
    const viewModeRadios = document.querySelectorAll('input[name="view-mode"]');
    viewModeRadios.forEach(radio => {
        radio.addEventListener('change', handleViewModeChange);
    });
}

/**
 * Handle view mode changes
 */
function handleViewModeChange(event) {
    const viewMode = event.target.value;
    const resultsContainer = document.getElementById('results-list');
    
    if (!resultsContainer) return;
    
    if (viewMode === 'grid') {
        resultsContainer.classList.add('search-results-grid');
        resultsContainer.classList.remove('search-results-list');
    } else {
        resultsContainer.classList.add('search-results-list');
        resultsContainer.classList.remove('search-results-grid');
    }
    
    // Save preference
    localStorage.setItem('searchViewMode', viewMode);
}

/**
 * Initialize keyboard navigation
 */
function initializeKeyboardNavigation() {
    // Add keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(event) {
    // Ctrl/Cmd + K: Focus search input
    if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault();
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape: Clear search
    if (event.key === 'Escape' && document.activeElement === searchInput) {
        if (searchInput.value) {
            searchInput.value = '';
            hideSuggestions();
        } else {
            searchInput.blur();
        }
    }
}

/**
 * Get CSRF token
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format search result count
 */
function formatResultCount(count) {
    if (count === 0) {
        return 'No results';
    } else if (count === 1) {
        return '1 result';
    } else {
        return `${count.toLocaleString()} results`;
    }
}

/**
 * Highlight search term in text
 */
function highlightSearchTerm(text, term) {
    if (!term || !text) return text;
    
    const regex = new RegExp(`(${term})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

/**
 * Truncate text
 */
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 1) {
        return 'Today';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
    } else if (diffDays < 365) {
        const months = Math.floor(diffDays / 30);
        return `${months} month${months > 1 ? 's' : ''} ago`;
    } else {
        const years = Math.floor(diffDays / 365);
        return `${years} year${years > 1 ? 's' : ''} ago`;
    }
}

/**
 * Export search results
 */
function exportSearchResults(format = 'csv') {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('export', format);
    window.open(currentUrl.toString(), '_blank');
}

/**
 * Save search
 */
function saveCurrentSearch() {
    const query = searchInput ? searchInput.value : '';
    if (!query) {
        showAlert('Please enter a search query', 'warning');
        return;
    }
    
    // Show save search modal
    const modal = new bootstrap.Modal(document.getElementById('saveSearchModal'));
    if (modal) {
        modal.show();
    }
}

/**
 * Clear search history
 */
function clearSearchHistory() {
    if (confirm('Are you sure you want to clear your search history?')) {
        localStorage.removeItem('recentSearches');
        showAlert('Search history cleared', 'success');
        
        // Reload recent searches
        loadRecentSearches();
    }
}

/**
 * Load saved searches
 */
async function loadSavedSearches() {
    try {
        const response = await fetch('/search/api/saved-searches/', {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const data = await response.json();
        displaySavedSearches(data.saved_searches || []);
    } catch (error) {
        console.error('Error loading saved searches:', error);
    }
}

/**
 * Display saved searches
 */
function displaySavedSearches(savedSearches) {
    // This would be implemented in the template
    // For now, we'll just log it
    console.log('Saved searches:', savedSearches);
}

/**
 * Run saved search
 */
function runSavedSearch(searchId) {
    window.location.href = `/search/saved/${searchId}/`;
}

/**
 * Delete saved search
 */
async function deleteSavedSearch(searchId) {
    if (!confirm('Are you sure you want to delete this saved search?')) {
        return;
    }
    
    try {
        const response = await fetch(`/search/api/saved-searches/${searchId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        showAlert('Saved search deleted', 'success');
        
        // Reload saved searches
        loadSavedSearches();
    } catch (error) {
        console.error('Error deleting saved search:', error);
        showAlert('Error deleting saved search', 'danger');
    }
}

// Export functions for use in templates
window.SearchApp = {
    fetchSearchSuggestions,
    saveRecentSearch,
    loadRecentSearches,
    trackSearch,
    showAlert,
    debounce,
    throttle,
    formatResultCount,
    highlightSearchTerm,
    truncateText,
    formatDate,
    exportSearchResults,
    saveCurrentSearch,
    clearSearchHistory,
    loadSavedSearches,
    runSavedSearch,
    deleteSavedSearch
};