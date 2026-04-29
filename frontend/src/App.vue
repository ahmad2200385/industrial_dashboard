<template>
  <div class="factory-shell">
    <header class="topbar">
      <div class="brand-block">
        <h1>SMART FACTORY CONTROL SYSTEM</h1>
        <p>Mission-critical operations view for lines, assets, and alarms</p>
      </div>
      <div class="top-status-grid">
        <div class="top-metric">
          <span class="label">Global Status</span>
          <strong :class="overallStatusClass">{{ overallStatusText }}</strong>
        </div>
        <div class="top-metric">
          <span class="label">Connection</span>
          <strong :class="isConnected ? 'ok' : 'critical'">
            <span class="live-dot" :class="{ offline: !isConnected }"></span>
            {{ isConnected ? 'WebSocket Live' : 'Fallback Polling' }}
          </strong>
        </div>
        <div class="top-metric">
          <span class="label">Latency</span>
          <strong class="mono">{{ wsLatencyText }}</strong>
        </div>
        <div class="top-metric">
          <span class="label">Time Sync</span>
          <strong class="info mono">{{ nowText }} | drift {{ clockDriftText }}</strong>
        </div>
      </div>
    </header>

    <div class="body-grid">
      <nav class="left-nav">
        <button
          v-for="item in navItems"
          :key="item.id"
          type="button"
          class="nav-item"
          :class="{ active: activeNav === item.id }"
          @click="activeNav = item.id"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <main class="content-area">
        <section class="sticky-filters">
          <div class="filter-grid">
            <label>
              <span>Line</span>
              <select v-model="lineFilter">
                <option value="all">All Lines</option>
                <option v-for="line in lineOptions" :key="line" :value="line">{{ line }}</option>
              </select>
            </label>
            <label>
              <span>Machine</span>
              <input v-model="searchText" type="text" placeholder="ID or Name" />
            </label>
            <label>
              <span>Status</span>
              <select v-model="statusFilter">
                <option value="all">All</option>
                <option value="normal">Normal</option>
                <option value="warning">Warning</option>
                <option value="error">Critical</option>
                <option value="no-data">No Data</option>
              </select>
            </label>
            <label>
              <span>Time Range</span>
              <select v-model="timeRange">
                <option value="5m">Last 5 min</option>
                <option value="1h">Last 1h</option>
                <option value="24h">Last 24h</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            <label>
              <span>Role</span>
              <select v-model="roleView">
                <option value="operator">Operator</option>
                <option value="supervisor">Supervisor</option>
              </select>
            </label>
            <label>
              <span>Sort</span>
              <select v-model="sortMode">
                <option value="priority">Priority</option>
                <option value="temp">Temperature</option>
                <option value="name">Machine Name</option>
              </select>
            </label>
          </div>
          <div class="filter-actions">
            <button type="button" class="btn" @click="refreshNow">Refresh</button>
            <button type="button" class="btn" @click="exportCsv">Export CSV</button>
            <button type="button" class="btn" @click="exportPdf">Export PDF</button>
          </div>
        </section>

        <section v-show="activeNav === 'overview' || activeNav === 'analytics'" class="kpi-strip">
          <article class="data-module">
            <span>OEE</span>
            <strong class="mono">{{ oeeText }}</strong>
            <small :title="`Availability ${availability.toFixed(1)}%, Performance ${performance.toFixed(1)}%, Quality ${quality.toFixed(1)}%`">
              A {{ availability.toFixed(1) }} | P {{ performance.toFixed(1) }} | Q {{ quality.toFixed(1) }}
            </small>
          </article>
          <article class="data-module">
            <span>Uptime</span>
            <strong class="mono ok">{{ uptimeText }}</strong>
            <small>{{ connectedMachines }}/{{ machines.length }} assets connected</small>
          </article>
          <article class="data-module">
            <span>Throughput</span>
            <strong class="mono info">{{ throughputText }}</strong>
            <small>Units/hour estimated</small>
          </article>
          <article class="data-module">
            <span>Energy</span>
            <strong class="mono">{{ energyText }}</strong>
            <small>kWh normalized load</small>
          </article>
        </section>

        <section v-show="activeNav === 'overview'" class="module-grid">
          <article class="module status-module">
            <div class="module-head">
              <h3>Live System Status</h3>
              <span class="badge info">{{ connectedMachines }} ONLINE / {{ offlineMachines }} OFFLINE</span>
            </div>
            <div class="status-list">
              <div class="status-pill ok">Normal {{ statusCounts.normal }}</div>
              <div class="status-pill warn">Warning {{ statusCounts.warning }}</div>
              <div class="status-pill crit">Critical {{ statusCounts.error }}</div>
              <div class="status-pill info">No Data {{ statusCounts['no-data'] }}</div>
            </div>
            <div class="util-block">
              <div class="bar-label"><span>Utilization</span><span class="mono">{{ utilizationPercent }}%</span></div>
              <div class="bar"><i :style="{ width: `${utilizationPercent}%` }"></i></div>
              <div class="bar-label"><span>Capacity</span><span class="mono">{{ capacityPercent }}%</span></div>
              <div class="bar danger"><i :style="{ width: `${capacityPercent}%` }"></i></div>
            </div>
          </article>

          <article class="module alerts-module">
            <div class="module-head">
              <h3>Alerts</h3>
              <span class="badge warn">{{ filteredAlerts.length }} active</span>
            </div>
            <div class="alert-filters">
              <select v-model="alertLevelFilter">
                <option value="all">All Levels</option>
                <option value="CRITICAL">Critical</option>
                <option value="WARNING">Warning</option>
                <option value="INFO">Info</option>
              </select>
            </div>
            <div class="alerts-scroll">
              <div
                v-for="alert in filteredAlerts.slice(0, 18)"
                :key="alert.id"
                class="alert-row"
                :class="severityClass(alert)"
              >
                <div class="alert-main" :title="alert.message">
                  <strong>
                    <span class="pulse" v-if="isCritical(alert)"></span>
                    {{ alert.level }}
                  </strong>
                  <span>{{ machineLabel(alert.machine_id) }}</span>
                  <p>{{ alert.message }}</p>
                </div>
                <div class="alert-actions">
                  <button type="button" @click="acknowledgeAlert(alert)">Ack</button>
                  <button type="button" @click="muteAlert(alert)">Mute</button>
                  <button type="button" @click="assignAlert(alert)">Assign</button>
                  <button type="button" @click="escalateAlert(alert)">Escalate</button>
                </div>
              </div>
              <div v-if="filteredAlerts.length === 0" class="empty">No active alerts in this filter.</div>
            </div>
          </article>
        </section>

        <section v-show="activeNav === 'overview' || activeNav === 'lines'" class="module table-module">
          <div class="module-head">
            <h3>Line Performance</h3>
            <span class="badge info">Click a line to drill into machines</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th @click="setLineSort('line')">Line</th>
                  <th @click="setLineSort('total')">Machines</th>
                  <th @click="setLineSort('normal')">Healthy</th>
                  <th @click="setLineSort('warning')">Warn</th>
                  <th @click="setLineSort('error')">Critical</th>
                  <th @click="setLineSort('avgTemp')">Avg Temp</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="line in displayLineSummaries"
                  :key="line.line"
                  :class="{ active: lineFilter === line.line }"
                  @click="lineFilter = lineFilter === line.line ? 'all' : line.line"
                >
                  <td>{{ line.line }}</td>
                  <td class="mono">{{ line.total }}</td>
                  <td class="mono ok">{{ line.normal }}</td>
                  <td class="mono warn">{{ line.warning }}</td>
                  <td class="mono crit">{{ line.error }}</td>
                  <td class="mono">{{ line.avgTemp }}</td>
                  <td>
                    <svg class="sparkline" viewBox="0 0 120 24" role="img" aria-label="line trend">
                      <polyline :points="lineSparklinePoints(line.line)" />
                    </svg>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-show="activeNav === 'analytics'" class="module charts-module">
          <div class="module-head">
            <h3>Real-Time Trends</h3>
            <span class="badge info">Threshold bands + telemetry hover</span>
          </div>
          <div class="chart-grid">
            <div class="chart-block">
              <h4>Temperature Trend</h4>
              <svg viewBox="0 0 760 240" class="trend-chart" @mousemove="handleChartHover($event, 'temp')" @mouseleave="clearHover">
                <rect x="0" y="0" width="760" height="240" class="band-safe" />
                <rect x="0" :y="temperatureBandY" width="760" :height="240 - temperatureBandY" class="band-danger" />
                <polyline :points="temperatureTrendPoints" class="trend-line temp" />
              </svg>
            </div>
            <div class="chart-block">
              <h4>Vibration Trend</h4>
              <svg viewBox="0 0 760 240" class="trend-chart" @mousemove="handleChartHover($event, 'vibration')" @mouseleave="clearHover">
                <rect x="0" y="0" width="760" height="240" class="band-safe" />
                <rect x="0" y="165" width="760" height="75" class="band-danger" />
                <polyline :points="vibrationTrendPoints" class="trend-line warn" />
              </svg>
            </div>
            <div class="chart-block full">
              <h4>Output Trend</h4>
              <svg viewBox="0 0 760 220" class="trend-chart" @mousemove="handleChartHover($event, 'output')" @mouseleave="clearHover">
                <rect x="0" y="0" width="760" height="220" class="band-safe" />
                <polyline :points="outputTrendPoints" class="trend-line info" />
              </svg>
            </div>
          </div>
          <div v-if="chartHover" class="chart-tooltip mono">
            {{ chartHover.series }} @ {{ chartHover.index }}: {{ chartHover.value }}
          </div>
        </section>

        <section v-show="activeNav === 'overview'" class="module split-module">
          <div>
            <div class="module-head">
              <h3>Temperature Heatmap</h3>
              <span class="badge info">Machine temperature distribution</span>
            </div>
            <div class="heatmap-grid">
              <button
                v-for="machine in visibleMachines.slice(0, 60)"
                :key="machine.id"
                type="button"
                class="heat-cell"
                :class="heatClass(sensorForMachine(machine.id)?.temperature)"
                :title="`${machine.name} | ${formatTemperature(sensorForMachine(machine.id))}`"
                @click="selectMachine(machine.id)"
              >
                {{ machine.id }}
              </button>
            </div>
          </div>
          <div>
            <div class="module-head">
              <h3>Alert Timeline</h3>
              <span class="badge warn">Newest first</span>
            </div>
            <div class="timeline">
              <div v-for="alert in activeAlerts.slice(0, 16)" :key="`tl-${alert.id}`" class="timeline-item" :class="severityClass(alert)">
                <i></i>
                <div>
                  <strong>{{ alert.level }}</strong>
                  <p>{{ machineLabel(alert.machine_id) }} | {{ alert.message }}</p>
                  <small class="mono">{{ formatTime(alert.created_at || alert.timestamp) }}</small>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="predictiveInsight && (activeNav === 'overview' || activeNav === 'analytics')" class="module predictive">
          <strong class="warn">Predictive Insight</strong>
          <span>{{ predictiveInsight }}</span>
        </section>

        <section v-show="activeNav === 'lines'" class="module split-module">
          <div>
            <div class="module-head">
              <h3>Line Health Summary</h3>
              <span class="badge info">Grouped by production line</span>
            </div>
            <div class="status-list">
              <div class="status-pill ok">Normal {{ statusCounts.normal }}</div>
              <div class="status-pill warn">Warning {{ statusCounts.warning }}</div>
              <div class="status-pill crit">Critical {{ statusCounts.error }}</div>
              <div class="status-pill info">No Data {{ statusCounts['no-data'] }}</div>
            </div>
            <div class="util-block">
              <div class="bar-label"><span>Utilization</span><span class="mono">{{ utilizationPercent }}%</span></div>
              <div class="bar"><i :style="{ width: `${utilizationPercent}%` }"></i></div>
            </div>
          </div>
          <div>
            <div class="module-head">
              <h3>Temperature Heatmap</h3>
              <span class="badge info">Top 60 machines</span>
            </div>
            <div class="heatmap-grid">
              <button
                v-for="machine in visibleMachines.slice(0, 60)"
                :key="`line-${machine.id}`"
                type="button"
                class="heat-cell"
                :class="heatClass(sensorForMachine(machine.id)?.temperature)"
                :title="`${machine.name} | ${formatTemperature(sensorForMachine(machine.id))}`"
                @click="selectMachine(machine.id)"
              >
                {{ machine.id }}
              </button>
            </div>
          </div>
        </section>

        <section v-show="activeNav === 'machines'" class="module table-module">
          <div class="module-head">
            <h3>Machine Fleet</h3>
            <span class="badge info">{{ visibleMachines.length }} visible machines</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Line</th>
                  <th>Status</th>
                  <th>Temperature</th>
                  <th>Output</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="machine in visibleMachines" :key="`m-${machine.id}`" @click="selectMachine(machine.id)">
                  <td class="mono">{{ machine.id }}</td>
                  <td>{{ machine.name }}</td>
                  <td>{{ machine.location }}</td>
                  <td :class="statusForMachine(machine.id)">{{ statusForMachine(machine.id) }}</td>
                  <td class="mono">{{ formatTemperature(sensorForMachine(machine.id)) }}</td>
                  <td class="mono">{{ formatProduction(sensorForMachine(machine.id)) }}</td>
                  <td class="mono">{{ formatTime(sensorForMachine(machine.id)?.timestamp || sensorForMachine(machine.id)?.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-show="activeNav === 'alerts'" class="module split-module">
          <article class="module alerts-module">
            <div class="module-head">
              <h3>Alerts Queue</h3>
              <span class="badge warn">{{ filteredAlerts.length }} active</span>
            </div>
            <div class="alert-filters">
              <select v-model="alertLevelFilter">
                <option value="all">All Levels</option>
                <option value="CRITICAL">Critical</option>
                <option value="WARNING">Warning</option>
                <option value="INFO">Info</option>
              </select>
            </div>
            <div class="alerts-scroll">
              <div
                v-for="alert in filteredAlerts.slice(0, 24)"
                :key="`alerts-tab-${alert.id}`"
                class="alert-row"
                :class="severityClass(alert)"
              >
                <div class="alert-main" :title="alert.message">
                  <strong>
                    <span class="pulse" v-if="isCritical(alert)"></span>
                    {{ alert.level }}
                  </strong>
                  <span>{{ machineLabel(alert.machine_id) }}</span>
                  <p>{{ alert.message }}</p>
                </div>
                <div class="alert-actions">
                  <button type="button" @click="acknowledgeAlert(alert)">Ack</button>
                  <button type="button" @click="muteAlert(alert)">Mute</button>
                  <button type="button" @click="assignAlert(alert)">Assign</button>
                  <button type="button" @click="escalateAlert(alert)">Escalate</button>
                </div>
              </div>
              <div v-if="filteredAlerts.length === 0" class="empty">No active alerts in this filter.</div>
            </div>
          </article>
          <article class="module">
            <div class="module-head">
              <h3>Alert Timeline</h3>
              <span class="badge info">Latest events</span>
            </div>
            <div class="timeline">
              <div v-for="alert in activeAlerts.slice(0, 24)" :key="`alert-view-${alert.id}`" class="timeline-item" :class="severityClass(alert)">
                <i></i>
                <div>
                  <strong>{{ alert.level }}</strong>
                  <p>{{ machineLabel(alert.machine_id) }} | {{ alert.message }}</p>
                  <small class="mono">{{ formatTime(alert.created_at || alert.timestamp) }}</small>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section v-show="activeNav === 'maintenance'" class="module split-module">
          <article class="module">
            <div class="module-head">
              <h3>Maintenance Queue</h3>
              <span class="badge warn">{{ statusCounts.error + statusCounts.warning }} machines need attention</span>
            </div>
            <div class="timeline">
              <div
                v-for="machine in visibleMachines.filter((m) => ['error', 'warning'].includes(statusForMachine(m.id))).slice(0, 20)"
                :key="`maint-${machine.id}`"
                class="timeline-item"
                :class="statusForMachine(machine.id)"
              >
                <i></i>
                <div>
                  <strong>{{ machine.name }}</strong>
                  <p>{{ machine.location }} | {{ statusForMachine(machine.id).toUpperCase() }}</p>
                  <small class="mono">Temp {{ formatTemperature(sensorForMachine(machine.id)) }} | Output {{ formatProduction(sensorForMachine(machine.id)) }}</small>
                </div>
              </div>
              <div v-if="visibleMachines.filter((m) => ['error', 'warning'].includes(statusForMachine(m.id))).length === 0" class="empty">
                No machines currently require maintenance action.
              </div>
            </div>
          </article>
          <article class="module">
            <div class="module-head">
              <h3>Service Notes</h3>
              <span class="badge info">Operations checklist</span>
            </div>
            <ul class="maintenance-list">
              <li>Inspect critical machines first and acknowledge alerts.</li>
              <li>Validate cooling path for units above threshold.</li>
              <li>Review production drop trends before restart.</li>
              <li>Confirm sensor heartbeat and WebSocket link status.</li>
              <li>Export latest incident data before shift handoff.</li>
            </ul>
          </article>
        </section>
      </main>
    </div>

    <aside class="machine-drawer" :class="{ open: !!selectedMachine }">
      <div class="drawer-head">
        <h3>{{ selectedMachine ? selectedMachine.name : 'Machine Detail' }}</h3>
        <button type="button" @click="selectedMachineId = null"><i class="fas fa-times"></i></button>
      </div>
      <div v-if="selectedMachine" class="drawer-content">
        <div class="drawer-grid">
          <div class="module-mini"><span>Status</span><strong :class="statusForMachine(selectedMachine.id)">{{ statusForMachine(selectedMachine.id) }}</strong></div>
          <div class="module-mini"><span>Temperature</span><strong class="mono">{{ formatTemperature(sensorForMachine(selectedMachine.id)) }}</strong></div>
          <div class="module-mini"><span>Output</span><strong class="mono">{{ formatProduction(sensorForMachine(selectedMachine.id)) }}</strong></div>
          <div class="module-mini"><span>Updated</span><strong class="mono">{{ formatTime(sensorForMachine(selectedMachine.id)?.timestamp || sensorForMachine(selectedMachine.id)?.created_at) }}</strong></div>
        </div>
        <h4>Telemetry Snapshot</h4>
        <ul>
          <li v-for="row in selectedMachineHistory.slice(0, 10)" :key="row.id" class="mono">
            {{ formatTime(row.timestamp || row.created_at) }} | T={{ Number(row.temperature || 0).toFixed(1) }} | S={{ row.status }} | P={{ row.production_count }}
          </li>
        </ul>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { useFactoryDashboard } from './composables/useFactoryDashboard.js'

const {
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
  machineLabel,
  machines,
  muteAlert,
  navItems,
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
} = useFactoryDashboard()
</script>

<style scoped>
.factory-shell { background: #090f1a; color: #e2ebf7; min-height: 100vh; }
.topbar { position: sticky; top: 0; z-index: 40; background: linear-gradient(180deg, #111a2b 0%, #0b1422 70%); border-bottom: 1px solid #2a3f5e; padding: 0.62rem 0.85rem; display: flex; gap: 1rem; justify-content: space-between; align-items: center; box-shadow: 0 8px 24px rgba(4, 9, 18, 0.45); }
.brand-block h1 { margin: 0; font-size: 1.04rem; font-weight: 700; letter-spacing: 0.11em; color: #f2f7ff; }
.brand-block p { margin: 0.15rem 0 0; font-size: 0.75rem; color: #a3b6cd; line-height: 1.4; }
.top-status-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.55rem; min-width: 62%; }
.top-metric { border: 1px solid #27405e; background: linear-gradient(180deg, #0f1a2a, #0c1624); padding: 0.42rem 0.5rem; border-radius: 6px; }
.label { display: block; text-transform: uppercase; font-size: 0.6rem; font-weight: 600; letter-spacing: 0.1em; color: #88a0bb; margin-bottom: 0.2rem; }
.top-metric strong { font-size: 0.83rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.25rem; }
.ok { color: #37d98a; }
.warn { color: #ffd166; }
.critical, .crit { color: #ff6b68; }
.info { color: #6fb7ff; }
.live-dot { width: 8px; height: 8px; border-radius: 1px; background: #37d98a; display: inline-block; box-shadow: 0 0 10px rgba(55, 217, 138, 0.65); }
.live-dot.offline { background: #ff6b68; box-shadow: 0 0 10px rgba(255, 107, 104, 0.6); }
.body-grid { display: grid; grid-template-columns: 188px 1fr; min-height: calc(100vh - 78px); }
.left-nav { border-right: 1px solid #23344d; background: #0b1321; padding: 0.45rem; display: flex; flex-direction: column; gap: 0.28rem; }
.nav-item { border: 1px solid #233650; background: #101b2d; color: #b5c6db; text-align: left; padding: 0.45rem; display: flex; gap: 0.45rem; align-items: center; font-size: 0.78rem; font-weight: 500; cursor: pointer; border-radius: 6px; transition: all 0.15s ease; }
.nav-item.active, .nav-item:hover { border-color: #39608a; color: #f0f7ff; background: #172a43; }
.content-area { padding: 0.5rem; display: flex; flex-direction: column; gap: 0.46rem; }
.sticky-filters { position: sticky; top: 78px; z-index: 30; border: 1px solid #26405f; background: linear-gradient(180deg, #0e1a2c, #0c1728); padding: 0.4rem; display: flex; justify-content: space-between; gap: 0.5rem; border-radius: 8px; }
.filter-grid { display: grid; grid-template-columns: repeat(6, minmax(118px, 1fr)); gap: 0.35rem; width: 100%; }
.filter-grid label { display: flex; flex-direction: column; gap: 0.14rem; }
.filter-grid span { font-size: 0.6rem; font-weight: 600; color: #8fa7c2; text-transform: uppercase; letter-spacing: 0.1em; }
.filter-grid input, .filter-grid select { background: #0a1422; border: 1px solid #345174; color: #e2ebf7; padding: 0.24rem 0.34rem; font-size: 0.76rem; border-radius: 4px; }
.filter-actions { display: flex; gap: 0.3rem; align-items: end; }
.btn { background: linear-gradient(180deg, #183152, #142743); border: 1px solid #3a5f89; color: #d8e9ff; font-size: 0.72rem; font-weight: 600; padding: 0.28rem 0.56rem; cursor: pointer; border-radius: 5px; transition: all 0.15s ease; }
.btn:hover { filter: brightness(1.07); }
.kpi-strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 0.38rem; }
.data-module { border: 1px solid #284564; background: linear-gradient(180deg, #111f34, #0d1a2c); padding: 0.5rem; display: flex; flex-direction: column; gap: 0.17rem; border-radius: 8px; }
.data-module span { font-size: 0.62rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #8ea5be; }
.data-module strong { font-size: 1.08rem; font-weight: 700; color: #f2f7ff; }
.data-module small { font-size: 0.68rem; color: #a4b9d1; line-height: 1.4; }
.module-grid { display: grid; grid-template-columns: 1fr 1.35fr; gap: 0.45rem; }
.module { border: 1px solid #27445f; background: linear-gradient(180deg, #0f1c30, #0c1727); padding: 0.46rem; border-radius: 8px; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.02); }
.module-head { display: flex; justify-content: space-between; align-items: center; gap: 0.4rem; margin-bottom: 0.37rem; }
.module-head h3 { margin: 0; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; color: #edf4ff; }
.badge { border: 1px solid #3a5f84; padding: 0.14rem 0.35rem; font-size: 0.64rem; font-weight: 600; text-transform: uppercase; border-radius: 999px; }
.status-list { display: flex; gap: 0.24rem; flex-wrap: wrap; }
.status-pill { border: 1px solid; padding: 0.16rem 0.36rem; font-size: 0.69rem; font-weight: 600; border-radius: 999px; }
.status-pill.ok { border-color: #1f7a50; color: #37d98a; }
.status-pill.warn { border-color: #7f6722; color: #ffd166; }
.status-pill.crit { border-color: #8c2f2f; color: #ff6b68; }
.status-pill.info { border-color: #366189; color: #6fb7ff; }
.util-block { margin-top: 0.48rem; display: grid; gap: 0.24rem; }
.bar-label { display: flex; justify-content: space-between; font-size: 0.69rem; font-weight: 500; color: #9bb1c9; }
.bar { height: 10px; border: 1px solid #2d4767; background: #091221; border-radius: 999px; overflow: hidden; }
.bar i { display: block; height: 100%; background: linear-gradient(90deg, #209c62, #37d98a); }
.bar.danger i { background: linear-gradient(90deg, #d9a745, #ff6b68); }
.alert-filters select { background: #0a1422; border: 1px solid #345174; color: #e2ebf7; font-size: 0.73rem; padding: 0.16rem 0.28rem; border-radius: 4px; }
.alerts-scroll { max-height: 280px; overflow: auto; display: grid; gap: 0.33rem; }
.alert-row { border: 1px solid #305171; background: #0a1422; padding: 0.34rem; display: grid; grid-template-columns: 1fr auto; gap: 0.34rem; border-radius: 6px; }
.alert-row.warning { border-left: 3px solid #ffd166; }
.alert-row.critical { border-left: 3px solid #ff6b68; }
.alert-row.info { border-left: 3px solid #6fb7ff; }
.alert-main strong { font-size: 0.72rem; font-weight: 700; display: flex; align-items: center; gap: 0.2rem; }
.alert-main span { font-size: 0.69rem; color: #9eb4cc; font-weight: 500; }
.alert-main p { margin: 0.2rem 0 0; font-size: 0.75rem; line-height: 1.45; color: #d3e2f3; }
.alert-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 0.18rem; }
.alert-actions button { background: #152b47; border: 1px solid #3a5f89; color: #d8e9ff; font-size: 0.63rem; font-weight: 600; cursor: pointer; padding: 0.16rem 0.28rem; border-radius: 4px; }
.pulse { width: 7px; height: 7px; background: #ff6b68; display: inline-block; animation: pulse 1.2s infinite; }
@keyframes pulse { 50% { opacity: 0.35; } }
.table-wrap { overflow: auto; border: 1px solid #27445f; border-radius: 6px; }
table { width: 100%; border-collapse: collapse; min-width: 900px; }
th, td { padding: 0.3rem 0.34rem; border-bottom: 1px solid #203753; font-size: 0.75rem; }
th { text-transform: uppercase; letter-spacing: 0.07em; font-size: 0.62rem; font-weight: 700; color: #9bb1c9; cursor: pointer; background: #112036; }
tbody tr { cursor: pointer; }
tbody tr:hover { background: #142946; }
tbody tr.active { background: #18385f; }
.sparkline { width: 120px; height: 24px; }
.sparkline polyline { fill: none; stroke: #6fb7ff; stroke-width: 1.5; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.42rem; }
.chart-block { border: 1px solid #27445f; background: #08111f; padding: 0.28rem; border-radius: 6px; }
.chart-block.full { grid-column: 1 / -1; }
.chart-block h4 { margin: 0 0 0.22rem; font-size: 0.69rem; font-weight: 700; color: #a6bdd6; text-transform: uppercase; letter-spacing: 0.08em; }
.trend-chart { width: 100%; height: 190px; border: 1px solid #1c2f48; background-image: linear-gradient(to bottom, rgba(72, 104, 137, 0.18) 1px, transparent 1px), linear-gradient(to right, rgba(72, 104, 137, 0.14) 1px, transparent 1px); background-size: 100% 24px, 48px 100%; }
.band-safe { fill: rgba(55, 217, 138, 0.06); }
.band-danger { fill: rgba(255, 107, 104, 0.12); }
.trend-line { fill: none; stroke-width: 2; }
.trend-line.temp { stroke: #6fb7ff; }
.trend-line.warn { stroke: #ffd166; }
.trend-line.info { stroke: #8ec9ff; }
.chart-tooltip { font-size: 0.71rem; color: #c9dcf0; }
.split-module { display: grid; grid-template-columns: 1fr 1fr; gap: 0.44rem; }
.heatmap-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(44px, 1fr)); gap: 0.22rem; }
.heat-cell { border: 1px solid #355574; background: #11233c; color: #e2ebf7; font-size: 0.66rem; font-weight: 600; padding: 0.24rem 0; cursor: pointer; border-radius: 4px; }
.heat-cell.normal { background: rgba(55, 217, 138, 0.15); border-color: #217a4f; }
.heat-cell.warning { background: rgba(255, 209, 102, 0.17); border-color: #836923; }
.heat-cell.critical { background: rgba(255, 107, 104, 0.2); border-color: #8c2f2f; }
.heat-cell.none { background: #0d192c; border-color: #2a4562; color: #90a7bf; }
.timeline { max-height: 252px; overflow: auto; display: grid; gap: 0.31rem; }
.timeline-item { display: grid; grid-template-columns: 11px 1fr; gap: 0.28rem; }
.timeline-item i { width: 8px; height: 8px; margin-top: 0.2rem; background: #6fb7ff; }
.timeline-item.warning i { background: #ffd166; }
.timeline-item.critical i { background: #ff6b68; }
.timeline-item.error i { background: #ff6b68; }
.timeline-item strong { font-size: 0.71rem; }
.timeline-item p { margin: 0.1rem 0; font-size: 0.72rem; line-height: 1.4; color: #c2d5ea; }
.timeline-item small { font-size: 0.66rem; color: #95abc3; }
.maintenance-list { margin: 0; padding-left: 1rem; display: grid; gap: 0.4rem; color: #c8d8ea; font-size: 0.76rem; line-height: 1.5; }
.predictive { border-color: #836923; background: rgba(255, 209, 102, 0.08); display: flex; gap: 0.46rem; align-items: center; }
.empty { color: #95abc3; font-size: 0.73rem; }
.machine-drawer { position: fixed; top: 78px; right: 0; width: 0; overflow: hidden; height: calc(100vh - 78px); background: #0a1322; border-left: 1px solid #27445f; transition: width 0.2s ease; z-index: 50; }
.machine-drawer.open { width: 340px; }
.drawer-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #27445f; padding: 0.44rem; }
.drawer-head h3 { margin: 0; font-size: 0.84rem; font-weight: 700; }
.drawer-head button { background: #152b47; border: 1px solid #3a5f89; color: #d8e9ff; border-radius: 4px; }
.drawer-content { padding: 0.44rem; }
.drawer-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.25rem; }
.module-mini { border: 1px solid #27445f; padding: 0.28rem; display: flex; flex-direction: column; gap: 0.16rem; border-radius: 6px; }
.module-mini span { font-size: 0.62rem; color: #8ea5be; font-weight: 600; text-transform: uppercase; }
.module-mini strong { font-size: 0.79rem; }
.drawer-content h4 { margin: 0.48rem 0 0.24rem; font-size: 0.75rem; color: #a6bdd6; text-transform: uppercase; letter-spacing: 0.07em; }
.drawer-content ul { margin: 0; padding-left: 0; list-style: none; max-height: 360px; overflow: auto; }
.drawer-content li { padding: 0.2rem 0; border-bottom: 1px solid #203753; font-size: 0.69rem; color: #c2d5ea; }
.mono { font-family: 'IBM Plex Mono', 'Consolas', monospace; }
@media (max-width: 1300px) { .filter-grid { grid-template-columns: repeat(3, minmax(120px, 1fr)); } .module-grid, .split-module { grid-template-columns: 1fr; } .chart-grid { grid-template-columns: 1fr; } }
@media (max-width: 980px) { .body-grid { grid-template-columns: 1fr; } .left-nav { display: grid; grid-template-columns: repeat(3, 1fr); border-right: none; border-bottom: 1px solid #23344d; } .top-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .sticky-filters { position: static; } .machine-drawer.open { width: 100%; } }
</style>


