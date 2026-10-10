import { ref } from 'vue'

export type ToastType = 'error' | 'warning' | 'info' | 'success'

export interface ToastItem {
  id: string
  type: ToastType
  title: string
  description: string
  errorCode?: string
  actionLabel?: string
  onAction?: () => void
  duration?: number
}

const toasts = ref<ToastItem[]>([])

export function useToast() {
  const show = (toast: Omit<ToastItem, 'id'>) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`
    const item: ToastItem = {
      id,
      duration: toast.duration ?? 5000,
      ...toast,
    }
    toasts.value.push(item)

    if (item.duration && item.duration > 0) {
      setTimeout(() => {
        dismiss(id)
      }, item.duration)
    }
    return id
  }

  const dismiss = (id: string) => {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  const clear = () => {
    toasts.value = []
  }

  /**
   * 根据后端抛出的 error_code 智能匹配针对性指引
   */
  const showErrorByCode = (
    errorCode?: string,
    fallbackMsg?: string,
    onRetry?: () => void,
    onOpenSettings?: () => void
  ) => {
    let title = '推演执行未完成'
    let description = '推演发生异常，事务已自动回滚，数据库未录入任何数据。请稍后重试。'
    let actionLabel = '点击重试'
    let onAction = onRetry

    switch (errorCode) {
      case 'AUTH_FAILED':
        title = 'API 凭证鉴权失败'
        description = 'API Key 校验未通过或权限不足。请打开右上角设置检查并更新 API 密钥。'
        actionLabel = '检查 API 设置'
        onAction = onOpenSettings
        break
      case 'RATE_LIMIT_OR_QUOTA':
        title = 'API 额度或频次超限'
        description = '模型接口额度耗尽或每分钟调用频次超限。请稍后重试或检查第三方模型账户额度。'
        actionLabel = '稍后重试'
        onAction = onRetry
        break
      case 'MODEL_NOT_FOUND':
        title = '未找到指定模型'
        description = '模型名称不存在或 Base URL 路径不匹配。请在设置中重新拉取模型列表。'
        actionLabel = '检查模型配置'
        onAction = onOpenSettings
        break
      case 'NETWORK_TIMEOUT':
        title = '网络连接超时'
        description = '请求模型接口超时，推演事务已自动撤销未污染数据库。请确认网络连通后点击重试。'
        actionLabel = '点击重试'
        onAction = onRetry
        break
      case 'NETWORK_ERROR':
        title = '网络连接异常'
        description = '无法连通模型接口服务，请检查 Base URL 地址有效性或代理状态。'
        actionLabel = '检查连接配置'
        onAction = onOpenSettings
        break
      case 'PASS1_FAILED':
        title = 'Pass 1 裁决生成中断'
        description = '世界因果裁决数据解析失败，推演已自动回滚，数据库未产生脏数据。'
        actionLabel = '点击重试'
        onAction = onRetry
        break
      case 'PASS2_FAILED':
        title = 'Pass 2 文学撰写中断'
        description = '场景小说正文生成中断，推演事务已撤销，数据库未录入任何数据。'
        actionLabel = '点击重试'
        onAction = onRetry
        break
      case 'EMPTY_RESPONSE':
        title = '模型返回内容为空'
        description = '大模型未输出有效正文内容，已放弃入库。请重试或更换模型。'
        actionLabel = '点击重试'
        onAction = onRetry
        break
      default:
        if (fallbackMsg) {
          description = `${fallbackMsg}（推演已回滚，未录入数据库）`
        }
        break
    }

    return show({
      type: 'error',
      title,
      description,
      errorCode,
      actionLabel,
      onAction,
      duration: 6500,
    })
  }

  const showSuccess = (title: string, description: string = '') => {
    return show({
      type: 'success',
      title,
      description,
      duration: 3500,
    })
  }

  return {
    toasts,
    show,
    dismiss,
    clear,
    showErrorByCode,
    showSuccess,
  }
}
