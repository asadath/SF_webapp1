# Local development

## Storage emulator (required for `func start`)

This app uses `AzureWebJobsStorage` with `UseDevelopmentStorage=true`, so the Azure Storage emulator must be running or the timer trigger will fail to start.

### Option A: Run Azurite (recommended)

1. Install Azurite (requires Node.js):
   ```bash
   npm install -g azurite
   ```
2. In a **separate terminal**, start Azurite:
   ```bash
   azurite
   ```
3. In this folder, run:
   ```bash
   func start
   ```

### Option B: Use a real Azure Storage account

1. Create a Storage account in Azure (or use an existing one).
2. In `local.settings.json`, set `AzureWebJobsStorage` to the connection string, e.g.:
   ```json
   "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=..."
   ```

After storage is available, the "Unable to access AzureWebJobsStorage" and "listener for function 'timer_trigger' was unable to start" errors will stop.
