import { setupServer } from 'msw/node'

// Per-test handlers are registered with server.use(...).
export const server = setupServer()
