export interface User {
  id: string
  name: string
  username?: string
  email?: string
}

export interface Session {
  token: string | null
  user: User | null
  isAuthenticated: boolean
}
