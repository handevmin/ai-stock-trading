import { useState } from 'react'
import { marketApi } from '../services/api'
import './StockSearch.css'

interface StockInfo {
  stock_code: string
  stock_name: string
  stock_name_abbr: string
  stock_name_eng: string
  market_code: string
  market_name: string
  stock_type: string
  stock_type_name: string
}

function StockSearch() {
  const [searchTerm, setSearchTerm] = useState('')
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!searchTerm.trim()) return

    setLoading(true)
    setError(null)
    try {
      const response = await marketApi.getStockInfo(searchTerm.trim())
      setStockInfo(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || '종목 정보를 찾을 수 없습니다.')
      setStockInfo(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="stock-search">
      <div className="card">
        <h2>종목 검색</h2>
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            className="input"
            placeholder="종목코드 입력 (예: 005930)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <button type="submit" className="button button-primary" disabled={loading}>
            {loading ? '검색 중...' : '검색'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {stockInfo && (
          <div className="stock-info">
            <h3>{stockInfo.stock_name}</h3>
            <div className="stock-details">
              <div className="detail-item">
                <span className="label">종목코드:</span>
                <span className="value">{stockInfo.stock_code}</span>
              </div>
              <div className="detail-item">
                <span className="label">시장:</span>
                <span className="value">{stockInfo.market_name || stockInfo.market_code}</span>
              </div>
              <div className="detail-item">
                <span className="label">상품유형:</span>
                <span className="value">{stockInfo.stock_type_name || stockInfo.stock_type}</span>
              </div>
              {stockInfo.stock_name_eng && (
                <div className="detail-item">
                  <span className="label">영문명:</span>
                  <span className="value">{stockInfo.stock_name_eng}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default StockSearch


