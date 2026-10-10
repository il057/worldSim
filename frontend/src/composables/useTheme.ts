import { ref, computed } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'auto'

export interface ThemePreset {
  id: string
  name: string
  color: string
  hover: string
}

export const THEME_COLOR_PRESETS: ThemePreset[] = [
  { id: 'indigo', name: '经典靛蓝', color: '#5e72e4', hover: '#4b5ecc' },
  { id: 'cyan', name: '极光湖蓝', color: '#0ea5e9', hover: '#0284c7' },
  { id: 'emerald', name: '翡翠青碧', color: '#10b981', hover: '#059669' },
  { id: 'amber', name: '琉璃琥珀', color: '#f59e0b', hover: '#d97706' },
  { id: 'rose', name: '绯红蔷薇', color: '#f43f5e', hover: '#e11d48' },
  { id: 'violet', name: '暮光罗兰', color: '#8b5cf6', hover: '#7c3aed' },
  { id: 'slate', name: '玄石冷墨', color: '#64748b', hover: '#475569' },
]

const DEFAULT_THEME_MODE: ThemeMode = 'light'
const DEFAULT_THEME_COLOR = '#5e72e4'

// 共享单例响应式状态
const themeMode = ref<ThemeMode>(
  (localStorage.getItem('neu_theme_mode') as ThemeMode) || DEFAULT_THEME_MODE
)
const themeColor = ref<string>(
  localStorage.getItem('neu_theme_color') || DEFAULT_THEME_COLOR
)

