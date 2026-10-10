import { ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'primary'
  icon?: string
}

interface ConfirmState extends ConfirmOptions {
  isOpen: boolean
  resolve?: (value: boolean) => void
}

const confirmState = ref<ConfirmState>({
  isOpen: false,
  message: '',
})

export function useConfirm() {
  const confirm = (options: ConfirmOptions | string): Promise<boolean> => {
    return new Promise((resolve) => {
      const opts: ConfirmOptions = typeof options === 'string' ? { message: options } : options
      confirmState.value = {
        isOpen: true,
        title: opts.title || '操作确认',
        message: opts.message,
        confirmText: opts.confirmText || '确定',
        cancelText: opts.cancelText || '取消',
        variant: opts.variant || 'danger',
        icon: opts.icon || (opts.variant === 'primary' ? 'material-symbols:info' : 'material-symbols:warning'),
        resolve,
      }
    })
  }

  const handleConfirm = () => {
    confirmState.value.resolve?.(true)
    confirmState.value.isOpen = false
  }

  const handleCancel = () => {
    confirmState.value.resolve?.(false)
    confirmState.value.isOpen = false
  }

  return {
    confirmState,
    confirm,
    handleConfirm,
    handleCancel,
  }
}
