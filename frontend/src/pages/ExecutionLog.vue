<template>
  <div class="page-container">
    <div class="page-header">
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索错误信息 / 命令" clearable style="width: 220px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterTask" placeholder="任务" clearable filterable style="width: 200px;" @change="fetchData">
          <el-option v-for="t in taskOptions" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-select v-model="filterGroup" placeholder="分组" clearable filterable style="width: 150px;" @change="fetchData">
          <el-option v-for="g in groupOptions" :key="g" :label="g" :value="g" />
        </el-select>
        <el-select v-model="filterResult" placeholder="执行结果" clearable style="width: 130px;" @change="fetchData">
          <el-option label="成功" value="SUCCESS" />
          <el-option label="失败" value="FAILED" />
          <el-option label="超时" value="TIMEOUT" />
          <el-option label="中断" value="INTERRUPTED" />
          <el-option label="执行中" value="RUNNING" />
          <el-option label="跳过" value="SKIPPED" />
        </el-select>
        <el-select v-model="filterHost" placeholder="执行机器" clearable style="width: 150px;" @change="fetchData">
          <el-option v-for="h in hosts" :key="h" :label="h" :value="h" />
        </el-select>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table :data="logs" stripe v-loading="loading" @row-click="showDetail" height="100%" style="cursor: pointer;">
        <el-table-column prop="task_name" label="任务" width="140" show-overflow-tooltip />
        <el-table-column prop="execution_host" label="执行机器" width="130" />
        <el-table-column label="结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="resultTagType(row.result)" size="small">{{ row.result_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="90">
          <template #default="{ row }">{{ row.duration != null ? row.duration.toFixed(1) + 's' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="return_code" label="返回码" width="80" align="center">
          <template #default="{ row }">{{ row.return_code ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="command_text" label="命令" min-width="200" show-overflow-tooltip />
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-footer">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <el-dialog v-model="drawerVisible" title="执行日志详情" width="1400px" destroy-on-close>
      <template v-if="selectedLog">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务">{{ selectedLog.task_name }}</el-descriptions-item>
          <el-descriptions-item label="结果">
            <el-tag :type="resultTagType(selectedLog.result)" size="small">{{ selectedLog.result_display }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行机器">{{ selectedLog.execution_host }}</el-descriptions-item>
          <el-descriptions-item label="返回码">{{ selectedLog.return_code ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="开始时间" :span="2">{{ formatTime(selectedLog.start_time) }}</el-descriptions-item>
          <el-descriptions-item label="结束时间" :span="2">{{ formatTime(selectedLog.end_time) }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ selectedLog.duration != null ? selectedLog.duration.toFixed(2) + ' 秒' : '-' }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 16px;">
          <h4 style="margin: 0 0 8px;">完整命令</h4>
          <el-input type="textarea" :model-value="selectedLog.command_text || '-'" :rows="2" readonly />
        </div>

        <div style="margin-top: 16px;">
          <h4 style="margin: 0 0 8px;">输出内容</h4>
          <el-input type="textarea" :model-value="selectedLog.output || '(无输出)'" :rows="8" readonly style="font-family: monospace;" />
        </div>

        <div style="margin-top: 16px;">
          <h4 style="margin: 0 0 8px;">错误信息</h4>
          <el-input
            type="textarea"
            :model-value="selectedLog.error_message || '(无错误)'"
            :rows="4"
            readonly
            style="font-family: monospace;"
            :class="{ 'error-text': selectedLog.error_message }"
          />
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getLogs, getHosts, getTaskOptions, getTaskGroups } from '../api'

const route = useRoute()
const logs = ref([])
const loading = ref(false)
const search = ref('')
const filterResult = ref('')
const filterHost = ref('')
const filterGroup = ref('')
const filterTask = ref(route.query.task ? Number(route.query.task) : '')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const hosts = ref([])
const groupOptions = ref([])
const taskOptions = ref([])

const drawerVisible = ref(false)
const selectedLog = ref(null)

const resultTagType = (result) => {
  const map = { SUCCESS: 'success', FAILED: 'danger', TIMEOUT: 'warning', INTERRUPTED: 'info', RUNNING: '', SKIPPED: 'info' }
  return map[result] || ''
}

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : '-'

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    if (filterResult.value) params.result = filterResult.value
    if (filterHost.value) params.execution_host = filterHost.value
    if (filterGroup.value) params.group = filterGroup.value
    if (filterTask.value) params.task = filterTask.value
    const res = await getLogs(params)
    logs.value = res.data.results || res.data
    total.value = res.data.count || logs.value.length
  } finally { loading.value = false }
}

const showDetail = async (row) => {
  const { data } = await (await import('../api')).getLog(row.id)
  selectedLog.value = data
  drawerVisible.value = true
}

onMounted(async () => {
  try {
    const res = await getHosts()
    const list = res.data.results || res.data
    hosts.value = [...new Set(list.map(h => h.ip))]
  } catch {}
  try {
    const res = await getTaskGroups()
    groupOptions.value = res.data.results || res.data || []
  } catch {}
  try {
    const res = await getTaskOptions()
    taskOptions.value = res.data || []
  } catch {}
  fetchData()
})
</script>

<style scoped>
.page-container {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}
.page-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.filter-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.table-wrapper {
  flex: 1;
  overflow: hidden;
  padding: 0 20px;
}
.page-footer {
  display: flex;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}
.error-text :deep(textarea) {
  color: #ff4d4f;
}
</style>
