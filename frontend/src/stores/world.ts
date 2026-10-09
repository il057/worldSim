import { defineStore } from 'pinia'
import { apiClient } from '../api/client'
import { useToast } from '../composables/useToast'
import type {
  CharacterDetailView,
  CharacterStateView,
  StoryLogView,
} from '../api/client'

function extractErrorInfo(err: any): { errorCode?: string; message: string } {
  const detail = err.response?.data?.detail
  if (detail && typeof detail === 'object') {
    return {
      errorCode: detail.error_code,
      message: detail.message || '推演执行未完成',
    }
  }
  if (typeof detail === 'string') {
    return {
      message: detail,
    }
  }
  return {
    message: err.message || '网络或接口服务异常',
  }
}

export const useWorldStore = defineStore('world', {
  state: () => ({
    characters: [] as Array<{ id: string; name: string; title?: string }>,
    currentCharacterId: '' as string,
    currentDetail: null as CharacterDetailView | null,
    currentState: null as CharacterStateView | null,
    timeline: [] as StoryLogView[],
    isLoading: false,
    isTicking: false,
    tickStatusText: '',
    error: null as string | null,
  }),

  getters: {
    currentCharacter: (state) => state.currentDetail,
    hasLogs: (state) => state.timeline.length > 0,
    isSleeping: (state) => Boolean(state.currentState?.is_sleeping),
  },

  actions: {
    async initialize() {
      this.isLoading = true
      this.error = null
      try {
        const res = await apiClient.getCharacters()
        this.characters = res.data
        if (this.characters.length > 0) {
          const targetId = this.currentCharacterId || this.characters[0].id
          await this.selectCharacter(targetId)
        }
      } catch (err: any) {
        this.error = err.message || '初始化加载失败'
      } finally {
        this.isLoading = false
      }
    },

    async selectCharacter(characterId: string) {
      this.currentCharacterId = characterId
      this.isLoading = true
      this.error = null
      try {
        const [detailRes, timeRes] = await Promise.all([
          apiClient.getCharacterDetail(characterId),
          apiClient.getTimeline(characterId, 1, 50),
        ])
        this.currentDetail = detailRes.data
        this.currentState = detailRes.data.state || null
        this.timeline = timeRes.data.items
      } catch (err: any) {
        this.error = err.message || '加载角色详情失败'
      } finally {
        this.isLoading = false
      }
    },

    async refreshState() {
      if (!this.currentCharacterId) return
      try {
        const stateRes = await apiClient.getCharacterState(this.currentCharacterId)
        this.currentState = stateRes.data
        if (this.currentDetail) {
          this.currentDetail.state = stateRes.data
        }
      } catch (err: any) {
        console.error('刷新状态异常:', err)
      }
    },

    getActivePromptConfig() {
      try {
        const raw = localStorage.getItem('simulation_prompt_config')
        if (raw) {
          return JSON.parse(raw)
        }
      } catch (e) {
        console.error('解析 simulation_prompt_config 异常:', e)
      }
      const pass1 = localStorage.getItem('custom_pass1_prompt') || undefined
      const pass2 = localStorage.getItem('custom_pass2_prompt') || undefined
      if (pass1 || pass2) {
        return {
          pass1_custom_prompt: pass1,
          pass2_custom_prompt: pass2,
        }
      }
      return undefined
    },

    async refreshRelationships() {
      if (!this.currentCharacterId) return
      try {
        const detailRes = await apiClient.getCharacterDetail(this.currentCharacterId)
        if (this.currentDetail) {
          this.currentDetail.relationships = detailRes.data.relationships
        }
      } catch (err: any) {
        console.error('刷新社交关系失败:', err)
      }
    },

    async runStep(hours = 1) {
      if (!this.currentCharacterId || this.isTicking) return
      this.isTicking = true
      this.tickStatusText = `正在推演演化 (${hours}h)...`
      this.error = null
      try {
        const config = this.getActivePromptConfig()
        const res = await apiClient.step(this.currentCharacterId, hours, config)
        this.currentState = res.data.current_state
        if (this.currentDetail) {
          this.currentDetail.state = res.data.current_state
        }
        this.timeline.push(res.data.story_log)
        // 若产生了新结识的 NPC 或好感变动，刷新社交关系网
        if (res.data.story_log?.delta_snapshot?.relationship_delta?.new_npcs?.length) {
          await this.refreshRelationships()
        }
      } catch (err: any) {
        const errInfo = extractErrorInfo(err)
        this.error = errInfo.message
        useToast().showErrorByCode(errInfo.errorCode, errInfo.message, () => this.runStep(hours))
      } finally {
        this.isTicking = false
        this.tickStatusText = ''
      }
    },

    async runFastForward(stepType: 'hour_6' | 'day_1') {
      if (!this.currentCharacterId || this.isTicking) return
      this.isTicking = true
      const span = stepType === 'hour_6' ? '+6h 阶段快进' : '+24h 跨日跃迁'
      this.tickStatusText = `正在执行 ${span}...`
      this.error = null
      try {
        const config = this.getActivePromptConfig()
        const res = await apiClient.fastForward(this.currentCharacterId, stepType, config)
        this.currentState = res.data.current_state
        if (this.currentDetail) {
          this.currentDetail.state = res.data.current_state
        }
        this.timeline.push(res.data.story_log)
        if (res.data.story_log?.delta_snapshot?.relationship_delta?.new_npcs?.length) {
          await this.refreshRelationships()
        }
      } catch (err: any) {
        const errInfo = extractErrorInfo(err)
        this.error = errInfo.message
        useToast().showErrorByCode(errInfo.errorCode, errInfo.message, () => this.runFastForward(stepType))
      } finally {
        this.isTicking = false
        this.tickStatusText = ''
      }
    },

    async triggerIncident() {
      if (!this.currentCharacterId || this.isTicking) return
      this.isTicking = true
      this.tickStatusText = 'AI 正在构思因果突发事件并注入裁决...'
      this.error = null
      try {
        const config = this.getActivePromptConfig()
        const res = await apiClient.triggerIncident(this.currentCharacterId, config)
        this.currentState = res.data.current_state
        if (this.currentDetail) {
          this.currentDetail.state = res.data.current_state
        }
        this.timeline.push(res.data.story_log)
      } catch (err: any) {
        const errInfo = extractErrorInfo(err)
        this.error = errInfo.message
        useToast().showErrorByCode(errInfo.errorCode, errInfo.message, () => this.triggerIncident())
      } finally {
        this.isTicking = false
        this.tickStatusText = ''
      }
    },

    async resetWorld() {
      if (!this.currentCharacterId || this.isTicking) return
      this.isLoading = true
      this.error = null
      try {
        await apiClient.resetCharacter(this.currentCharacterId)
        await this.selectCharacter(this.currentCharacterId)
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || '重置世界失败'
      } finally {
        this.isLoading = false
      }
    },

    async deleteCharacter(characterId: string) {
      if (this.isTicking) return
      this.isLoading = true
      this.error = null
      try {
        await apiClient.deleteCharacter(characterId)
        this.characters = this.characters.filter((c) => c.id !== characterId)
        if (this.currentCharacterId === characterId) {
          if (this.characters.length > 0) {
            await this.selectCharacter(this.characters[0].id)
          } else {
            this.currentCharacterId = ''
            this.currentDetail = null
            this.currentState = null
            this.timeline = []
          }
        }
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || '删除角色失败'
        throw err
      } finally {
        this.isLoading = false
      }
    },
  },
})
