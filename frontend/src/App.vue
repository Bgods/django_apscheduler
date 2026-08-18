<template>
  <router-view />
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 按钮禁用态颜色加深（覆盖 Element Plus 默认浅色禁用样式） */
.el-button.is-disabled,
.el-button.is-disabled.is-plain {
  color: #fff;
  border-color: #909399;
  background-color: #909399;
}
.el-button.is-disabled:hover,
.el-button.is-disabled:focus {
  color: #fff;
  border-color: #909399;
  background-color: #909399;
}
.el-button--primary.is-disabled,
.el-button--primary.is-disabled:hover,
.el-button--primary.is-disabled:focus {
  color: #fff;
  border-color: #337ecc;
  background-color: #337ecc;
}
.el-button--success.is-disabled,
.el-button--success.is-disabled:hover,
.el-button--success.is-disabled:focus {
  color: #fff;
  border-color: #529b2e;
  background-color: #529b2e;
}
.el-button--warning.is-disabled,
.el-button--warning.is-disabled:hover,
.el-button--warning.is-disabled:focus {
  color: #fff;
  border-color: #b88230;
  background-color: #b88230;
}
.el-button--danger.is-disabled,
.el-button--danger.is-disabled:hover,
.el-button--danger.is-disabled:focus {
  color: #fff;
  border-color: #c45656;
  background-color: #c45656;
}
.el-button--info.is-disabled,
.el-button--info.is-disabled:hover,
.el-button--info.is-disabled:focus {
  color: #fff;
  border-color: #6b7075;
  background-color: #6b7075;
}
</style>
