const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003'

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Machine endpoints
  async getMachines() {
    return this.request('/machines')
  }

  async getMachine(id) {
    return this.request(`/machines/${id}`)
  }

  async createMachine(machine) {
    return this.request('/machines', {
      method: 'POST',
      body: JSON.stringify(machine)
    })
  }

  async updateMachine(id, machine) {
    return this.request(`/machines/${id}`, {
      method: 'PUT',
      body: JSON.stringify(machine)
    })
  }

  async deleteMachine(id) {
    return this.request(`/machines/${id}`, {
      method: 'DELETE'
    })
  }

  // Sensor data endpoints
  async getSensorData(limit = 100) {
    return this.request(`/sensor-data?limit=${limit}`)
  }

  async createSensorData(sensorData) {
    return this.request('/sensor-data', {
      method: 'POST',
      body: JSON.stringify(sensorData)
    })
  }

  // Alerts endpoints
  async getAlerts(limit = 100, activeOnly = false) {
    return this.request(`/alerts?limit=${limit}&active_only=${activeOnly}`)
  }

  async resolveAlert(alertId, reason = null) {
    return this.request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ reason })
    })
  }

  // Redis cache endpoints
  async getCachedMachine(id) {
    return this.request(`/machines/${id}/cached`)
  }

  async getSensorHistory(machineId, limit = 10) {
    return this.request(`/machines/${machineId}/sensor-history?limit=${limit}`)
  }

  async getCachedAlerts(machineId, limit = 10) {
    return this.request(`/machines/${machineId}/alerts/cached?limit=${limit}`)
  }

  async getRedisHealth() {
    return this.request('/redis/health')
  }

  async clearCache(pattern = "*") {
    return this.request(`/redis/cache/clear?pattern=${pattern}`, {
      method: 'POST'
    })
  }
}

export const apiService = new ApiService()

