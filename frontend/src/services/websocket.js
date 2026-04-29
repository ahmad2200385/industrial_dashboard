const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8003/ws'

class WebSocketService {
  constructor() {
    this.ws = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 30
    this.baseReconnectInterval = 1500

    this.messageHandlers = []
    this.connectHandlers = []
    this.disconnectHandlers = []

    this.subscribedMachines = new Set()
    this.reconnectToken = null

    this._pingTimer = null
    this._isManualClose = false
  }

  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this._isManualClose = false
    const url = this.reconnectToken ? `${WS_URL}?reconnect_token=${encodeURIComponent(this.reconnectToken)}` : WS_URL

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.isConnected = true
        this.reconnectAttempts = 0
        this._startHeartbeat()
        this.connectHandlers.forEach((handler) => handler())
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          if (message.type === 'connected' && message.reconnect_token) {
            this.reconnectToken = message.reconnect_token
          }

          if (message.type === 'resume_confirmed' && Array.isArray(message.machine_ids)) {
            this.subscribedMachines = new Set(message.machine_ids)
          }

          this.messageHandlers.forEach((handler) => handler(message))
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = () => {
        this.isConnected = false
        this._stopHeartbeat()
        this.disconnectHandlers.forEach((handler) => handler())

        if (!this._isManualClose) {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.attemptReconnect()
    }
  }

  disconnect() {
    this._isManualClose = true
    this._stopHeartbeat()
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts += 1
    const interval = Math.min(this.baseReconnectInterval * (2 ** (this.reconnectAttempts - 1)), 15000)

    setTimeout(() => {
      this.connect()
    }, interval)
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    }
  }

  subscribeToMachine(machineId) {
    const id = Number(machineId)
    if (!this.subscribedMachines.has(id)) {
      this.subscribedMachines.add(id)
      this.send({ action: 'subscribe', machine_ids: [id] })
    }
  }

  subscribeToMachines(machineIds) {
    const normalized = machineIds.map((id) => Number(id))
    const newSubscriptions = normalized.filter((id) => !this.subscribedMachines.has(id))
    if (newSubscriptions.length > 0) {
      newSubscriptions.forEach((id) => this.subscribedMachines.add(id))
      this.send({ action: 'subscribe', machine_ids: newSubscriptions })
    }
  }

  unsubscribeFromMachine(machineId) {
    const id = Number(machineId)
    if (this.subscribedMachines.has(id)) {
      this.subscribedMachines.delete(id)
      this.send({ action: 'unsubscribe', machine_ids: [id] })
    }
  }

  subscribeToAll() {
    this.send({ action: 'subscribe', machine_ids: [] })
  }

  unsubscribeFromAll() {
    const machineIds = Array.from(this.subscribedMachines)
    if (machineIds.length > 0) {
      this.subscribedMachines.clear()
      this.send({ action: 'unsubscribe', machine_ids: machineIds })
    }
  }

  onMessage(handler) {
    this.messageHandlers.push(handler)
  }

  onConnect(handler) {
    this.connectHandlers.push(handler)
  }

  onDisconnect(handler) {
    this.disconnectHandlers.push(handler)
  }

  ping() {
    this.send({ action: 'ping' })
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this._pingTimer = setInterval(() => {
      this.ping()
    }, 25000)
  }

  _stopHeartbeat() {
    if (this._pingTimer) {
      clearInterval(this._pingTimer)
      this._pingTimer = null
    }
  }

  getConnectionStatus() {
    return {
      connected: this.isConnected,
      subscribedMachines: Array.from(this.subscribedMachines),
      reconnectAttempts: this.reconnectAttempts,
      reconnectToken: this.reconnectToken
    }
  }
}

export const websocketService = new WebSocketService()

