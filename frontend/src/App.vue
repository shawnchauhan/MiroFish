<template>
  <div v-if="authState.authEnabled && authState.authenticated" class="auth-bar">
    <div class="auth-user">
      <img v-if="authState.user?.avatar_url" :src="authState.user.avatar_url" class="avatar" />
      <span class="user-name">{{ authState.user?.display_name || authState.user?.email }}</span>
    </div>
    <button class="logout-btn" @click="handleLogout">Logout</button>
  </div>
  <router-view />
</template>

<script setup>
import { useRouter } from 'vue-router'
import { authState, clearAuth } from './store/auth'
import { logout } from './api/auth'

const router = useRouter()

async function handleLogout() {
  try {
    await logout()
  } catch {
    // ignore errors, clear client state regardless
  }
  clearAuth()
  router.push({ name: 'Login' })
}
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #000000;
  background-color: #ffffff;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #000000;
}

::-webkit-scrollbar-thumb:hover {
  background: #333333;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

/* Auth bar */
.auth-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 20px;
  background: #f8f8f8;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
}

.auth-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
}

.user-name {
  color: #333;
}

.logout-btn {
  background: none;
  border: 1px solid #ccc;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  color: #666;
}
.logout-btn:hover {
  border-color: #999;
  color: #333;
}
</style>
