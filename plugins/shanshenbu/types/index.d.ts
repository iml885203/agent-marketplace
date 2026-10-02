export type Mood =
  | 'idle'
  | 'working'
  | 'review'
  | 'kick'
  | 'waiting'
  | 'failed'
  | 'jump'
  | 'wave'

declare module 'claude-code' {
  interface PluginState {
    shanshenbu: { mood: Mood; isHidden: boolean }
  }
}
