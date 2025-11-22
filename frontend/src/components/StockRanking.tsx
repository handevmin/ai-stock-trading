import { useState, useEffect } from 'react'
import { marketApi, orderApi } from '../services/api'
import './StockRanking.css'

interface RankingItem {
  rank: number
  stock_code: string
  stock_name: string
  current_price: number
  change_price: number
  change_rate: number
  change_sign: string
  volume?: number
  amount?: number
  market_cap?: number
}

interface RankingResponse {
  market_code: string
  sort_type?: string
  rankings: RankingItem[]
}

function StockRanking() {
  const [activeTab, setActiveTab] = useState<'volume' | 'fluctuation' | 'market_cap'>('volume')
  const [rankings, setRankings] = useState<RankingItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [marketCode, setMarketCode] = useState('J')
  const [sortType, setSortType] = useState('0')
  const [showOrderModal, setShowOrderModal] = useState(false)
  const [selectedStock, setSelectedStock] = useState<RankingItem | null>(null)
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY')
  const [orderQuantity, setOrderQuantity] = useState(1)
  const [orderPrice, setOrderPrice] = useState(0)
  const [orderType, setOrderType] = useState('00') // 00: 지정가, 01: 시장가
  const [orderLoading, setOrderLoading] = useState(false)
  const [orderError, setOrderError] = useState<string | null>(null)
  const [orderSuccess, setOrderSuccess] = useState(false)

  const fetchRankings = async () => {
    setLoading(true)
    setError(null)
    try {
      let response
      if (activeTab === 'volume') {
        response = await marketApi.getVolumeRank(marketCode, sortType)
      } else if (activeTab === 'fluctuation') {
        response = await marketApi.getFluctuationRank(marketCode, sortType)
      } else {
        response = await marketApi.getMarketCapRank(marketCode)
      }
      setRankings(response.data.rankings || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || '랭킹 데이터를 불러오는데 실패했습니다.')
      setRankings([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRankings()
  }, [activeTab, marketCode, sortType])

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR').format(num)
  }

  const formatAmount = (num: number) => {
    if (num >= 1000000000000) {
      return `${(num / 1000000000000).toFixed(2)}조`
    } else if (num >= 100000000) {
      return `${(num / 100000000).toFixed(2)}억`
    } else if (num >= 10000) {
      return `${(num / 10000).toFixed(2)}만`
    }
    return formatNumber(num)
  }

  const handleOrderClick = (stock: RankingItem, side: 'BUY' | 'SELL') => {
    setSelectedStock(stock)
    setOrderSide(side)
    setOrderPrice(stock.current_price)
    setOrderQuantity(1)
    setOrderType('00')
    setOrderError(null)
    setOrderSuccess(false)
    setShowOrderModal(true)
  }

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedStock) return

    setOrderLoading(true)
    setOrderError(null)
    setOrderSuccess(false)

    try {
      await orderApi.placeOrder({
        stock_code: selectedStock.stock_code,
        side: orderSide,
        quantity: orderQuantity,
        price: orderPrice,
        order_type: orderType,
      })

      setOrderSuccess(true)
      setTimeout(() => {
        setShowOrderModal(false)
        setOrderSuccess(false)
        fetchRankings() // 랭킹 새로고침
      }, 1500)
    } catch (err: any) {
      setOrderError(err.response?.data?.detail || '주문에 실패했습니다.')
    } finally {
      setOrderLoading(false)
    }
  }

  const calculateTotalAmount = () => {
    if (orderType === '01') {
      // 시장가인 경우 현재가 기준
      return selectedStock ? selectedStock.current_price * orderQuantity : 0
    }
    return orderPrice * orderQuantity
  }

  return (
    <div className="stock-ranking">
      <div className="card">
        <div className="ranking-header">
          <h2>실시간 랭킹</h2>
          <div className="ranking-controls">
            <select
              className="input"
              value={marketCode}
              onChange={(e) => setMarketCode(e.target.value)}
              style={{ width: '120px' }}
            >
              <option value="J">KRX</option>
              <option value="Q">코스닥</option>
              <option value="UN">통합</option>
            </select>
            {activeTab !== 'market_cap' && (
              <select
                className="input"
                value={sortType}
                onChange={(e) => setSortType(e.target.value)}
                style={{ width: '150px' }}
              >
                {activeTab === 'volume' ? (
                  <>
                    <option value="0">평균거래량</option>
                    <option value="1">거래증가율</option>
                    <option value="2">평균거래회전율</option>
                    <option value="3">거래금액순</option>
                    <option value="4">평균거래금액회전율</option>
                  </>
                ) : (
                  <option value="0000">등락률순</option>
                )}
              </select>
            )}
            <button
              className="button button-primary"
              onClick={fetchRankings}
              disabled={loading}
            >
              {loading ? '로딩 중...' : '새로고침'}
            </button>
          </div>
        </div>

        <div className="ranking-tabs">
          <button
            className={`tab-button ${activeTab === 'volume' ? 'active' : ''}`}
            onClick={() => setActiveTab('volume')}
          >
            거래량순위
          </button>
          <button
            className={`tab-button ${activeTab === 'fluctuation' ? 'active' : ''}`}
            onClick={() => setActiveTab('fluctuation')}
          >
            등락률순위
          </button>
          <button
            className={`tab-button ${activeTab === 'market_cap' ? 'active' : ''}`}
            onClick={() => setActiveTab('market_cap')}
          >
            시가총액순위
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {loading && rankings.length === 0 ? (
          <div className="loading">로딩 중...</div>
        ) : (
          <div className="ranking-table">
            <table>
              <thead>
                <tr>
                  <th>순위</th>
                  <th>종목명</th>
                  <th>종목코드</th>
                  <th>현재가</th>
                  <th>전일대비</th>
                  <th>등락률</th>
                  {activeTab === 'volume' && <th>거래량</th>}
                  {activeTab === 'volume' && <th>거래대금</th>}
                  {activeTab === 'market_cap' && <th>시가총액</th>}
                  <th>주문</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((item) => (
                  <tr key={item.rank}>
                    <td className="rank-cell">{item.rank}</td>
                    <td className="name-cell">{item.stock_name}</td>
                    <td className="code-cell">{item.stock_code}</td>
                    <td>{formatNumber(item.current_price)}원</td>
                    <td className={item.change_price >= 0 ? 'up' : 'down'}>
                      {item.change_price >= 0 ? '+' : ''}
                      {formatNumber(item.change_price)}원
                    </td>
                    <td className={item.change_rate >= 0 ? 'up' : 'down'}>
                      {item.change_rate >= 0 ? '+' : ''}
                      {item.change_rate.toFixed(2)}%
                    </td>
                    {activeTab === 'volume' && (
                      <>
                        <td>{formatNumber(item.volume || 0)}</td>
                        <td>{formatAmount(item.amount || 0)}</td>
                      </>
                    )}
                    {activeTab === 'market_cap' && (
                      <td>{formatAmount((item.market_cap || 0) * 1000000000000)}</td>
                    )}
                    <td className="action-cell">
                      <button
                        className="order-btn buy-btn"
                        onClick={() => handleOrderClick(item, 'BUY')}
                      >
                        매수
                      </button>
                      <button
                        className="order-btn sell-btn"
                        onClick={() => handleOrderClick(item, 'SELL')}
                      >
                        매도
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rankings.length === 0 && !loading && (
              <div className="empty-state">랭킹 데이터가 없습니다.</div>
            )}
          </div>
        )}
      </div>

      {/* 주문 모달 */}
      {showOrderModal && selectedStock && (
        <div className="modal-overlay" onClick={() => setShowOrderModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>
                {orderSide === 'BUY' ? '매수' : '매도'} 주문 - {selectedStock.stock_name} ({selectedStock.stock_code})
              </h3>
              <button className="modal-close" onClick={() => setShowOrderModal(false)}>
                ×
              </button>
            </div>

            <div className="modal-body">
              <div className="order-info">
                <div className="info-item">
                  <span className="label">현재가:</span>
                  <span className="value">{formatNumber(selectedStock.current_price)}원</span>
                </div>
                <div className="info-item">
                  <span className="label">전일대비:</span>
                  <span className={`value ${selectedStock.change_price >= 0 ? 'up' : 'down'}`}>
                    {selectedStock.change_price >= 0 ? '+' : ''}
                    {formatNumber(selectedStock.change_price)}원 ({selectedStock.change_rate >= 0 ? '+' : ''}
                    {selectedStock.change_rate.toFixed(2)}%)
                  </span>
                </div>
              </div>

              <form onSubmit={handleOrderSubmit} className="order-form">
                <div className="form-group">
                  <label>주문 유형</label>
                  <select
                    className="input"
                    value={orderType}
                    onChange={(e) => {
                      setOrderType(e.target.value)
                      if (e.target.value === '01') {
                        // 시장가 선택 시 현재가로 설정
                        setOrderPrice(selectedStock.current_price)
                      }
                    }}
                  >
                    <option value="00">지정가</option>
                    <option value="01">시장가</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>주문 수량</label>
                  <input
                    type="number"
                    className="input"
                    min="1"
                    value={orderQuantity}
                    onChange={(e) => setOrderQuantity(parseInt(e.target.value) || 1)}
                    required
                  />
                </div>

                {orderType === '00' && (
                  <div className="form-group">
                    <label>주문 가격 (원)</label>
                    <input
                      type="number"
                      className="input"
                      min="0"
                      step="1"
                      value={orderPrice}
                      onChange={(e) => setOrderPrice(parseFloat(e.target.value) || 0)}
                      required
                    />
                  </div>
                )}

                <div className="order-summary">
                  <div className="summary-item">
                    <span className="label">총 주문 금액:</span>
                    <span className="value">{formatNumber(calculateTotalAmount())}원</span>
                  </div>
                </div>

                {orderError && <div className="error">{orderError}</div>}
                {orderSuccess && (
                  <div className="success">주문이 성공적으로 접수되었습니다!</div>
                )}

                <div className="modal-actions">
                  <button
                    type="button"
                    className="button button-secondary"
                    onClick={() => setShowOrderModal(false)}
                    disabled={orderLoading}
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    className={`button ${orderSide === 'BUY' ? 'button-buy' : 'button-sell'}`}
                    disabled={orderLoading || orderSuccess}
                  >
                    {orderLoading ? '주문 중...' : orderSide === 'BUY' ? '매수 주문' : '매도 주문'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StockRanking

