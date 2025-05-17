
const originalConsoleError = console.error;
console.error = (...args) => {
  if (
    typeof args[0] === 'string' &&
    args[0].startsWith('Encountered two children with the same key')
  ) {
    console.log('⚠️ Duplicate key warning — here's where it came from:');
    console.trace();
  }
  originalConsoleError(...args);
};
