/**
 * Utility functions for the trading application
 * 
 * This file contains common utility functions used throughout the application
 * including formatters, data helpers, and DOM utilities.
 */

/**
 * Format a number as currency
 * @param {number} value - The value to format
 * @param {string} [currency='USD'] - The currency code
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted currency string
 */
function formatCurrency(value, currency = 'USD', locale = 'en-US') {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency
  }).format(value);
}

/**
 * Format a number as a percentage
 * @param {number} value - The value to format (e.g., 0.15 for 15%)
 * @param {number} [decimals=2] - Number of decimal places
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted percentage string
 */
function formatPercent(value, decimals = 2, locale = 'en-US') {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

/**
 * Format a date in a readable format
 * @param {Date|string|number} date - The date to format
 * @param {string} [format='short'] - Format style: 'short', 'medium', 'long', or 'full'
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted date string
 */
function formatDate(date, format = 'short', locale = 'en-US') {
  const dateObj = date instanceof Date ? date : new Date(date);
  
  const options = { 
    dateStyle: format
  };
  
  return new Intl.DateTimeFormat(locale, options).format(dateObj);
}

/**
 * Format a time in a readable format
 * @param {Date|string|number} time - The time to format
 * @param {boolean} [includeSeconds=false] - Whether to include seconds
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted time string
 */
function formatTime(time, includeSeconds = false, locale = 'en-US') {
  const dateObj = time instanceof Date ? time : new Date(time);
  
  const options = { 
    timeStyle: includeSeconds ? 'medium' : 'short'
  };
  
  return new Intl.DateTimeFormat(locale, options).format(dateObj);
}

/**
 * Format a datetime in a readable format
 * @param {Date|string|number} datetime - The datetime to format
 * @param {string} [dateFormat='short'] - Date format style: 'short', 'medium', 'long', or 'full'
 * @param {boolean} [includeSeconds=false] - Whether to include seconds in time
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted datetime string
 */
function formatDateTime(datetime, dateFormat = 'short', includeSeconds = false, locale = 'en-US') {
  const dateObj = datetime instanceof Date ? datetime : new Date(datetime);
  
  const options = {
    dateStyle: dateFormat,
    timeStyle: includeSeconds ? 'medium' : 'short'
  };
  
  return new Intl.DateTimeFormat(locale, options).format(dateObj);
}

/**
 * Truncate a string to a specified length and add ellipsis if truncated
 * @param {string} str - The string to truncate
 * @param {number} maxLength - Maximum length of the string
 * @returns {string} Truncated string
 */
function truncateString(str, maxLength) {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '...';
}

/**
 * Debounce a function to limit how often it can be called
 * @param {Function} func - The function to debounce
 * @param {number} wait - The time to wait in milliseconds
 * @returns {Function} Debounced function
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
 * Create an element with attributes and children
 * @param {string} tag - The tag name of the element
 * @param {Object} [attributes={}] - Attributes to set on the element
 * @param {Array|Node|string} [children=[]] - Child elements or text content
 * @returns {HTMLElement} The created element
 */
function createElement(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);
  
  // Set attributes
  Object.entries(attributes).forEach(([key, value]) => {
    if (key === 'className') {
      element.className = value;
    } else if (key === 'style' && typeof value === 'object') {
      Object.assign(element.style, value);
    } else if (key.startsWith('on') && typeof value === 'function') {
      element.addEventListener(key.substring(2).toLowerCase(), value);
    } else {
      element.setAttribute(key, value);
    }
  });
  
  // Add children
  if (Array.isArray(children)) {
    children.forEach(child => {
      if (child instanceof Node) {
        element.appendChild(child);
      } else {
        element.appendChild(document.createTextNode(String(child)));
      }
    });
  } else if (children instanceof Node) {
    element.appendChild(children);
  } else {
    element.textContent = String(children);
  }
  
  return element;
}

/**
 * Add class(es) to an element
 * @param {HTMLElement} element - The element to add class(es) to
 * @param {string|string[]} classes - Class name(s) to add
 */
