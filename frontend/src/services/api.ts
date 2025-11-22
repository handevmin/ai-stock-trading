import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      console.error('API 오류:', error.response.data)
    }
    return Promise.reject(error)
  }
)

// 계좌 API
export const accountApi = {
  getBalance: () => api.get('/api/account/balance'),
  getHoldings: () => api.get('/api/account/holdings'),
}

// 시세 API
export const marketApi = {
  getCurrentPrice: (stockCode: string) => api.get(`/api/market/current-price/${stockCode}`),
  getOrderbook: (stockCode: string) => api.get(`/api/market/orderbook/${stockCode}`),
  getStockInfo: (stockCode: string) => api.get(`/api/market/stock-info/${stockCode}`),
  getChart: (stockCode: string, startDate: string, endDate: string, period: string = 'D') =>
    api.get(`/api/market/chart/${stockCode}`, {
      params: { start_date: startDate, end_date: endDate, period }
    }),
  getPriceTrend: (stockCode: string) => api.get(`/api/market/trend/${stockCode}`),
  getVolumeRank: (marketCode?: string, sortType?: string) =>
    api.get('/api/market/ranking/volume', { params: { market_code: marketCode, sort_type: sortType } }),
  getFluctuationRank: (marketCode?: string, sortType?: string) =>
    api.get('/api/market/ranking/fluctuation', { params: { market_code: marketCode, sort_type: sortType } }),
  getMarketCapRank: (marketCode?: string) =>
    api.get('/api/market/ranking/market-cap', { params: { market_code: marketCode } }),
}

// 주문 API
export const orderApi = {
  placeOrder: (data: {
    stock_code: string
    side: string
    quantity: number
    price: number
    order_type?: string
  }) => api.post('/api/order/place', data),
  cancelOrder: (orderNo: string, stockCode: string) =>
    api.post(`/api/order/cancel/${orderNo}`, { stock_code: stockCode }),
  getHistory: () => api.get('/api/order/history'),
  getTrades: (limit?: number) => api.get('/api/order/trades', { params: { limit } }),
}

// 전략 API
export const strategyApi = {
  getStrategies: () => api.get('/api/strategy'),
  getStrategy: (id: number) => api.get(`/api/strategy/${id}`),
  getStrategyTypes: () => api.get('/api/strategy/types/list'),
  createStrategy: (data: {
    name: string
    description?: string
    strategy_type?: string
    config?: any
  }) => api.post('/api/strategy', data),
  updateStrategy: (id: number, data: any) => api.put(`/api/strategy/${id}`, data),
  deleteStrategy: (id: number) => api.delete(`/api/strategy/${id}`),
  activateStrategy: (id: number) => api.post(`/api/strategy/${id}/activate`),
  deactivateStrategy: (id: number) => api.post(`/api/strategy/${id}/deactivate`),
}

// 인증 API
export const authApi = {
  refreshToken: () => api.post('/api/auth/token/refresh'),
  getTokenStatus: () => api.get('/api/auth/token/status'),
}

// 관심종목 API
export const watchlistApi = {
  getWatchlist: () => api.get('/api/watchlist'),
  addToWatchlist: (data: { stock_code: string; stock_name?: string; notes?: string }) =>
    api.post('/api/watchlist', data),
  removeFromWatchlist: (id: number) => api.delete(`/api/watchlist/${id}`),
  getWatchlistStockCodes: () => api.get('/api/watchlist/stock-codes'),
}

// 자동매매 API
export const autoTradingApi = {
  execute: () => api.post('/api/auto-trading/execute'),
  getStatus: () => api.get('/api/auto-trading/status'),
  startScheduler: (intervalSeconds: number, scheduleType: 'interval' | 'daily' = 'interval') => 
    api.post('/api/auto-trading/scheduler/start', { 
      interval_seconds: intervalSeconds,
      schedule_type: scheduleType
    }),
  stopScheduler: () => api.post('/api/auto-trading/scheduler/stop'),
}

export default api


