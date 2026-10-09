import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000, // LLM 推演可能耗时较长
})

export interface CircadianProfile {
  chronotype: string
  typical_rest_window: string
  environment_tolerance: string
  sleep_trigger_summary?: string
}

export interface CharacterStateView {
  id: number
  character_id: string
  virtual_time: string
  location: string
  health: number
  stamina: number
  is_sleeping: number
  psychological_state: string
  inventory: string[]
  active_goals: string[]
  completed_goals: string[]
  total_ticks: number
  updated_at?: string
}

export interface ArbitratorDelta {
  simulated_hours_passed: number
  new_virtual_time: string
  new_location: string
  rest_decision: {
    is_sleeping: boolean
    sleep_quality: string
    rest_reason: string
  }
  health_delta: number
  stamina_delta: number
  psychological_change: string
  inventory_delta: {
    added: string[]
    removed: string[]
  }
  goal_delta: {
    completed: string[]
    added: string[]
    current_active: string[]
  }
  relationship_delta?: {
    new_npcs: Array<{
      npc_name: string
      relation_type: string
      affinity: number
      summary: string
      is_present: boolean
    }>
    updated_npcs: Array<{
      npc_name: string
      relation_type: string
      affinity: number
      summary: string
      is_present: boolean
    }>
  }
  plot_beat: string
  sensory_cues: string[]
}

export interface StoryLogView {
  id: number
  character_id: string
  tick_index: number
  virtual_time: string
  location: string
  plot_beat: string
  narrative_prose: string
  delta_snapshot?: ArbitratorDelta
  created_at?: string
}

export interface CharacterRelationshipView {
  id: number
  npc_name: string
  relation_type: string
  affinity: number
  summary: string
  is_present: number
}

export interface CharacterDetailView {
  id: string
  name: string
  title?: string
  avatar_url?: string
  persona_summary: string
  inner_drive: string
  circadian_profile: CircadianProfile
  is_active: number
  state?: CharacterStateView
  relationships: CharacterRelationshipView[]
  world_lores_count: number
}

export interface DetectedRelationship {
  npc_name: string
  relation_type: string
  affinity: number
  summary: string
}

export interface DetectedEntity {
  entity_id: string
  name: string
  title?: string
  avatar_url?: string
  persona_summary: string
  inner_drive: string
  circadian_profile: CircadianProfile
  relationships_with_others?: string
  initial_location?: string
  initial_virtual_time?: string
  initial_health?: number
  initial_stamina?: number
  initial_psychological_state?: string
  initial_inventory?: string[]
  initial_goals?: string[]
}

export interface WorldLoreInput {
  category: string
  trigger_keys?: string
  title: string
  content: string
}

export interface CardParseResponse {
  is_multi_entity: boolean
  detected_entities: DetectedEntity[]
  detected_relationships?: DetectedRelationship[]
  total_lore_entries: number
  lores: WorldLoreInput[]
  raw_preview?: any
}

export interface StepTickResponse {
  character_id: string
  story_log: StoryLogView
  current_state: CharacterStateView
}

export interface TimelinePageResponse {
  total: number
  page: number
  page_size: number
  items: StoryLogView[]
}

export interface SimulationPromptConfig {
  style_preset?: string
  word_count_tier?: string
  min_words?: number
  max_words?: number
  enabled_patches?: string[]
  custom_style_guidance?: string
  pass1_custom_prompt?: string
  pass2_custom_prompt?: string
}

export const apiClient = {
  // 角色列表与详情
  getCharacters: () => api.get<any[]>('/characters'),
  getCharacterDetail: (id: string) => api.get<CharacterDetailView>(`/characters/${id}/detail`),
  getCharacterState: (id: string) => api.get<CharacterStateView>(`/characters/${id}/state`),
  getTimeline: (id: string, page = 1, pageSize = 30) =>
    api.get<TimelinePageResponse>(`/characters/${id}/timeline?page=${page}&page_size=${pageSize}`),
  resetCharacter: (id: string) => api.post(`/characters/${id}/reset`),
  deleteCharacter: (id: string) => api.delete<{ message: string }>(`/characters/${id}`),

  // 纯按钮推演控制
  step: (characterId: string, hours = 1, config?: SimulationPromptConfig) =>
    api.post<StepTickResponse>('/sim/step', { character_id: characterId, hours, config }),
  fastForward: (characterId: string, stepType: 'hour_6' | 'day_1', config?: SimulationPromptConfig) =>
    api.post<StepTickResponse>('/sim/fast-forward', { character_id: characterId, step_type: stepType, config }),
  triggerIncident: (characterId: string, config?: SimulationPromptConfig) =>
    api.post<StepTickResponse>('/sim/trigger-incident', { character_id: characterId, config }),
  getPromptMeta: () => api.get<any>('/sim/prompt-meta'),

  // 角色卡解析与极简创建
  parseCard: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<CardParseResponse>('/cards/parse', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  importCard: (payload: {
    selected_entity: DetectedEntity
    all_entities: DetectedEntity[]
    lores: WorldLoreInput[]
    relationships?: DetectedRelationship[]
    initial_location?: string
    initial_virtual_time?: string
    initial_health?: number
    initial_stamina?: number
    initial_psychological_state?: string
    initial_inventory?: string[]
    initial_goals?: string[]
  }) => api.post<{ character_id: string; name: string }>('/cards/import', payload),

  generateQuickCharacter: (payload: {
    name: string
    role: string
    archetype: string
    initial_situation: string
  }) => api.post<{ character_id: string; name: string }>('/characters/generate-quick', payload),

  // 世界书管理
  getLores: (characterId: string) => api.get<any[]>(`/characters/${characterId}/lores`),
  createLore: (characterId: string, payload: { category: string; trigger_keys?: string; title: string; content: string }) =>
    api.post<{ id: number; message: string }>(`/characters/${characterId}/lores`, payload),
  deleteLore: (characterId: string, loreId: number) =>
    api.delete<{ message: string }>(`/characters/${characterId}/lores/${loreId}`),

  // 系统配置
  getSystemConfig: () => api.get<any>('/characters/system/config'),
  updateSystemConfig: (payload: any) => api.post<{ message: string }>('/characters/system/config', payload),
  fetchModels: (payload?: { llm_base_url?: string; llm_api_key?: string }) =>
    api.post<{ models: string[] }>('/characters/system/fetch-models', payload || {}),
}