// 计算稍暗的悬停色
function computeHoverColor(hex: string): string {
  const preset = THEME_COLOR_PRESETS.find(
    (p) => p.color.toLowerCase() === hex.toLowerCase()
  )
  if (preset) return preset.hover

  let c = hex.replace('#', '')
  if (c.length === 3) c = c.split('').map((x) => x + x).join('')
  const num = parseInt(c, 16)
  if (isNaN(num)) return hex
  const r = Math.max(0, (num >> 16) - 22)
  const g = Math.max(0, ((num >> 8) & 0x00ff) - 22)
  const b = Math.max(0, (num & 0x0000ff) - 22)
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`
}

function hexToRgb(hex: string): string {
  let c = hex.replace('#', '')
  if (c.length === 3) c = c.split('').map((x) => x + x).join('')
  const num = parseInt(c, 16)
  if (isNaN(num)) return '94, 114, 228'
  const r = (num >> 16) & 255
  const g = (num >> 8) & 255
  const b = num & 255
  return `${r}, ${g}, ${b}`
}

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  let c = hex.replace('#', '')
  if (c.length === 3) c = c.split('').map((x) => x + x).join('')
  const num = parseInt(c, 16)
  if (isNaN(num)) return { h: 231, s: 72, l: 63 }
  const r = ((num >> 16) & 255) / 255
  const g = ((num >> 8) & 255) / 255
  const b = (num & 255) / 255

  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }
    h = Math.round(h * 60)
  }
  return { h, s: Math.round(s * 100), l: Math.round(l * 100) }
}

/**
 * 依据当前主题主色调 (themeColor) 纯动态衍生对白色彩体系
 * 杜绝任何写死硬编码，随用户主题色与深浅模式智能映射
 */
function deriveDialogueColors(hex: string, isDark: boolean) {
  const { h, s } = hexToHsl(hex)
  const baseSat = Math.max(s, 30)

  if (isDark) {
    return {
      // 主双引号对白：同色系高明度高对比微光，与主题色浑然一体
      double: `hsl(${h}, ${Math.min(baseSat + 15, 95)}%, 76%)`,
      // 东方角标引对白：偏暖向邻近色（+28度），典雅文学层次
      corner: `hsl(${(h + 28) % 360}, ${Math.min(baseSat + 10, 90)}%, 74%)`,
      // 单引号心绪/轻声：偏冷向邻近色（-28度），清润通透
      single: `hsl(${(h - 28 + 360) % 360}, ${Math.min(baseSat + 10, 90)}%, 75%)`,
    }
  } else {
    return {
      // 主双引号对白：同色系深邃高对比度，保证浅色底上的极致清晰度
      double: `hsl(${h}, ${Math.min(baseSat + 20, 95)}%, 32%)`,
      // 东方角标引对白：偏暖向深色邻近色
      corner: `hsl(${(h + 28) % 360}, ${Math.min(baseSat + 15, 90)}%, 34%)`,
      // 单引号心绪/轻声：偏冷向深色邻近色
      single: `hsl(${(h - 28 + 360) % 360}, ${Math.min(baseSat + 15, 90)}%, 33%)`,
    }
  }
}

// 应用主题变量到 DOM
function applyTheme() {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  let resolvedMode: 'light' | 'dark' = 'light'

  if (themeMode.value === 'auto') {
    resolvedMode =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
  } else {
    resolvedMode = themeMode.value
  }

  root.setAttribute('data-theme', resolvedMode)
  if (document.body) {
    document.body.setAttribute('data-theme', resolvedMode)
  }

  const activeColor = themeColor.value || DEFAULT_THEME_COLOR
  const hoverColor = computeHoverColor(activeColor)
  const isDarkActive = resolvedMode === 'dark'

  // 直接写入最高优先级的全局 CSS 变量
  if (isDarkActive) {
    root.style.setProperty('--neu-bg', '#1c2027')
    root.style.setProperty('--neu-surface', '#1c2027')
    root.style.setProperty('--neu-light', '#272d37')
    root.style.setProperty('--neu-dark', '#121419')
    root.style.setProperty('--neu-text-primary', '#e2e8f0')
    root.style.setProperty('--neu-text-secondary', '#94a3b8')
    root.style.setProperty('--neu-text-muted', '#64748b')
    root.style.setProperty('--neu-border', 'rgba(255, 255, 255, 0.08)')
  } else {
    root.style.setProperty('--neu-bg', '#e6e9ef')
    root.style.setProperty('--neu-surface', '#e6e9ef')
    root.style.setProperty('--neu-light', '#ffffff')
    root.style.setProperty('--neu-dark', '#c4c9d4')
    root.style.setProperty('--neu-text-primary', '#2d3748')
    root.style.setProperty('--neu-text-secondary', '#718096')
    root.style.setProperty('--neu-text-muted', '#a0aec0')
    root.style.setProperty('--neu-border', 'rgba(255, 255, 255, 0.45)')
  }

  // 动态主题色及其 RGB 变量
  root.style.setProperty('--neu-accent', activeColor)
  root.style.setProperty('--neu-accent-hover', hoverColor)
  root.style.setProperty('--neu-accent-rgb', hexToRgb(activeColor))

  // 动态与主题色深度绑定的对白颜色
  const dialogueColors = deriveDialogueColors(activeColor, isDarkActive)
  root.style.setProperty('--dialogue-double', dialogueColors.double)
  root.style.setProperty('--dialogue-corner', dialogueColors.corner)
  root.style.setProperty('--dialogue-single', dialogueColors.single)
}

// 监听系统深浅色切换
if (typeof window !== 'undefined' && window.matchMedia) {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  mediaQuery.addEventListener('change', () => {
    if (themeMode.value === 'auto') {
      applyTheme()
    }
  })
}

export function useTheme() {
  const setThemeMode = (mode: ThemeMode) => {
    themeMode.value = mode
    localStorage.setItem('neu_theme_mode', mode)
    applyTheme()
  }

  const setThemeColor = (color: string) => {
    themeColor.value = color
    localStorage.setItem('neu_theme_color', color)
    applyTheme()
  }

  const initTheme = () => {
    applyTheme()
  }

  const isDark = computed(() => {
    if (themeMode.value === 'auto') {
      return (
        typeof window !== 'undefined' &&
        window.matchMedia?.('(prefers-color-scheme: dark)').matches
      )
    }
    return themeMode.value === 'dark'
  })

  // 动态生成符合当前主题色与深浅背景的 DiceBear 头像 URL
  const getDicebearAvatarUrl = (name?: string): string => {
    const seed = encodeURIComponent(name || 'NPC')
    const darkActive = isDark.value
    const bgColors = darkActive ? '1c2027,272d37,121419' : 'e6e9ef,d9dde5,f0f3f8'
    const cleanColor = (themeColor.value || DEFAULT_THEME_COLOR).replace('#', '')
    const bodyColors = darkActive
      ? `cbd5e1,94a3b8,64748b,475569,${cleanColor}`
      : `4a4a50,63636a,37373c,757580,${cleanColor}`

    return `https://api.dicebear.com/10.x/slice/svg?seed=${seed}&backgroundColor=${bgColors}&bodyColor=${bodyColors}`
  }

  return {
    themeMode,
    themeColor,
    isDark,
    presets: THEME_COLOR_PRESETS,
    setThemeMode,
    setThemeColor,
    initTheme,
    getDicebearAvatarUrl,
  }
}
