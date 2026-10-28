import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/index.css'
import { permission as permissionDirective } from './directives/permission'

async function bootstrap() {
  // Mock Service Worker — 仅在 VITE_USE_MOCK=true 时启动
  if (import.meta.env.VITE_USE_MOCK === 'true') {
    const { worker } = await import('./mock/browser')
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: `${import.meta.env.BASE_URL}mockServiceWorker.js` },
    })
  }

  const app = createApp(App)
  app.use(createPinia())
  app.use(router)
  app.use(ElementPlus, { size: 'default' })

  // 注册所有 Element Plus 图标为全局组件
  for (const [key, comp] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, comp)
  }

  // 自定义指令
  app.directive('permission', permissionDirective)

  app.mount('#app')
}

bootstrap()
