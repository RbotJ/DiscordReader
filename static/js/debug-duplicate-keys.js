/**
 * Debug utility for detecting duplicate React keys
 * This script adds a patch to React's development mode error reporting
 * to help identify which component has duplicate keys
 */

// Store original console.error to restore later
const originalConsoleError = console.error;

// Create a modified version that adds more context to React key warnings
console.error = function(...args) {
  // Check if this is a React duplicate key warning
  if (args[0] && typeof args[0] === 'string' && 
      args[0].includes('Encountered two children with the same key')) {
    
    // Log the duplicate key for easier debugging
    console.warn('DUPLICATE KEY DETECTED:', args[1]);
    
    // Try to capture stack trace to see which component is causing the issue
    console.warn('Possible source component:', new Error().stack);
  }
  
  // Call original console.error with all arguments
  return originalConsoleError.apply(console, args);
};

// Log that the debug patch is active
console.log('React duplicate key debug patch installed');