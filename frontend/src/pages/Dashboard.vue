<template>
  <div class="dashboard-container" style="padding: 10px;">
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card shadow="hover" class="clickable-card" @click="$router.push('/tasks')">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6f7ff;">
              <el-icon :size="28" color="#1890ff"><Setting /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalTasks }}</div>
              <div class="stat-label">任务总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="clickable-card" @click="$router.push('/tasks?is_active=true')">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f6ffed;">
              <el-icon :size="28" color="#52c41a"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.activeTasks }}</div>
              <div class="stat-label">已启用</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="clickable-card" @click="$router.push('/hosts')">
          <div class="stat-card">
            <div class="stat-icon" style="background: #fff7e6;">
              <el-icon :size="28" color="#fa8c16"><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.hostCount }}</div>
              <div class="stat-label">执行机器</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="clickable-card" @click="$router.push('/databases')">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f9f0ff;">
              <el-icon :size="28" color="#722ed1"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.dbCount }}</div>
              <div class="stat-label">数据库配置</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="clickable-card" @click="$router.push('/logs')" style="cursor: pointer;">
          <template #header>
            <span>最近执行日志</span>
          </template>
          <el-table :data="recentLogs" size="small" stripe style="width: 100%;" highlight-current-row>
            <el-table-column prop="task_name" label="任务" min-width="180" show-overflow-tooltip />
            <el-table-column prop="execution_host" label="执行机器" width="120" show-overflow-tooltip />
            <el-table-column prop="result_display" label="结果" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="resultTagType(row.result)" size="small">{{ row.result_display }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="70" align="center">
              <template #default="{ row }">
                {{ row.duration ? row.duration.toFixed(1) + 's' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="时间" width="170">
              <template #default="{ row }">
                {{ formatTime(row.start_time) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>任务类型分布</span>
          </template>
          <div style="padding: 10px 0;">
            <el-row :gutter="12" style="margin-bottom: 16px;">
              <el-col :span="12">
                <el-card shadow="never" class="type-card clickable-card" @click="$router.push('/tasks?task_type=python')" style="border-left: 4px solid #1890ff;">
                  <div class="type-info">
                    <div class="type-label">Python 脚本任务</div>
                    <div class="type-value" style="color: #1890ff;">{{ stats.pythonTasks }}</div>
                  </div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card shadow="never" class="type-card clickable-card" @click="$router.push('/tasks?task_type=sql')" style="border-left: 4px solid #52c41a;">
                  <div class="type-info">
                    <div class="type-label">SQL 脚本任务</div>
                    <div class="type-value" style="color: #52c41a;">{{ stats.sqlTasks }}</div>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <div style="margin-top: 16px;">
              <div style="font-weight: 600; margin-bottom: 12px; color: #606266;">任务分组</div>
              <div class="group-tags">
                <el-tag
                  v-for="(g, idx) in groupStats"
                  :key="g.name"
                  :color="groupColors[idx % groupColors.length]"
                  class="group-tag clickable-tag"
                  @click="$router.push('/tasks?group=' + encodeURIComponent(g.name))"
                >
                  {{ g.name }} [{{ g.count }}]
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDashboardStats } from '../api'

const stats = ref({
  totalTasks: 0, activeTasks: 0, pythonTasks: 0, sqlTasks: 0,
  hostCount: 0, dbCount: 0,
})
const recentLogs = ref([])
const groupStats = ref([])

const groupColors = [
  '#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96',
  '#13c2c2', '#fa541c', '#2f54eb', '#a0d911', '#f5222d',
  '#722ed1', '#1890ff', '#52c41a', '#fa8c16', '#eb2f96',
]

const resultTagType = (result) => {
  const map = { SUCCESS: 'success', FAILED: 'danger', TIMEOUT: 'warning', INTERRUPTED: 'info', RUNNING: '' }
  return map[result] || ''
}

const formatTime = (t) => {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}

onMounted(async () => {
  try {
    const { data } = await getDashboardStats()
    stats.value = {
      totalTasks: data.total_tasks,
      activeTasks: data.active_tasks,
      pythonTasks: data.python_tasks,
      sqlTasks: data.sql_tasks,
      hostCount: data.host_count,
      dbCount: data.db_count,
    }
    groupStats.value = data.group_stats
    recentLogs.value = data.recent_logs
  } catch (e) {
    console.error('加载仪表盘数据失败:', e)
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 10px;
  overflow: auto;
  height: 100%;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.clickable-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.clickable-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}
.type-card {
  padding: 12px 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.type-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.type-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.type-label {
  font-size: 14px;
  color: #606266;
}
.type-value {
  font-size: 24px;
  font-weight: 600;
}
.group-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.group-tag {
  cursor: pointer;
  color: #fff !important;
  font-weight: 500;
  font-size: 14px;
  height: 34px;
  line-height: 32px;
  padding: 0 16px;
  border: none !important;
  border-radius: 17px;
  transition: opacity 0.2s, transform 0.15s;
}
.group-tag:hover {
  opacity: 0.85;
  transform: scale(1.05);
}
</style>
