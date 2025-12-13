# Running ContactSphere as a Service

You can run ContactSphere as a background service using systemd.

## Setup

1. **Edit the service file (Optional)**
   If you want to change the ports, edit `contactsphere.service` and modify the `Environment` variables:
   ```ini
   Environment="BACKEND_PORT=9000"
   Environment="FRONTEND_PORT=9090"
   ```

2. **Install the service**
   Copy the service file to the systemd directory:
   ```bash
   sudo cp contactsphere.service /etc/systemd/system/
   ```

3. **Reload systemd**
   ```bash
   sudo systemctl daemon-reload
   ```

4. **Enable and Start the service**
   ```bash
   sudo systemctl enable contactsphere
   sudo systemctl start contactsphere
   ```

5. **Check status**
   ```bash
   sudo systemctl status contactsphere
   ```

6. **To Stop the Service**
sudo systemctl stop contactsphere

7. **To stop it and prevent it from starting on boot**
sudo systemctl disable --now contactsphere
sudo systemctl disable --now contactsphere


## Viewing Logs

To see the application logs:
```bash
journalctl -u contactsphere -f
```

## Automatic Port Adjustment

The application is smart enough to detect if you've changed the ports via environment variables (`BACKEND_PORT`, `FRONTEND_PORT`) and will automatically adjust the `GOOGLE_REDIRECT_URI` and `FRONTEND_URL` loaded from your `.env` file to match the new ports, preserving your hostname/IP configuration.

However, please note:
1.  **Google OAuth**: If you change the backend port, you **MUST** also update the "Authorized redirect URIs" in your Google Cloud Console to match the new port (e.g., `http://localhost:9000/auth/google/callback`).
2.  **Frontend URL**: The application will redirect to the new frontend port automatically.

## Manual Run with Custom Ports

You can also run the application manually with custom ports:

```bash
export BACKEND_PORT=9000
export FRONTEND_PORT=9090
./start.sh
```
