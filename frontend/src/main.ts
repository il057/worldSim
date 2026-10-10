import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import { useTheme } from './composables/useTheme'

useTheme().initTheme()

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