function addClass(element, classes) {
  if (Array.isArray(classes)) {
    classes.forEach(cls => element.classList.add(cls));
  } else {
    element.classList.add(classes);
  }
}

/**
 * Remove class(es) from an element
 * @param {HTMLElement} element - The element to remove class(es) from
 * @param {string|string[]} classes - Class name(s) to remove
 */
function removeClass(element, classes) {
  if (Array.isArray(classes)) {
    classes.forEach(cls => element.classList.remove(cls));
  } else {
    element.classList.remove(classes);
  }
}

/**
 * Toggle class(es) on an element
 * @param {HTMLElement} element - The element to toggle class(es) on
 * @param {string|string[]} classes - Class name(s) to toggle
 * @param {boolean} [force] - If provided, adds class when true, removes when false
 */
function toggleClass(element, classes, force) {
  if (Array.isArray(classes)) {
    classes.forEach(cls => element.classList.toggle(cls, force));
  } else {
    element.classList.toggle(classes, force);
  }
}

/**
 * Check if element has a specific class
 * @param {HTMLElement} element - The element to check
 * @param {string} className - Class name to check for
 * @returns {boolean} True if element has the class, false otherwise
 */
function hasClass(element, className) {
  return element.classList.contains(className);
}

/**
 * Get query parameters from the URL
 * @returns {Object} Object containing query parameters
 */
function getQueryParams() {
  const params = {};
  const queryString = window.location.search;
  
  if (!queryString) return params;
  
  const searchParams = new URLSearchParams(queryString);
  
  for (const [key, value] of searchParams.entries()) {
    params[key] = value;
  }
  
  return params;
}

/**
 * Format a number with thousands separators
 * @param {number} num - The number to format
 * @param {number} [decimals=0] - Number of decimal places
 * @param {string} [locale='en-US'] - The locale to use for formatting
 * @returns {string} Formatted number string
 */
function formatNumber(num, decimals = 0, locale = 'en-US') {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
}

/**
 * Deep clone an object
 * @param {Object} obj - The object to clone
 * @returns {Object} Cloned object
 */
function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Check if a value is a number or can be converted to a number
 * @param {*} value - The value to check
 * @returns {boolean} True if value is or can be converted to a number
 */
function isNumeric(value) {
  return !isNaN(parseFloat(value)) && isFinite(value);
}

/**
 * Format a price value for display
 * @param {number|string} price - The price to format
 * @param {number} [precision=2] - Number of decimal places
 * @returns {string} Formatted price
 */
function formatPrice(price, precision = 2) {
  if (!isNumeric(price)) return 'N/A';
  
  return parseFloat(price).toFixed(precision);
}

/**
 * Format a UTC timestamp for local display
 * @param {string|Date} utcString - UTC timestamp string or Date object
 * @param {string} [timeZone='America/Chicago'] - Target timezone
 * @returns {string} Formatted timestamp string
 */
function formatTimestamp(utcString, timeZone = 'America/Chicago') {
  if (!utcString) return 'N/A';
  
  const options = {
    timeZone: timeZone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZoneName: 'short'
  };
  
  try {
    const date = new Date(utcString);
    return date.toLocaleString('en-US', options);
  } catch (error) {
    console.warn('Failed to format timestamp:', utcString, error);
    return 'Invalid Date';
  }
}

// Make functions globally available for older browsers
window.formatCurrency = formatCurrency;
window.formatPercent = formatPercent;
window.formatDate = formatDate;
window.formatTime = formatTime;
window.formatDateTime = formatDateTime;
window.formatTimestamp = formatTimestamp;
window.truncateString = truncateString;
window.debounce = debounce;
window.createElement = createElement;
window.addClass = addClass;
window.removeClass = removeClass;
window.toggleClass = toggleClass;
window.hasClass = hasClass;
window.getQueryParams = getQueryParams;
window.formatNumber = formatNumber;
window.deepClone = deepClone;
window.isNumeric = isNumeric;
window.formatPrice = formatPrice;