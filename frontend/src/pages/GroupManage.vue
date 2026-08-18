<template>
  <div class="page-container">
    <div class="page-header">
      <div class="filter-bar">
        <el-input v-model="search" placeholder="搜索分组名称" clearable style="width: 250px;" @clear="fetchData" @keyup.enter="fetchData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <div class="action-bar">
        <el-button type="primary" @click="openDialog(null)"><el-icon><Plus /></el-icon> 添加分组</el-button>
      </div>
    </div>

    <div class="table-wrapper">
      <el-table :data="groups" stripe v-loading="loading" height="100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="分组名称" min-width="160" />
        <el-table-column label="权限" min-width="300">
          <template #default="{ row }">
            <template v-if="row.permissions_display && row.permissions_display.length">
              <el-tag v-for="p in row.permissions_display.slice(0, 5)" :key="p" size="small" style="margin-right: 4px;">{{ p }}</el-tag>
              <span v-if="row.permissions_display.length > 5" style="color: #909399; font-size: 12px;">等 {{ row.permissions_display.length }} 项</span>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="page-footer">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑分组' : '添加分组'" width="560px" destroy-on-close top="6vh">
      <el-form :model="form" label-width="90px">
        <el-form-item label="分组名称" required>
          <el-input v-model="form.name" placeholder="如 报表查看组" />
        </el-form-item>
        <el-form-item label="权限选择">
          <el-select
            v-model="form.permissions"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%;"
            placeholder="选择权限"
          >
            <el-option-group v-for="g in permGroups" :key="g.label" :label="g.label">
              <el-option v-for="p in g.options" :key="p.id" :label="p.label" :value="p.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getGroups, createGroup, updateGroup, deleteGroup, getPermissions } from '../api'

const groups = ref([])
const allPermissions = ref([])
const loading = ref(false)
const search = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dialogVisible = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ name: '', permissions: [] })

// 权限按 app 分组，供下拉选择
const permGroups = computed(() => {
  const map = {}
  for (const p of allPermissions.value) {
    const ct = p.content_type || 'other'
    if (!map[ct]) map[ct] = []
    map[ct].push({ id: p.id, label: p.name })
  }
  return Object.entries(map).map(([label, options]) => ({ label, options }))
})

const fetchPermissions = async () => {
  try {
    const res = await getPermissions({ page_size: 10000 })
    allPermissions.value = res.data.results || res.data || []
  } catch {}
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (search.value) params.search = search.value
    const res = await getGroups(params)
    groups.value = res.data.results || res.data
    total.value = res.data.count || groups.value.length
  } finally { loading.value = false }
}

const openDialog = (group) => {
  if (group) {
    editing.value = group
    form.value = { name: group.name, permissions: group.permissions || [] }
  } else {
    editing.value = null
    form.value = { name: '', permissions: [] }
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.name) return ElMessage.warning('请输入分组名称')
  saving.value = true
  try {
    if (editing.value) {
      await updateGroup(editing.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await createGroup(form.value)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    const err = e.response?.data
    ElMessage.error(err?.name?.[0] || err?.detail || '保存失败')
  } finally { saving.value = false }
}

const handleDelete = async (row) => {
  try {
    await deleteGroup(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(() => { fetchPermissions(); fetchData() })
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
.filter-bar, .action-bar {
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
</style>