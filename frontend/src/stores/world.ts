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
    streamingStage: '' as 'pass1' | 'pass2' | 'incident_conceive' | string,
    streamingLog: null as StoryLogView | null,
    lastAffinityDeltas: {} as Record<string, number>,
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
        this.lastAffinityDeltas = {}
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
      actionType: 'step' | 'fastForward' | 'triggerIncident' | 'continue',
      params: { hours?: number; stepType?: 'hour_6' | 'day_1'; incidentDescription?: string } = {}
    ) {
      if (!this.currentCharacterId || this.isTicking) return
      this.isTicking = true
      this.error = null

      const nextIndex =
        this.timeline.length > 0 ? this.timeline[this.timeline.length - 1].tick_index + 1 : 1

      // 无论流式或非流式，推演启动时立即在最新楼层挂载占位卡片
      this.streamingLog = {
        id: -999,
        character_id: this.currentCharacterId,
        tick_index: nextIndex,
        virtual_time: this.currentState?.virtual_time || '推演中',
        location: this.currentState?.location || '推演中',
        plot_beat: '',
        narrative_prose: '',
      }

      let defaultStatus = '推演进行中...'
      if (actionType === 'step') {
        defaultStatus = `正在推进时间 (${params.hours || 1}h)...`
      } else if (actionType === 'continue') {
        defaultStatus = '正在续写故事历程...'
      } else if (actionType === 'fastForward') {
        const span = params.stepType === 'hour_6' ? '+6h 阶段快进' : '+24h 跨日跃迁'
        defaultStatus = `正在执行 ${span}...`
      } else if (actionType === 'triggerIncident') {
        defaultStatus = params.incidentDescription
          ? '正在融入突发事件...'
          : '正在构思突发事件...'
      }
      this.tickStatusText = defaultStatus

      try {
        const config = this.getActivePromptConfig()
        // 记录推演前各 NPC 的好感度快照，以便精准计算本次好感变动值
        const preTickAffinityMap = new Map<string, number>()
        if (this.currentDetail?.relationships) {
          for (const rel of this.currentDetail.relationships) {
            preTickAffinityMap.set(rel.npc_name, rel.affinity)
          }
        }
        let resData: { story_log: StoryLogView; current_state: CharacterStateView }

        if (this.enableStreamDisplay) {
          this.isStreaming = true
          this.streamingStage = 'pass1'
          this.tickStatusText = '【衡律之神】正在权衡因果法则与身心节律...'

          const callbacks = {
            onStatus: (data: { stage: string; message: string }) => {
              this.streamingStage = data.stage
              if (data.message) {
                this.tickStatusText = data.message
              } else if (data.stage === 'pass1') {
                this.tickStatusText = '【衡律之神】正在权衡因果法则与身心节律...'
              } else if (data.stage === 'pass2') {
                this.tickStatusText = '【见证之神】正在以有限视角编织时空切片...'
              }
            },
            onPass1Done: (data: { virtual_time: string; location: string; plot_beat: string }) => {
              if (this.streamingLog) {
                this.streamingLog.virtual_time = data.virtual_time
                this.streamingLog.location = data.location
                this.streamingLog.plot_beat = data.plot_beat
              }
            },
            onChunk: (chunk: string) => {
              if (this.streamingLog) {
                this.streamingLog.narrative_prose += chunk
              }
            },
          }

          if (actionType === 'step') {
            resData = await apiClient.stepStream(
              this.currentCharacterId,
              params.hours || 1,
              config,
              callbacks
            )
          } else if (actionType === 'continue') {
            resData = await apiClient.continueStream(
              this.currentCharacterId,
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
              params.incidentDescription,
              config,
              callbacks
            )
          }
        } else {
          // 普通非流式单次请求
          this.isStreaming = false
          this.streamingStage = ''
          this.tickStatusText = '生成中'

          let res: any
          if (actionType === 'step') {
            res = await apiClient.step(this.currentCharacterId, params.hours || 1, config)
          } else if (actionType === 'continue') {
            res = await apiClient.continue(this.currentCharacterId, config)
          } else if (actionType === 'fastForward') {
            res = await apiClient.fastForward(
              this.currentCharacterId,
              params.stepType || 'hour_6',
              config
            )
          } else {
            res = await apiClient.triggerIncident(this.currentCharacterId, params.incidentDescription, config)
          }
          resData = res.data
        }

        // 统一提交推演结果
        this.streamingLog = null
        this.currentState = resData.current_state
        if (this.currentDetail) {
          this.currentDetail.state = resData.current_state
        }
        this.timeline.push(resData.story_log)

        // 计算本次 NPC 好感度变动 delta
        const deltas: Record<string, number> = {}
        const updatedList = resData.story_log?.delta_snapshot?.relationship_delta?.updated_npcs || []
        for (const u of updatedList) {
          const oldVal = preTickAffinityMap.get(u.npc_name)
          if (oldVal !== undefined) {
            deltas[u.npc_name] = u.affinity - oldVal
          }
        }
        this.lastAffinityDeltas = deltas

        // 若产生了新结识的 NPC 或好感变动，刷新社交关系网
        if (
          resData.story_log?.delta_snapshot?.relationship_delta?.new_npcs?.length ||
          resData.story_log?.delta_snapshot?.relationship_delta?.updated_npcs?.length
        ) {
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

    async runContinue() {
      return this.executeSimTick('continue')
    },

    async runFastForward(stepType: 'hour_6' | 'day_1') {
      return this.executeSimTick('fastForward', { stepType })
    },

    async triggerIncident(incidentDescription?: string) {
      return this.executeSimTick('triggerIncident', { incidentDescription })
    },

    async deleteTimelineLog(log: StoryLogView) {
      if (!this.currentCharacterId || this.isTicking) return
      this.isLoading = true
      this.error = null
      try {
        await apiClient.deleteTimelineLog(this.currentCharacterId, log.id)
        // 级联移除 tick_index >= log.tick_index 的所有切片
        this.timeline = this.timeline.filter((item) => item.tick_index < log.tick_index)
        // 刷新即时状态与人际关系网看板
        await Promise.all([this.refreshState(), this.refreshRelationships()])
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || '删除切片失败'
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async updateTimelineLog(logId: number, narrativeProse: string, plotBeat?: string) {
      if (!this.currentCharacterId) return
      try {
        const res = await apiClient.updateTimelineLog(this.currentCharacterId, logId, {
          narrative_prose: narrativeProse,
          plot_beat: plotBeat,
        })
        const target = this.timeline.find((item) => item.id === logId)
        if (target) {
          target.narrative_prose = res.data.narrative_prose
          if (res.data.plot_beat) {
            target.plot_beat = res.data.plot_beat
          }
        }
      } catch (err: any) {
        this.error = err.response?.data?.detail || err.message || '修改切片失败'
        throw err
      }
    },

    async rewriteLatestLog(log: StoryLogView) {
      if (!this.currentCharacterId || this.isTicking) return
      // 先删除最新切片并回滚状态
      await this.deleteTimelineLog(log)
      // 接着自动触发智能续写生成新的切片
      await this.runContinue()
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
