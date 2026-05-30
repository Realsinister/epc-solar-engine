const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('electron', {
  // Expose safe electron APIs here if needed
});
