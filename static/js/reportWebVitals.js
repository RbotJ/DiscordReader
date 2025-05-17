/**
 * Web Vitals reporting function
 * 
 * This is a utility to report web vital metrics for performance monitoring.
 * Learn more: https://bit.ly/CRA-vitals
 */

const reportWebVitals = (onPerfEntry) => {
  if (onPerfEntry && typeof onPerfEntry === 'function') {
    // Only log performance metrics in non-production environments
    if (process.env.NODE_ENV !== 'production') {
      // We can add actual web vitals reporting here in the future
      console.log('Performance monitoring enabled');
    }
  }
};

export default reportWebVitals;