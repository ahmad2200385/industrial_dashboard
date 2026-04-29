import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiService } from '../services/api.js'
import { websocketService } from '../services/websocket.js'
import { NAV_ITEMS } from '../constants/dashboard.js'

const INITIAL_SORT = { by: 'line', dir: 1 }
const EXPECTED_LINES = Array.from({ length: 10 }, (_, i) => `Line ${i + 1}`)

export function useFactoryDashboard() {
  const machines = ref([])
  const sensorData = ref([])
  const alerts = ref([])
  const isConnected = ref(false)

  const pollingTimer = ref(null)
  const clockTicker = ref(null)

  const searchText = ref('')
  const statusFilter = ref('all')
  const lineFilter = ref('all')
  const sortMode = ref('priority')
  const timeRange = ref('1h')
  const roleView = ref('operator')
  const alertLevelFilter = ref('all')
  const activeNav = ref('overview')

  const selectedMachineId = ref(null)
  const lastRefreshAt = ref(null)
  const lineSortBy = ref(INITIAL_SORT.by)
  const lineSortDir = ref(INITIAL_SORT.dir)

  const wsLatencyMs = ref(null)
  const lastWsAt = ref(null)
  const nowTs = ref(Date.now())
  const clockDriftMs = ref(0)

  const mutedAlerts = ref({})
  const assignedAlerts = ref({})
  const escalatedAlerts = ref({})
  const chartHover = ref(null)

  const temperatureThreshold = 80
  const SENSOR_LIMIT = 2200

  const machineById = computed(() => {
    const map = new Map()
    for (const machine of machines.value) map.set(machine.id, machine)
    return map
  })

  const latestSensorByMachine = computed(() => {
    const latest = Object.create(null)
    for (const row of sensorData.value) {
      if (!latest[row.machine_id]) latest[row.machine_id] = row
    }
    return latest
  })

  const sensorsByLine = computed(() => {
    const byLine = new Map()
    for (const row of sensorData.value) {
      const machine = machineById.value.get(row.machine_id)
      const line = machine?.location
      if (!line) continue
      if (!byLine.has(line)) byLine.set(line, [])
      byLine.get(line).push(Number(row.temperature || 0))
    }
    return byLine
  })

  const nowText = computed(() => new Date(nowTs.value).toLocaleTimeString())
  const clockDriftText = computed(() => `${Math.abs(Math.round(clockDriftMs.value / 1000))}s`)
  const wsLatencyText = computed(() => (!isConnected.value || wsLatencyMs.value == null ? '--' : `${Math.round(wsLatencyMs.value)} ms`))

  function sensorForMachine(machineId) {
    return latestSensorByMachine.value[machineId] || null
  }

  function statusForMachine(machineId) {
    const sensor = sensorForMachine(machineId)
    if (!sensor) return 'no-data'
    if (String(sensor.status || '').toLowerCase() === 'error') return 'error'
    if (Number(sensor.temperature) > temperatureThreshold || String(sensor.status || '').toLowerCase() === 'warning') return 'warning'
    return 'normal'
  }

  function machinePriority(machineId) {
    const status = statusForMachine(machineId)
    if (status === 'error') return 4
    if (status === 'warning') return 3
    if (status === 'normal') return 2
    return 1
  }

  function compareMachines(a, b) {
    if (sortMode.value === 'name') return String(a.name || '').localeCompare(String(b.name || ''))
    if (sortMode.value === 'temp') return Number(sensorForMachine(b.id)?.temperature || -999) - Number(sensorForMachine(a.id)?.temperature || -999)
    return machinePriority(b.id) - machinePriority(a.id)
  }

  const activeAlerts = computed(() =>
    alerts.value
      .filter((alert) => String(alert.state || 'ACTIVE').toUpperCase() === 'ACTIVE')
      .sort((a, b) => new Date(b.created_at || b.timestamp || 0) - new Date(a.created_at || a.timestamp || 0))
  )

  const filteredAlerts = computed(() =>
    activeAlerts.value.filter((alert) => {
      if (alertLevelFilter.value === 'all') return true
      return String(alert.level || '').toUpperCase() === alertLevelFilter.value
    })
  )

  const lineOptions = computed(() => [...new Set(machines.value.map((m) => m.location).filter(Boolean))].sort((a, b) => a.localeCompare(b)))

  const visibleMachines = computed(() => {
    const needle = searchText.value.trim().toLowerCase()
    return machines.value
      .filter((machine) => {
        const status = statusForMachine(machine.id)
        const lineOk = lineFilter.value === 'all' || machine.location === lineFilter.value
        const statusOk = statusFilter.value === 'all' || status === statusFilter.value
        const searchOk = !needle || String(machine.name || '').toLowerCase().includes(needle) || String(machine.id).includes(needle)
        return lineOk && statusOk && searchOk
      })
      .sort(compareMachines)
  })

  const selectedMachine = computed(() => (selectedMachineId.value ? machineById.value.get(selectedMachineId.value) || null : null))
  const selectedMachineHistory = computed(() => (selectedMachineId.value ? sensorData.value.filter((row) => row.machine_id === selectedMachineId.value) : []))

  const statusCounts = computed(() => {
    const counts = { error: 0, warning: 0, normal: 0, 'no-data': 0 }
    for (const machine of machines.value) counts[statusForMachine(machine.id)] += 1
    return counts
  })

  const connectedMachines = computed(() => machines.value.filter((m) => statusForMachine(m.id) !== 'no-data').length)
  const offlineMachines = computed(() => machines.value.length - connectedMachines.value)

  const utilizationPercent = computed(() => (machines.value.length ? Math.round((connectedMachines.value / machines.value.length) * 100) : 0))

  const capacityPercent = computed(() => {
    if (!machines.value.length) return 0
    const loaded = machines.value.filter((m) => Number(sensorForMachine(m.id)?.production_count || 0) > 500).length
    return Math.round((loaded / machines.value.length) * 100)
  })

  const lineSummaries = computed(() => {
    const byLine = Object.create(null)
    for (const machine of machines.value) {
      const line = machine.location || 'Unknown'
      if (!byLine[line]) byLine[line] = { line, total: 0, normal: 0, warning: 0, error: 0, tempSum: 0, tempCount: 0 }
      const bucket = byLine[line]
      bucket.total += 1
      const st = statusForMachine(machine.id)
      if (st === 'normal') bucket.normal += 1
      if (st === 'warning') bucket.warning += 1
      if (st === 'error') bucket.error += 1
      const t = Number(sensorForMachine(machine.id)?.temperature)
      if (Number.isFinite(t)) {
        bucket.tempSum += t
        bucket.tempCount += 1
      }
    }

    return Object.values(byLine).map((row) => ({
      ...row,
      avgTempValue: row.tempCount ? row.tempSum / row.tempCount : 0,
      avgTemp: row.tempCount ? `${(row.tempSum / row.tempCount).toFixed(1)}C` : '--'
    }))
  })

  const sortedLineSummaries = computed(() => {
    const key = lineSortBy.value
    const dir = lineSortDir.value
    return [...lineSummaries.value].sort((a, b) => {
      if (key === 'line') return a.line.localeCompare(b.line) * dir
      if (key === 'avgTemp') return (a.avgTempValue - b.avgTempValue) * dir
      return (Number(a[key] || 0) - Number(b[key] || 0)) * dir
    })
  })

  const displayLineSummaries = computed(() => {
    const map = new Map(sortedLineSummaries.value.map((row) => [row.line, row]))
    for (const line of EXPECTED_LINES) {
      if (!map.has(line)) {
        map.set(line, {
          line,
          total: 0,
          normal: 0,
          warning: 0,
          error: 0,
          tempSum: 0,
          tempCount: 0,
          avgTempValue: 0,
          avgTemp: '--'
        })
      }
    }
    return Array.from(map.values()).sort((a, b) => {
      const key = lineSortBy.value
      const dir = lineSortDir.value
      if (key === 'line') return a.line.localeCompare(b.line) * dir
      if (key === 'avgTemp') return (a.avgTempValue - b.avgTempValue) * dir
      return (Number(a[key] || 0) - Number(b[key] || 0)) * dir
    })
  })

  const overallStatusText = computed(() => {
    if (statusCounts.value.error > 0) return 'CRITICAL'
    if (statusCounts.value.warning > 0) return 'WARNING'
    if (statusCounts.value.normal > 0) return 'NORMAL'
    return 'NO DATA'
  })

  const overallStatusClass = computed(() => {
    if (overallStatusText.value === 'CRITICAL') return 'critical'
    if (overallStatusText.value === 'WARNING') return 'warn'
    return 'ok'
  })

  const uptimeText = computed(() => `${utilizationPercent.value}%`)

  const productionValues = computed(() =>
    visibleMachines.value.map((m) => Number(sensorForMachine(m.id)?.production_count || 0)).filter((v) => Number.isFinite(v))
  )

  const tempValues = computed(() =>
    visibleMachines.value.map((m) => Number(sensorForMachine(m.id)?.temperature || 0)).filter((v) => Number.isFinite(v) && v > 0)
  )

  const throughputText = computed(() => `${Math.round(productionValues.value.reduce((acc, v) => acc + v, 0) / Math.max(visibleMachines.value.length, 1))}`)
  const energyText = computed(() => `${(tempValues.value.reduce((acc, v) => acc + v, 0) / Math.max(tempValues.value.length, 1) * 0.68).toFixed(1)}`)

  const availability = computed(() => utilizationPercent.value)
  const performance = computed(() => Math.min(100, Number(throughputText.value) / 8))
  const quality = computed(() => Math.max(82, 100 - statusCounts.value.error * 6 - statusCounts.value.warning * 2))
  const oeeText = computed(() => `${((availability.value * performance.value * quality.value) / 10000).toFixed(1)}%`)

  const predictiveInsight = computed(() => {
    const hot = visibleMachines.value
      .map((m) => ({ m, t: Number(sensorForMachine(m.id)?.temperature || 0), p: Number(sensorForMachine(m.id)?.production_count || 0) }))
      .filter((x) => x.t > 72 && x.p > 600)
      .sort((a, b) => b.t - a.t)[0]
    if (!hot) return ''
    const eta = Math.max(8, Math.round((temperatureThreshold - hot.t) / 0.35))
    return `${hot.m.name} likely to overheat in ${eta} min if load remains constant.`
  })

  const trendRows = computed(() => [...sensorData.value].slice(0, 90).reverse())

  function seriesToPoints(values, width, height) {
    if (!values.length) return ''
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = Math.max(max - min, 1)
    return values
      .map((v, i) => {
        const x = (i / Math.max(values.length - 1, 1)) * width
        const y = height - ((v - min) / span) * (height - 6) - 3
        return `${x.toFixed(2)},${y.toFixed(2)}`
      })
      .join(' ')
  }

  const temperatureTrendPoints = computed(() => seriesToPoints(trendRows.value.map((r) => Number(r.temperature || 0)), 760, 240))
  const vibrationTrendPoints = computed(() => {
    const values = trendRows.value.map((r, i) => {
      const t = Number(r.temperature || 0)
      const p = Number(r.production_count || 0)
      return t * 0.02 + (p % 90) * 0.05 + (i % 7) * 0.4
    })
    return seriesToPoints(values, 760, 240)
  })
  const outputTrendPoints = computed(() => seriesToPoints(trendRows.value.map((r) => Number(r.production_count || 0)), 760, 220))

  const temperatureBandY = computed(() => {
    const max = Math.max(...trendRows.value.map((r) => Number(r.temperature || 0)), temperatureThreshold, 1)
    return 240 - (temperatureThreshold / max) * 240
  })

  async function loadInitialData() {
    try {
      const [machinesResponse, sensorResponse, alertsResponse] = await Promise.all([
        apiService.getMachines(),
        apiService.getSensorData(1600),
        apiService.getAlerts(500, false)
      ])
      machines.value = machinesResponse
      sensorData.value = sensorResponse
      alerts.value = alertsResponse
      if (!selectedMachineId.value && machines.value.length > 0) selectedMachineId.value = machines.value[0].id
      lastRefreshAt.value = new Date()
    } catch (error) {
      console.error('Failed to load data:', error)
    }
  }

  function upsertAlert(alert) {
    const index = alerts.value.findIndex((a) => a.id === alert.id)
    if (index === -1) alerts.value.unshift(alert)
    else alerts.value.splice(index, 1, { ...alerts.value[index], ...alert })
  }

  function handleMachineUpdate(machine, action) {
    if (action === 'created') machines.value.push(machine)
    else if (action === 'updated') {
      const index = machines.value.findIndex((m) => m.id === machine.id)
      if (index !== -1) machines.value.splice(index, 1, machine)
    } else if (action === 'deleted') machines.value = machines.value.filter((m) => m.id !== machine.id)
  }

  function handleWebSocketMessage(message) {
    lastWsAt.value = Date.now()
    if (message.type === 'sensor_data') {
      sensorData.value.unshift(message.data)
      sensorData.value = sensorData.value.slice(0, SENSOR_LIMIT)
    } else if (message.type === 'alert') {
      upsertAlert(message.data)
    } else if (message.type === 'machine_update') {
      handleMachineUpdate(message.data, message.action)
    }
    lastRefreshAt.value = new Date()
  }

  function startFallbackPolling() {
    if (pollingTimer.value) return
    pollingTimer.value = setInterval(() => {
      loadInitialData()
    }, 10000)
  }

  function stopFallbackPolling() {
    if (!pollingTimer.value) return
    clearInterval(pollingTimer.value)
    pollingTimer.value = null
  }

  function connectWebSocket() {
    websocketService.onMessage((data) => handleWebSocketMessage(data))
    websocketService.onConnect(() => {
      isConnected.value = true
      stopFallbackPolling()
      websocketService.subscribeToAll()
    })
    websocketService.onDisconnect(() => {
      isConnected.value = false
      startFallbackPolling()
    })
    websocketService.connect()
  }

  function machineLabel(machineId) {
    const machine = machineById.value.get(machineId)
    return machine ? `${machine.name} (${machine.location})` : `Machine-${machineId}`
  }

  function severityClass(alert) {
    const level = String(alert.level || '').toUpperCase()
    if (level === 'CRITICAL') return 'critical'
    if (level === 'WARNING') return 'warning'
    return 'info'
  }

  function isCritical(alert) {
    return String(alert.level || '').toUpperCase() === 'CRITICAL'
  }

  async function acknowledgeAlert(alert) {
    try {
      const resolved = await apiService.resolveAlert(alert.id, 'Acknowledged from factory dashboard')
      upsertAlert(resolved)
    } catch (error) {
      console.error('Acknowledge failed:', error)
    }
  }

  function muteAlert(alert) {
    mutedAlerts.value = { ...mutedAlerts.value, [alert.id]: true }
  }

  function assignAlert(alert) {
    assignedAlerts.value = { ...assignedAlerts.value, [alert.id]: roleView.value === 'supervisor' ? 'Supervisor' : 'Operator' }
  }

  function escalateAlert(alert) {
    escalatedAlerts.value = { ...escalatedAlerts.value, [alert.id]: true }
  }

  function refreshNow() {
    loadInitialData()
  }

  function selectMachine(machineId) {
    selectedMachineId.value = machineId
  }

  function setLineSort(key) {
    if (lineSortBy.value === key) lineSortDir.value *= -1
    else {
      lineSortBy.value = key
      lineSortDir.value = 1
    }
  }

  function lineSparklinePoints(lineName) {
    const points = (sensorsByLine.value.get(lineName) || []).slice(0, 18).reverse()
    return seriesToPoints(points, 120, 24)
  }

  function handleChartHover(event, series) {
    const map = {
      temp: trendRows.value.map((r) => Number(r.temperature || 0)),
      vibration: trendRows.value.map((r, i) => Number(r.temperature || 0) * 0.02 + (Number(r.production_count || 0) % 90) * 0.05 + (i % 7) * 0.4),
      output: trendRows.value.map((r) => Number(r.production_count || 0))
    }
    const values = map[series]
    if (!values.length) return
    const rect = event.currentTarget.getBoundingClientRect()
    const x = event.clientX - rect.left
    const idx = Math.min(values.length - 1, Math.max(0, Math.round((x / rect.width) * (values.length - 1))))
    chartHover.value = { series, index: idx, value: Number(values[idx]).toFixed(2) }
  }

  function clearHover() {
    chartHover.value = null
  }

  function formatTime(ts) {
    return ts ? new Date(ts).toLocaleTimeString() : '--'
  }

  function formatTemperature(sensor) {
    if (!sensor || typeof sensor.temperature !== 'number') return '--'
    return `${sensor.temperature.toFixed(1)}C`
  }

  function formatProduction(sensor) {
    if (!sensor || typeof sensor.production_count !== 'number') return '--'
    return String(sensor.production_count)
  }

  function heatClass(temp) {
    const t = Number(temp || 0)
    if (!Number.isFinite(t) || t <= 0) return 'none'
    if (t >= temperatureThreshold) return 'critical'
    if (t >= 70) return 'warning'
    return 'normal'
  }

  function exportCsv() {
    const rows = visibleMachines.value.map((m) => {
      const s = sensorForMachine(m.id)
      return [m.id, m.name, m.location, statusForMachine(m.id), s?.temperature ?? '', s?.production_count ?? '', s?.timestamp || s?.created_at || '']
    })
    const csv = ['machine_id,name,line,status,temperature,production,last_update', ...rows.map((r) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `factory_export_${Date.now()}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  function exportPdf() {
    window.print()
  }

  onMounted(async () => {
    await loadInitialData()
    connectWebSocket()
    clockTicker.value = setInterval(() => {
      nowTs.value = Date.now()
      if (lastRefreshAt.value) clockDriftMs.value = nowTs.value - lastRefreshAt.value.getTime()
      if (lastWsAt.value) wsLatencyMs.value = nowTs.value - lastWsAt.value
    }, 1000)
  })

  onBeforeUnmount(() => {
    websocketService.disconnect()
    stopFallbackPolling()
    if (clockTicker.value) clearInterval(clockTicker.value)
  })

  return {
    activeAlerts,
    activeNav,
    acknowledgeAlert,
    alertLevelFilter,
    assignAlert,
    availability,
    capacityPercent,
    chartHover,
    clearHover,
    clockDriftText,
    connectedMachines,
    energyText,
    escalatedAlerts,
    escalateAlert,
    exportCsv,
    exportPdf,
    filteredAlerts,
    formatProduction,
    formatTemperature,
    formatTime,
    handleChartHover,
    heatClass,
    isConnected,
    isCritical,
    lineFilter,
    lineOptions,
    lineSparklinePoints,
    loadInitialData,
    machineLabel,
    machines,
    mutedAlerts,
    muteAlert,
    navItems: NAV_ITEMS,
    nowText,
    offlineMachines,
    oeeText,
    outputTrendPoints,
    overallStatusClass,
    overallStatusText,
    performance,
    predictiveInsight,
    quality,
    refreshNow,
    roleView,
    searchText,
    selectMachine,
    selectedMachine,
    selectedMachineHistory,
    selectedMachineId,
    sensorForMachine,
    setLineSort,
    severityClass,
    sortMode,
    displayLineSummaries,
    sortedLineSummaries,
    statusCounts,
    statusFilter,
    statusForMachine,
    temperatureBandY,
    temperatureTrendPoints,
    throughputText,
    timeRange,
    utilizationPercent,
    vibrationTrendPoints,
    visibleMachines,
    wsLatencyText
  }
}
