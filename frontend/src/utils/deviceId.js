/**
 * Device ID management for per-device material isolation.
 *
 * Generates a UUID on first access and persists it in localStorage.
 * This ID is sent with every API request via the X-Device-ID header
 * to scope uploaded materials to the current browser/device.
 */

const STORAGE_KEY = "vfsb_device_id";

/**
 * Get the device ID, generating one if it doesn't exist.
 * @returns {string} The device UUID
 */
export function getDeviceId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

export default getDeviceId;
