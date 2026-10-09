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
    enableStreamDisplay: (() => {
      const stored = localStorage.getItem('enable_stream_display')
      return stored !== null ? stored === 'true' : true
    })() as boolean,
    isStreaming: false,
    streamingStage: '' as 'pass1' | 'pass2' | '',
    streamingLog: null as StoryLogView | null,
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
        // 同步系统配置中的流式显示选项
        try {
          const cfgRes = await apiClient.getSystemConfig()
          if (cfgRes.data?.enable_stream_display !== undefined) {
            this.enableStreamDisplay = Boolean(cfgRes.data.enable_stream_display)
            localStorage.setItem('enable_stream_display', String(this.enableStreamDisplay))
          }
        } catch {
          // 降级使用本地存储
        }
      } catch (err: any) {
        this.error = err.message || '初始化加载失败'
      } finally {
        this.isLoading = false
      }
    },

    setEnableStreamDisplay(val: boolean) {
      this.enableStreamDisplay = val
      localStorage.setItem('enable_stream_display', String(val))
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

    async executeSimTick(
      actionType: 'step' | 'fastForward' | 'triggerIncident',
      params: { hours?: number; stepType?: 'hour_6' | 'day_1' } = {}
    ) {
      if (!this.currentCharacterId || this.isTicking) return
      this.isTicking = true
      this.error = null
      this.streamingLog = null

      let defaultStatus = '推演进行中...'
      if (actionType === 'step') {
        defaultStatus = `正在推演演化 (${params.hours || 1}h)...`
      } else if (actionType === 'fastForward') {
        const span = params.stepType === 'hour_6' ? '+6h 阶段快进' : '+24h 跨日跃迁'
        defaultStatus = `正在执行 ${span}...`
      } else if (actionType === 'triggerIncident') {
        defaultStatus = 'AI 正在构思因果突发事件并注入裁决...'
      }
      this.tickStatusText = defaultStatus

      try {
        const config = this.getActivePromptConfig()
        let resData: { story_log: StoryLogView; current_state: CharacterStateView }

        if (this.enableStreamDisplay) {
          this.isStreaming = true
          this.streamingStage = 'pass1'

          const callbacks = {
            onStatus: (data: { stage: 'pass1' | 'pass2'; message: string }) => {
              this.streamingStage = data.stage
              if (data.stage === 'pass1') {
                this.tickStatusText = data.message || 'Pass 1 正在进行理性因果裁决...'
              } else if (data.stage === 'pass2') {
                this.tickStatusText = data.message || 'Pass 2 正在以有限视角实时书写正文...'
              }
            },
            onPass1Done: (data: { virtual_time: string; location: string; plot_beat: string }) => {
              const nextIndex =
                this.timeline.length > 0 ? this.timeline[this.timeline.length - 1].tick_index + 1 : 1
              this.streamingLog = {
                id: -999,
                character_id: this.currentCharacterId,
                tick_index: nextIndex,
                virtual_time: data.virtual_time,
                location: data.location,
                plot_beat: data.plot_beat,
                narrative_prose: '',
              }
            },
            onChunk: (chunk: string) => {
              if (!this.streamingLog) {
                const nextIndex =
                  this.timeline.length > 0 ? this.timeline[this.timeline.length - 1].tick_index + 1 : 1
                this.streamingLog = {
                  id: -999,
                  character_id: this.currentCharacterId,
                  tick_index: nextIndex,
                  virtual_time: this.currentState?.virtual_time || '',
                  location: this.currentState?.location || '',
                  plot_beat: '',
                  narrative_prose: '',
                }
              }
              this.streamingLog.narrative_prose += chunk
            },
          }

          if (actionType === 'step') {
            resData = await apiClient.stepStream(
              this.currentCharacterId,
              params.hours || 1,
              config,
              callbacks
            )
          } else if (actionType === 'fastForward') {
            resData = await apiClient.fastForwardStream(
              this.currentCharacterId,
              params.stepType || 'hour_6',
              config,
              callbacks
            )
          } else {
            resData = await apiClient.triggerIncidentStream(
              this.currentCharacterId,
              config,
              callbacks
            )
          }
        } else {
          // 普通非流式单次请求
          let res: any
          if (actionType === 'step') {
            res = await apiClient.step(this.currentCharacterId, params.hours || 1, config)
          } else if (actionType === 'fastForward') {
            res = await apiClient.fastForward(
              this.currentCharacterId,
              params.stepType || 'hour_6',
              config
            )
          } else {
            res = await apiClient.triggerIncident(this.currentCharacterId, config)
          }
          resData = res.data
        }

        // 统一提交推演结果
        this.currentState = resData.current_state
        if (this.currentDetail) {
          this.currentDetail.state = resData.current_state
        }
        this.timeline.push(resData.story_log)

        // 若产生了新结识的 NPC 或好感变动，刷新社交关系网
        if (resData.story_log?.delta_snapshot?.relationship_delta?.new_npcs?.length) {
          await this.refreshRelationships()
        }
      } catch (err: any) {
        const errInfo = extractErrorInfo(err)
        this.error = errInfo.message
        useToast().showErrorByCode(errInfo.errorCode, errInfo.message, () =>
          this.executeSimTick(actionType, params)
        )
      } finally {
        this.isTicking = false
        this.isStreaming = false
        this.streamingStage = ''
        this.streamingLog = null
        this.tickStatusText = ''
      }
    },

    async runStep(hours = 1) {
      return this.executeSimTick('step', { hours })
    },

    async runFastForward(stepType: 'hour_6' | 'day_1') {
      return this.executeSimTick('fastForward', { stepType })
    },

    async triggerIncident() {
      return this.executeSimTick('triggerIncident')
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
